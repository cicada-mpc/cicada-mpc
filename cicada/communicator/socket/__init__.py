# Copyright 2021 National Technology & Engineering Solutions
# of Sandia, LLC (NTESS). Under the terms of Contract DE-NA0003525 with NTESS,
# the U.S. Government retains certain rights in this software.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Functionality for communicating using the builtin :mod:`socket` module.
"""

import collections
import contextlib
import hashlib
import logging
import multiprocessing
import numbers
import os
import pickle
import queue
import select
import socket
import ssl
import threading
import time
import traceback
import urllib.parse

import numpy
import pynetstring

from ..interface import Communicator
from .connect import LoggerAdapter, NetstringSocket, Timeout, Timer, direct, geturl, listen, rendezvous

Message = collections.namedtuple("Message", ["serial", "tag", "sender", "payload"])
Message.__doc__ = """
Wrapper class for messages sent between processes.
"""

class Failed(Exception):
    """Used to indicate that a player process raised an exception."""
    def __init__(self, exception, traceback):
        self.exception = exception
        self.traceback = traceback

    def __repr__(self):
        return f"Failed(exception={self.exception!r})" # pragma: no cover


class NotRunning(Exception):
    """Raised calling an operation after the communicator has been freed."""
    pass


class Revoked(Exception):
    """Raised calling an operation after the communicator has been revoked."""
    pass


class Terminated(Exception):
    """Used to indicate that a player process terminated unexpectedly without output."""
    def __init__(self, exitcode):
        self.exitcode = exitcode

    def __repr__(self):
        return f"Terminated(exitcode={self.exitcode!r})" # pragma: no cover


class TryAgain(Exception):
    """Raised when a non-blocking operation would block."""
    pass


class SocketCommunicator(Communicator):
    """Cicada communicator that uses Python's builtin :mod:`socket` module as the transport layer.

    Note
    ----
    Creating a communicator is a collective operation that must be called by
    all players that will be members.

    Parameters
    ----------
    sockets: :class:`dict` of :class:`~cicada.communicator.socket.connect.NetstringSocket`, required
        Dictionary containing sockets that are connected to the other players
        and ready to use.  The dictionary keys must be the ranks of the other
        players, and there must be one socket in the dictionary for every
        player except the caller (since players don't need a socket to
        communicate with themselves).  Note that the communicator world size is
        inferred from the size of the dictionary, and the communicator rank
        from whichever key doesn't appear in the dictionary.
    name: :class:`str`, optional
        Human-readable name for this communicator, used for logging and
        debugging.  Defaults to "world"
    timeout: :class:`numbers.Number`
        Maximum time to wait for communication to complete, in seconds.
    """

    _tags = [
        "allgather",
        "barrier-enter",
        "barrier-exit",
        "broadcast",
        "gather",
        "gatherv",
        "revoke",
        "scatter",
        "scatterv",
        "send",
        "shrink-begin",
        "shrink-end",
        ]


    def __init__(self, *, sockets, name="world", timeout=5):
        if not isinstance(sockets, dict):
            raise ValueError("sockets must be a dict, got {sockets} instead.") # pragma: no cover
        for key, socket in sockets.items():
            if not isinstance(key, int):
                raise ValueError("sockets keys must be ints, got {sockets} instead.") # pragma: no cover
            if not isinstance(socket, NetstringSocket):
                raise ValueError("sockets values must be NetstringSocket, got {sockets} instead.") # pragma: no cover

        world_size = len(sockets) + 1
        for index in range(world_size):
            if index not in sockets:
                rank = index

        if not isinstance(name, str):
            raise ValueError("name must be a string, got {name} instead.") # pragma: no cover

        if not isinstance(timeout, numbers.Number):
            raise ValueError(f"timeout must be a number, got {timeout} instead.") # pragma: no cover

        # Setup internal state.
        self._name = name
        self._world_size = world_size
        self._rank = rank
        self._timeout = timeout
        self._revoked = False
        self._log = LoggerAdapter(logging.getLogger(__name__), name, rank)
        self._players = sockets

        # Begin normal operation.
        self._send_serial = 0
        self._running = True

        # Setup queues for incoming messages.
        self._incoming = queue.Queue()
        self._receive_queues = {}
        for tag in self._tags:
            if tag not in ["revoke"]:
                self._receive_queues[tag] = {}
                for rank in self.ranks:
                    self._receive_queues[tag][rank] = queue.Queue()

        # Start queueing incoming messages.
        self._queueing_thread = threading.Thread(name="Queueing", target=self._queue_messages, daemon=True)
        self._queueing_thread.start()

        # Start receiving incoming messages.
        self._incoming_thread = threading.Thread(name="Incoming", target=self._receive_messages, daemon=True)
        self._incoming_thread.start()

        self._log.info(f"communicator ready.")


    def _queue_messages(self):
        # Place incoming messages in the correct queue.
        while self._running:
            # Wait for the next incoming message.
            try:
                message = self._incoming.get(block=True, timeout=0.1)
            except queue.Empty:
                continue

            # Drop messages with missing attributes or unexpected values.
            try:
                if not hasattr(message, "payload"):
                    raise RuntimeError(f"Message missing payload.") # pragma: no cover
                if not hasattr(message, "sender"):
                    raise RuntimeError(f"Message missing sender.") # pragma: no cover
                if not hasattr(message, "serial"):
                    raise RuntimeError(f"Message missing serial number.") # pragma: no cover
                if not hasattr(message, "tag"):
                    raise RuntimeError(f"Message missing tag.") # pragma: no cover
                if message.tag not in self._tags:
                    raise RuntimeError(f"Unknown tag: {message.tag}") # pragma: no cover
                if message.sender not in self.ranks:
                    raise RuntimeError(f"Unexpected sender: {message.sender}") # pragma: no cover
            except Exception as e: # pragma: no cover
                self._log.warning(f"ignoring message: {message} exception: {e}")
                continue

            # Log queued messages.
            if self._log.isEnabledFor(logging.DEBUG):
                self._log.debug(f"<-- player {message.sender} {message.tag}#{message.serial:04}") # pragma: no cover

            # Revoke messages don't get queued because they receive special handling.
            if message.tag == "revoke":
                if not self._revoked:
                    self._revoked = True
                    self._log.warning(f"revoked by player {message.sender}")
                continue

            # Insert the message into the correct queue.
            self._receive_queues[message.tag][message.sender].put(message, block=True, timeout=None)

        self._log.debug(f"queueing thread closed.")


    def _receive_messages(self):
        # Parse and queue incoming messages as they arrive.
        while self._running:
            try:
                # Wait for data to arrive from the other players.
                ready, _, _ = select.select(self._players.values(), [], [], 0.01)
                for player in ready:
                    player.feed()

                # Process any messages that were received. Note that
                # we iterate over every player, not just the ones that
                # were selected above, because there might be a few
                # messages left from the startup process.
                for player in self._players.values():
                    for raw_message in player.messages():
                        # Ignore unparsable messages.
                        try:
                            message = pickle.loads(raw_message)
                        except Exception as e: # pragma: no cover
                            self._log.warning(f"ignoring unparsable message: {e}")
                            continue

                        self._log.debug(f"received {message}")

                        # Insert the message into the incoming queue.
                        self._incoming.put(message, block=True, timeout=None)
            except Exception as e: # pragma: no cover
                self._log.warning(f"receive exception: {e}")

        # The communicator has been freed, so exit the thread.
        self._log.debug(f"receive thread closed.")



    def _receive(self, *, tag, sender, block):
        try:
            return self._receive_queues[tag][sender].get(block=block, timeout=self._timeout)
        except queue.Empty:
            if block:
                raise Timeout(f"Tag {tag!r} from sender {sender} timed-out after {self._timeout}s")
            else: # pragma: no cover
                raise TryAgain(f"Tag {tag!r} from sender {sender} try again.")


    def _require_rank(self, rank):
        if not isinstance(rank, numbers.Integral):
            raise ValueError("Rank must be an integer.") # pragma: no cover
        if rank < 0 or rank >= self._world_size:
            raise ValueError(f"Rank must be in the range [0, {self._world_size}).") # pragma: no cover
        return int(rank)


    def _require_rank_list(self, ranks):
        ranks = [self._require_rank(rank) for rank in ranks]
        if len(ranks) != len(set(ranks)):
            raise ValueError("Duplicate ranks are not allowed.") # pragma: no cover
        return ranks


    def _require_running(self):
        if not self._running:
            raise NotRunning(f"Comm {self.name!r} player {self.rank} is not running.")


    def _require_unrevoked(self):
        if self._revoked:
            raise Revoked(f"Comm {self.name!r} player {self.rank} has been revoked.")


    def _send(self, *, tag, payload, dst):
        if tag not in self._tags:
            raise ValueError(f"Unknown tag: {tag}") # pragma: no cover
        if dst not in self.ranks:
            raise ValueError(f"Unknown destination: {dst}") # pragma: no cover

        message = Message(self._send_serial, tag, self._rank, payload)
        self._send_serial += 1

        if self._log.isEnabledFor(logging.DEBUG):
            self._log.debug(f"--> player {dst} {message.tag}#{message.serial:04}") # pragma: no cover

        # As a special-case, route messages sent to ourself directly to the incoming queue.
        if dst == self.rank:
            self._incoming.put(message, block=True, timeout=None)
        # Otherwise, send the message to the appropriate socket.
        else:
            try:
                raw_message = pickle.dumps(message)
                player = self._players[dst]
                player.send(raw_message)
            except Exception as e: # pragma: no cover
                self._log.error(f"exception sending to {dst}: {e}")


    def all_gather(self, value):
        self._log.debug(f"all_gather()")

        self._require_unrevoked()
        self._require_running()

        # Send messages.
        for rank in self.ranks:
            self._send(tag="allgather", payload=value, dst=rank)

        # Receive messages.
        messages = [self._receive(tag="allgather", sender=rank, block=True) for rank in self.ranks]
        values = [message.payload for message in messages]
        return values


    def barrier(self):
        """If the implementation returns without raising an exception, then
        every player entered the barrier.  If an exception is raised then there
        are no guarantees about whether every player entered.
        """
        self._log.debug(f"barrier()")

        self._require_unrevoked()
        self._require_running()

        # Notify rank 0 that we've entered the barrier.
        self._send(tag="barrier-enter", payload=None, dst=0)

        if self.rank == 0:
            # Wait until every player enters the barrier.
            for rank in self.ranks:
                self._receive(tag="barrier-enter", sender=rank, block=True)
            # Notify every player that it's time to exit the barrier.
            for rank in self.ranks:
                self._send(tag="barrier-exit", payload=None, dst=rank)

        # Wait until we're told to exit.
        self._receive(tag="barrier-exit", sender=0, block=True)


    def broadcast(self, *, src, value):
        self._log.debug(f"broadcast(src={src})")

        self._require_unrevoked()
        self._require_running()

        src = self._require_rank(src)

        # Broadcast the value to all players.
        if self.rank == src:
            for rank in self.ranks:
                self._send(tag="broadcast", payload=value, dst=rank)

        # Receive the broadcast value.
        message = self._receive(tag="broadcast", sender=src, block=True)
        return message.payload


    @staticmethod
    def connect(*, world_size=None, rank=None, address=None, root_address=None, identity=None, trusted=None, name="world", timeout=5, startup_timeout=5):
        """High level function to create a SocketCommunicator.

        This is a high level convenience function that can be used to create a
        communicator, given just the calling player's address and the address
        of the root player.  By default, the parameters will be read from
        environment variables that can be set permanently by the user, or
        temporarily using the :ref:`cicada` command.

        Parameters
        ----------
        world_size: :class:`int`, optional
            Number of players.  Defaults to the value of the CICADA_WORLD_SIZE
            environment variable, which is automatically set by the :ref:`cicada` command.
        rank: :class:`int`, optional
            Rank of the caller.  Defaults to the value of the CICADA_RANK
            environment variable, which is automatically set by the :ref:`cicada` command.
        address: :class:`str`, optional
            Listening address of the caller.  This must be a URL of the form
            `"tcp://{host}:{port}"` for TCP sockets, or `"file:///path/to/foo"`
            for Unix domain sockets.  Defaults to the value of the
            CICADA_ADDRESS environment variable, which is automatically set
            by the :ref:`cicada` command.
        root_address: :class:`str`, optional
            Listening address of the root (rank 0) player.  This must be a URL
            of the form `"tcp://{host}:{port}"` for TCP sockets, or
            `"file:///path/to/foo"` for Unix domain sockets.  Defaults to the
            value of the CICADA_ROOT_ADDRESS environment variable, which is
            automatically set by the :ref:`cicada` command.
        identity: :class:`str`, optional
            Path to a private key and certificate in PEM format.  Defaults to
            the value of the CICADA_IDENTITY environment variable, which is
            automatically set by the :ref:`cicada` command.
        trusted: sequence of :class:`str`, optional
            Path to certificates in PEM format.  Defaults to
            the value of the CICADA_TRUSTED environment variable, which is
            automatically set by the :ref:`cicada` command.
        name: :class:`str`, optional
            Human-readable name for the new communicator.  Defaults to "world".
        timeout: :class:`numbers.Number`
            Communication timeout for the new communicator, in seconds.  Defaults to five.
        startup_timeout: :class:`numbers.Number`
            Maximum time to wait for communicator setup, in seconds.  Defaults to five.

        Raises
        ------
        :class:`ValueError`
            If there are problems with input parameters.
        :class:`Timeout`
            If `timeout` seconds elapses before all connections are established.
        :class:`TokenMismatch`
            If every player doesn't provide the same token during startup.

        Returns
        -------
        communicator: :class:`SocketCommunicator`
            A fully-initialized communicator, ready for use.

        """
        if world_size is None:
            world_size = int(os.environ.get("CICADA_WORLD_SIZE"))
        if rank is None:
            rank = int(os.environ.get("CICADA_RANK"))
        if address is None:
            address = os.environ.get("CICADA_ADDRESS")
        if root_address is None:
            root_address = os.environ.get("CICADA_ROOT_ADDRESS")
        if identity is None:
            identity = os.environ.get("CICADA_IDENTITY", "")
        if trusted is None:
            trusted = [trust for trust in os.environ.get("CICADA_TRUSTED", "").split(",") if trust]

        if identity and trusted:
            server = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            server.load_cert_chain(certfile=identity)
            for trust in trusted:
                server.load_verify_locations(trust)
            server.check_hostname=False
            server.verify_mode = ssl.CERT_REQUIRED

            client = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            client.load_cert_chain(certfile=identity)
            for trust in trusted:
                client.load_verify_locations(trust)
            client.check_hostname = False
            client.verify_mode = ssl.CERT_REQUIRED

            tls = (server, client)
        else:
            tls = None

        timer = Timer(threshold=startup_timeout)
        listen_socket = listen(address=address, rank=rank, name=name, timer=timer)
        sockets = rendezvous(listen_socket=listen_socket, root_address=root_address, world_size=world_size, rank=rank, timer=timer, tls=tls)
        return SocketCommunicator(sockets=sockets, timeout=timeout)


    def free(self):
        # Calling free() multiple times is a no-op.
        if not self._running:
            return

        self._running = False

        # Stop receiving incoming messages.
        self._incoming_thread.join()

        # Stop queueing incoming messages.
        self._queueing_thread.join()

        # Close connections to the other players.
        for player in self._players.values():
            player.close()

        self._log.info(f"communicator freed.")


    def gather(self, *, value, dst):
        self._log.debug(f"gather(dst={dst})")

        self._require_unrevoked()
        self._require_running()

        dst = self._require_rank(dst)

        # Send local data to the destination.
        self._send(tag="gather", payload=value, dst=dst)

        # Receive data from all ranks.
        if self.rank == dst:
            # Messages could arrive out of order.
            messages = [self._receive(tag="gather", sender=rank, block=True) for rank in self.ranks]
            values = [message.payload for message in messages]
            return values

        return None


    def gatherv(self, *, src, value, dst):
        self._log.debug(f"gatherv(src={src}, dst={dst})")

        self._require_unrevoked()
        self._require_running()

        src = self._require_rank_list(src)
        dst = self._require_rank(dst)

        # Send local data to the destination.
        if self.rank in src:
            self._send(tag="gatherv", payload=value, dst=dst)

        # Receive data from the other players.
        if self.rank == dst:
            # Messages could arrive out of order.
            messages = [self._receive(tag="gatherv", sender=rank, block=True) for rank in src]
            values = [message.payload for message in messages]
            return values

        return None


    def irecv(self, *, src):
        self._log.debug(f"irecv(src={src})")

        self._require_unrevoked()
        self._require_running()

        src = self._require_rank(src)

        class Result:
            def __init__(self, communicator, sender):
                self._communicator = communicator
                self._sender = sender
                self._message = None

            @property
            def is_completed(self):
                if self._message is None:
                    try:
                        self._message = self._communicator._receive(tag="send", sender=self._sender, block=False)
                    except TryAgain:
                        pass
                return self._message is not None

            @property
            def value(self):
                if self._message is None:
                    raise RuntimeError("Call not completed.") # pragma: no cover
                return self._message.payload

            def wait(self):
                if self._message is None:
                    self._message = self._communicator._receive(tag="send", sender=self._sender, block=True)

        return Result(self, src)


    def isend(self, *, value, dst):
        self._log.debug(f"isend(dst={dst})")

        self._require_unrevoked()
        self._require_running()

        dst = self._require_rank(dst)

        self._send(tag="send", payload=value, dst=dst)

        # This is safe, because we pickle the value before returning; thus,
        # nothing the caller can do to the value will have unexpected
        # side-effects.
        class Result:
            @property
            def is_completed(self):
                return True
            def wait(self):
                pass

        return Result()


    @property
    def name(self):
        """The name of this communicator, which can be used for logging / debugging.

        Returns
        -------
        name: :class:`str`
        """
        return self._name


    @contextlib.contextmanager
    def override(self, *, timeout=None):
        """Temporarily change communicator properties.

        Use :meth:`override` to temporarily modify communicator behavior in a with statement::

            with communicator.override(timeout=10):
                # Do stuff with the new timeout here.
            # The timeout will return to its previous value here.

        Parameters
        ----------
        timeout: :class:`numbers.Number`, optional
            If specified, override the maximum time for communications to complete, in seconds.

        Returns
        -------
        context: :class:`object`
            A context manager object that will restore the communicator state when exited.
        """
        original_context = {
            "timeout": self._timeout,
        }

        try:
            if timeout is not None:
                self._timeout = timeout
            yield original_context
        finally:
            if timeout is not None:
                self._timeout = original_context["timeout"]


    @property
    def rank(self):
        return self._rank


    def recv(self, *, src):
        self._log.debug(f"recv(src={src})")

        self._require_unrevoked()
        self._require_running()

        src = self._require_rank(src)

        message = self._receive(tag="send", sender=src, block=True)
        return message.payload


    def revoke(self):
        """Revoke the current communicator.

        Revokes the communicator for this player, and any players able to
        receive messages.  A revoked communicator cannot be used to perform any
        operation other than :meth:`shrink`.  Typically, revoke should be
        called by any player that detects a communication failure, to initiate
        a recovery phase.
        """
        self._log.debug(f"revoke()")

        self._require_running()

        # Notify all players that the communicator is revoked.
        for rank in self.ranks:
            try:
                self._send(tag="revoke", payload=None, dst=rank)
            except Exception as e: # pragma: no cover
                # We handle this here instead of propagating it to the
                # application layer because we expect some recipients to be
                # missing, else there'd be no reason to call revoke().
                self._log.error(f"timeout revoking player {rank}.")


    @staticmethod
    def run(*, world_size, fn, identities=None, trusted=None, args=(), kwargs={}, name="world", timeout=5, startup_timeout=5):
        """Run a function in parallel using sub-processes on the local host.

        This is extremely useful for running examples and regression tests on one machine.

        The given function *must* accept a communicator as its first
        argument.  Additional positional and keyword arguments may follow the
        communicator.

        To run computations across multiple hosts, you should use the
        :ref:`cicada` command line executable instead.

        Parameters
        ----------
        world_size: :class:`int`, required
            The number of players that will run the function.
        fn: :func:`callable`, required
            The function to execute in parallel.
        identities: sequence of :class:`str`, optional
            Path to files in PEM format each containing a private key and a certificate, one per player.
        trusted: sequence of :class:`str`, optional
            Path to files in PEM format containing certificates.
        args: :class:`tuple`, optional
            Positional arguments to pass to `fn` when it is executed.
        kwargs: :class:`dict`, optional
            Keyword arguments to pass to `fn` when it is executed.
        name: :class:`str`, optional
            Human-readable name for the communicator created by this function.
            Defaults to "world".
        timeout: :class:`numbers.Number`, optional
            Maximum time to wait for normal communication to complete in
            seconds.  Defaults to five seconds.
        startup_timeout: :class:`numbers.Number`, optional
            Maximum time allowed to setup the communicator in seconds.
            Defaults to five seconds.

        Returns
        -------
        results: list
            The return value from the function for each player, in
            rank order.  If a player process terminates unexpectedly, the
            result will be an instance of :class:`Terminated`, which can be
            used to access the process exit code.  If the player process raises
            a Python exception, the result will be an instance of
            :class:`Failed`, which can be used to access the Python exception
            and a traceback of the failing code.
        """
        def launch(*, parent_queue, child_queue, rank, fn, identity, trusted, args, kwargs, name, timeout, startup_timeout):
            # Run the work function.
            try:
                # Create a socket with a randomly-assigned port number.
                timer = Timer(threshold=startup_timeout)
                listen_socket = listen(name=name, rank=rank, address="tcp://127.0.0.1", timer=timer)
                address = geturl(listen_socket)

                # Send our address to the parent process.
                parent_queue.put((rank, address))

                # Get all addresses from the parent process.
                addresses = child_queue.get()

                # Optionally setup TLS.
                if identity and trusted:
                    server = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
                    server.load_cert_chain(certfile=identity)
                    for trust in trusted:
                        server.load_verify_locations(trust)
                    server.check_hostname=False
                    server.verify_mode = ssl.CERT_REQUIRED

                    client = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
                    client.load_cert_chain(certfile=identity)
                    for trust in trusted:
                        client.load_verify_locations(trust)
                    client.check_hostname = False
                    client.verify_mode = ssl.CERT_REQUIRED

                    tls = (server, client)
                else:
                    tls = None

                sockets=direct(listen_socket=listen_socket, addresses=addresses, rank=rank, name=name, timer=timer, tls=tls)
                communicator = SocketCommunicator(sockets=sockets, name=name, timeout=timeout)
                result = fn(communicator, *args, **kwargs)
                communicator.free()
            except Exception as e: # pragma: no cover
                result = Failed(e, traceback.format_exc())

            # Return results to the parent process.
            parent_queue.put((rank, result))

        # Setup the multiprocessing context.
        context = multiprocessing.get_context(method="fork") # I don't remember why we prefer fork().

        # Create queues for IPC.
        parent_queue = context.Queue()
        child_queue = context.Queue()

        # Create per-player processes.
        processes = []
        for rank in range(world_size):
            identity = None if identities is None else identities[rank]
            processes.append(context.Process(
                target=launch,
                kwargs=dict(parent_queue=parent_queue, child_queue=child_queue, rank=rank, fn=fn, identity=identity, trusted=trusted, args=args, name=name, kwargs=kwargs, timeout=timeout, startup_timeout=startup_timeout),
                ))

        # Start per-player processes.
        for process in processes:
            process.daemon = True
            process.start()

        # Collect addresses from every process.
        addresses = [None] * world_size
        for process in processes:
            rank, address = parent_queue.get(block=True)
            addresses[rank] = address

        # Send addresses to every process.
        for process in processes:
            child_queue.put(addresses)

        # Wait until every process terminates.
        for process in processes:
            process.join()

        # Collect a result for every process, but don't block in case
        # there are missing results.
        results = []
        for process in processes:
            try:
                results.append(parent_queue.get(block=False))
            except:
                break

        # Return the output of each rank, in rank order, with a sentinel object for missing outputs.
        output = [Terminated(process.exitcode) for process in processes]
        for rank, result in results:
            output[rank] = result

        # Log the results for each player.
        log = logging.getLogger(__name__)

        for rank, result in enumerate(output):
            if isinstance(result, Failed):
                log.warning(f"Comm {name!r} player {rank} failed: {result.exception!r}")
            elif isinstance(result, Exception):
                log.warning(f"Comm {name!r} player {rank} failed: {result!r}")
            else:
                log.info(f"Comm {name!r} player {rank} result: {result}")

        # Print a traceback for players that failed.
        for rank, result in enumerate(output):
            if isinstance(result, Failed):
                log.error("*" * 80)
                log.error(f"Comm {name!r} player {rank} traceback:")
                log.error(result.traceback)

        return output


    def scatter(self, *, src, values):
        self._log.debug(f"scatter(src={src})")

        self._require_unrevoked()
        self._require_running()

        src = self._require_rank(src)
        if self.rank == src:
            values = [value for value in values]
            if len(values) != self._world_size:
                raise ValueError(f"Expected {self._world_size} values, received {len(values)}.") # pragma: no cover

        # Send data to every player.
        if self.rank == src:
            for value, rank in zip(values, self.ranks):
                self._send(tag="scatter", payload=value, dst=rank)

        # Receive data from the sender.
        message = self._receive(tag="scatter", sender=src, block=True)
        return message.payload


    def scatterv(self, *, src, values, dst):
        self._log.debug(f"scatterv(src={src}, dst={dst})")

        self._require_unrevoked()
        self._require_running()

        src = self._require_rank(src)
        dst = self._require_rank_list(dst)

        if self.rank == src:
            values = [value for value in values]
            if len(values) != len(dst):
                raise ValueError("values must contain one value instance for every destination player.") # pragma: no cover

        # Send data to every destination.
        if self.rank == src:
            for value, rank in zip(values, dst):
                self._send(tag="scatterv", payload=value, dst=rank)

        # Receive data from the sender.
        if self.rank in dst:
            message = self._receive(tag="scatterv", sender=src, block=True)
            return message.payload

        return None


    def send(self, *, value, dst):
        self._log.debug(f"send(dst={dst})")

        self._require_unrevoked()
        self._require_running()

        dst = self._require_rank(dst)

        self._send(tag="send", payload=value, dst=dst)


    def shrink(self, *, name, timeout=5, startup_timeout=5):
        """Create a new communicator containing surviving players.

        This method should be called as part of a failure-recovery phase by as
        many players as possible (ideally, every player still running).  It
        will attempt to rendezvous with the other players and return a new
        communicator, but the process could fail and raise an exception
        instead.  In that case it is up to the application to decide how to
        proceed.

        Parameters
        ----------
        name: :class:`str`, required
            New communicator name.
        timeout: :class:`numbers.Number`, optional
            Maximum time to wait for communication, in seconds.
        startup_timeout: :class:`numbers.Number`, optional
            Maximum time to wait for communicator_setup, in seconds.

        Returns
        -------
        communicator: a new :class:`SocketCommunicator` instance.
        """
        self._log.debug(f"shrink()")

        self._require_running()

        # By default, we assume that everyone is alive.
        remaining_ranks = self.ranks

        # Sort the remaining ranks; the lowest rank will become rank 0 in the new communicator.
        remaining_ranks = sorted(remaining_ranks)

        # Generate a token based on a hash of the remaining ranks that we can
        # use to ensure that every player is in agreement on who's remaining.
        token = hashlib.sha3_256()
        for rank in remaining_ranks:
            token.update(f"rank-{rank}".encode("utf8"))
        token = token.hexdigest()

        # Generate new connection information.
        world_size=len(remaining_ranks)
        rank = remaining_ranks.index(self.rank)

        # Create a new socket with a randomly-assigned port number.
        address = urllib.parse.urlparse(geturl(next(iter(self._players.values()))))
        if address.scheme != "tcp":
            raise ValueError(f"Comm {self.name!r} player {self.rank} only communicators using TCP sockets can shrink.") # pragma: no cover

        listen_socket = socket.create_server((address.hostname, 0))
        address = geturl(listen_socket)

        if self.rank == remaining_ranks[0]:
            for remaining_rank in remaining_ranks:
                self._send(tag="shrink-end", payload=address, dst=remaining_rank)
        root_address = self._receive(tag="shrink-end", sender=remaining_ranks[0], block=True).payload

        timer = Timer(threshold=startup_timeout)
        sockets=rendezvous(listen_socket=listen_socket, root_address=root_address, world_size=world_size, rank=rank, name=name, token=token, timer=timer)
        return SocketCommunicator(sockets=sockets, name=name, timeout=timeout), remaining_ranks


    def split(self, *, name, timeout=5, startup_timeout=5):
        """Return a new communicator with the given name.

        If players specify different names - which can be any :class:`str`
        - then a new communicator will be created for each unique name, with
        those players as members.  If a player supplies a name of `None`,
        they will not be a part of any communicator, and this method will
        return `None`.

        .. note::
            This is a collective operation that *must* be called by every member
            of the communicator, even if they aren't going to be a member of any
            of the resulting groups!

        Parameters
        ----------
        name: :class:`str` or :any:`None`, required
            Communicator name, or `None`.
        timeout: :class:`numbers.Number`, optional
            Maximum time to wait for communication, in seconds.
        startup_timeout: :class:`numbers.Number`, optional
            Maximum time to wait for communicator setup, in seconds.

        Returns
        -------
        communicator: a new :class:`SocketCommunicator` instance, or `None`
        """
        self._log.debug(f"split(name={name})")

        self._require_unrevoked()
        self._require_running()

        if not isinstance(name, (str, type(None))):
            raise ValueError(f"Comm {self.name!r} player {self.rank} name must be a string or None, got {name} instead.") # pragma: no cover

        # Create a new socket with a randomly-assigned port number.
        if name is not None:
            address = urllib.parse.urlparse(geturl(next(iter(self._players.values()))))
            if address.scheme != "tcp":
                raise ValueError(f"Comm {self.name!r} player {self.rank} only communicators using TCP sockets can be split.") # pragma: no cover

            listen_socket = socket.create_server((address.hostname, 0))
            address = geturl(listen_socket)
        else:
            address = None

        # Send names and addresses to rank 0.
        addresses = self.gather(value=(name, address), dst=0)

        # Compute new communicator parameters.
        if self.rank == 0:
            groups = collections.defaultdict(list)
            for rank, (name, address) in enumerate(addresses):
                groups[name].append((rank, address))

            players = []
            for rank, (name, address) in enumerate(addresses):
                group = sorted(groups[name])
                ranks, addresses = zip(*group)
                players.append((name, len(group), ranks.index(rank), addresses))
        else:
            players = None

        # Send new connection info to all players.
        group_name, group_world_size, group_rank, group_addresses = self.scatter(src=0, values=players)

        # Return a new communicator.
        if group_name is not None:
            timer = Timer(threshold=startup_timeout)
            sockets = direct(listen_socket=listen_socket, addresses=group_addresses, rank=group_rank, name=group_name, timer=timer)
            return SocketCommunicator(sockets=sockets, name=group_name, timeout=timeout)

        return None


    @property
    def stats(self):
        """Nested dict containing communication statistics for logging / debugging."""
        totals = {
            "sent": {"bytes": 0, "messages": 0},
            "received": {"bytes": 0, "messages": 0},
        }
        for rank, player in self._players.items():
            stats = player.stats
            totals[rank] = stats
            totals["sent"]["bytes"] += stats["sent"]["bytes"]
            totals["sent"]["messages"] += stats["sent"]["messages"]
            totals["received"]["bytes"] += stats["received"]["bytes"]
            totals["received"]["messages"] += stats["received"]["messages"]
        return totals


    @property
    def timeout(self):
        """Amount of time allowed for communications to complete, in seconds.

        Returns
        -------
        timeout: :class:`numbers.Number`.
            The timeout in seconds.
        """
        return self._timeout


    @timeout.setter
    def timeout(self, timeout):
        self._timeout = timeout


    @property
    def world_size(self):
        return self._world_size


