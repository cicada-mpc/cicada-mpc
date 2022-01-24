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

"""Functionality for communicating using NNG, see https://pynng.readthedocs.io.

.. deprecated:: 0.2.0
   Use :mod:`cicada.communicator.socket` instead.

"""

import collections
import contextlib
import functools
import hashlib
import itertools
import logging
import math
import multiprocessing
import numbers
import os
import pickle
import queue
import threading
import time
import traceback
import warnings

import numpy
import pynng

from .interface import Communicator
import cicada
import cicada.bind

log = logging.getLogger(__name__)
logging.getLogger("pynng.nng").setLevel(logging.INFO)

Message = collections.namedtuple("Message", ["serial", "tag", "sender", "payload"])
Message.__doc__ = """
Wrapper class for messages sent between processes.
"""

def nng_timeout(value):
    """Convert a timeout in seconds to an NNG timeout."""
    return -1 if value is None else int(float(value) * 1000.0)


class Failed(Exception):
    """Used to indicate that a player process raised an exception."""
    def __init__(self, exception, traceback):
        self.exception = exception
        self.traceback = traceback

    def __repr__(self):
        return f"Failed(exception={self.exception!r})" # pragma: no cover


class Terminated(Exception):
    """Used to indicate that a player process terminated unexpectedly without output."""
    def __init__(self, exitcode):
        self.exitcode = exitcode

    def __repr__(self):
        return f"Terminated(exitcode={self.exitcode!r})" # pragma: no cover


class Revoked(Exception):
    """Raised calling an operation after the communicator has been revoked."""
    pass


class Timeout(Exception):
    """Raised when a blocking operation has timed-out."""
    pass


class TryAgain(Exception):
    """Raised when a non-blocking operation would block."""
    pass


class NNGCommunicator(Communicator):
    """Cicada communicator that uses pynng (https://pynng.readthedocs.io) as the transport layer.

    .. deprecated:: 0.2.0
       Use :class:`cicada.communicator.socket.SocketCommunicator` instead.

    Note
    ----
    Creating a communicator is a collective operation that must be called by
    all players that will be members.

    Parameters
    ----------
    name: string, optional
        The name of this communicator, which is used strictly for logging
        and debugging.  If unspecified the default is "world".
    world_size: integer, optional
        The number of players that will be members of this communicator.
        Defaults to the value of the WORLD_SIZE environment variable.
    link_addr: string, optional
        NNG address of the root (rank 0) player.  This address must be
        publically accessible to all of the other players.  Defaults to the
        value of the LINK_ADDR environment variable.
    rank: integer, optional
        The rank of the local player, in the range [0, world_size).  Defaults
        to the value of the RANK environment variable.
    host_addr: string, optional
        NNG address of the local player.  This address must be publically
        accessible to all of the other players.  Defaults to the value of the
        HOST_ADDR environment variable.  Note that this value is ignored
        by the root player.
    timeout: number or `None`
        Maximum time to wait for normal communication to complete in seconds, or `None` to disable timeouts.
    setup_timeout: number or `None`
        Maximum time allowed to setup the communicator in seconds, or `None` to disable timeouts during setup.
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
        "shrink-enter",
        "shrink-exit",
        "split",
        "split-prepare",
        ]

    class _Done(object):
        """Sentinel message used to shut-down the queueing thread."""
        pass

    def __init__(self, *, name=None, world_size=None, rank=None, link_addr=None, host_addr=None, token=0, timeout=5, setup_timeout=5):
        warnings.warn("cicada.communicator.nng.NNGCommunicator is deprecated, use cicada.communicator.socket.SocketCommunicator instead.", cicada.DeprecationWarning, stacklevel=2)
        # Setup defaults.
        if name is None:
            name = "world"
        if world_size is None:
            world_size = int(os.environ["WORLD_SIZE"])
        if rank is None:
            rank = int(os.environ["RANK"])
        if link_addr is None:
            link_addr = os.environ["LINK_ADDR"]
        if host_addr is None:
            host_addr = os.environ["HOST_ADDR"]

        # Enforce preconditions.
        if not isinstance(world_size, int):
            raise ValueError("world_size must be an integer.") # pragma: no cover
        if not world_size > 0:
            raise ValueError("world_size must be an integer greater than zero.") # pragma: no cover
        if not isinstance(rank, int):
            raise ValueError("rank must be an integer.") # pragma: no cover
        if not (0 <= rank and rank < world_size):
            raise ValueError(f"rank must be in the range [0, {world_size}).") # pragma: no cover
        if not isinstance(link_addr, str):
            raise ValueError("link_addr must be an NNG address string.") # pragma: no cover
        if not isinstance(host_addr, str):
            raise ValueError("host_addr must be an NNG address string.") # pragma: no cover
        if rank == 0 and link_addr != host_addr:
            raise ValueError(f"link_addr {link_addr} and host_addr {host_addr} must match for rank 0.") # pragma: no cover

        # Setup the player's receiving socket.
        self._receiver = pynng.Rep0(listen=host_addr, recv_timeout=nng_timeout(setup_timeout))
        log.info(f"Player {rank} rendezvous with {link_addr} from {host_addr}.")

        # Rank 0 waits for every player to send their address.
        if rank == 0:
            remaining_ranks = set(range(1, world_size))
            addresses = [(rank, host_addr)]

            for index in range(1, world_size):
                other_rank, other_host_addr, other_token = pickle.loads(self._receiver.recv())
                self._receiver.send(b"ok")

                if other_token != token:
                    raise RuntimeError(f"Player {rank} expected token {token}, received {other_token} from player {other_rank}.")
                addresses.append((other_rank, other_host_addr))

            # Setup sockets for sending to the other players.
            addresses = [address for rank, address in sorted(addresses)]
            self._players = [pynng.Req0(dial=address) for address in addresses]

            # Send addresses back to the other players.
            for player in self._players[1:]:
                player.send(pickle.dumps(addresses))
                player.recv()

        # All players send their address to rank 0.
        if rank != 0:
            with pynng.Req0(dial=link_addr, send_timeout=nng_timeout(setup_timeout)) as link:
                link.send(pickle.dumps((rank, host_addr, token)))
                link.recv()

            addresses = pickle.loads(self._receiver.recv())
            self._receiver.send(b"ok")

            # Setup sockets for sending to the other players.
            self._players = [pynng.Req0(dial=address) for address in addresses]

        # We don't want a timeout for the receiving socket.
        self._receiver.recv_timeout = nng_timeout(None)

        self._name = name
        self._world_size = world_size
        self._link_addr = link_addr
        self._rank = rank
        self._host_addr = host_addr
        self._timeout = timeout
        self._revoked = False

        self._send_serial = 0

        self._stats = {
             "bytes": {
                 "sent": {
                     "total": 0,
                 },
                 "received": {
                     "total": 0,
                 },
             },
            "messages": {
                "sent": {
                    "total": 0,
                },
                "received": {
                    "total": 0,
                    },
                },
        }

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
        self._receiving_thread = threading.Thread(name="Incoming", target=self._receive_messages, daemon=True)
        self._receiving_thread.start()

        self._freed = False

        log.info(f"Comm {self.name!r} player {self._rank} communicator ready.")

    def _queue_messages(self):
        # Place incoming messages in the correct queue.
        while True:
            # Wait for the next incoming message.
            message = self._incoming.get(block=True, timeout=None)

            # If the communicator has been freed, exit the thread.
            if isinstance(message, NNGCommunicator._Done):
                return

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
                log.error(f"Comm {self.name!r} player {self.rank} dropping unexpected message: {e}")
                continue

            # Log received messages.
            if log.isEnabledFor(logging.DEBUG):
                log.debug(f"Comm {self.name!r} player {self.rank} <-- player {message.sender} {message.tag}#{message.serial:04}")

            # Revoke messages don't get queued because they receive special handling.
            if message.tag == "revoke":
                if not self._revoked:
                    self._revoked = True
                    log.info(f"Comm {self.name!r} player {self.rank} revoked by player {message.sender}")
                continue

            # Insert the message into the correct queue.
            self._receive_queues[message.tag][message.sender].put(message, block=True, timeout=None)


    def _receive_messages(self):
        # Parse and queue incoming messages as they arrive.
        while True:
            try:
                # Wait for a message to arrive from the pynng socket.
                raw_message = self._receiver.recv(block=True)
                self._receiver.send(b"ok")

                # Update statistics.
                self._stats["bytes"]["received"]["total"] += len(raw_message)
                self._stats["messages"]["received"]["total"] += 1

                # Ignore unparsable messages.
                try:
                    message = pickle.loads(raw_message)
                except Exception as e: # pragma: no cover
                    log.error(f"Comm {self.name!r} player {self.rank} ignoring unparsable message: {e}")
                    continue

                # Insert the message into the incoming queue.
                self._incoming.put(message, block=True, timeout=None)
            except pynng.exceptions.Closed:
                # The communicator has been freed, so exit the thread.
                log.debug(f"Comm {self.name!r} player {self.rank} receiving socket closed.")
                break


    def _receive(self, *, tag, sender, block):
        try:
            return self._receive_queues[tag][sender].get(block=block, timeout=self._timeout)
        except queue.Empty:
            if block:
                raise Timeout(f"Tag {tag!r} from sender {sender} timed-out after {self._timeout}s")
            else:
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


    def _require_value(self, value):
        return value


    def _require_optional_value(self, value):
        return value


    def _require_unrevoked(self):
        if self._revoked:
            raise Revoked(f"Comm {self.name!r} player {self.rank} revoked.")


    def _send(self, *, tag, payload, dst):
        if tag not in self._tags:
            raise ValueError(f"Unknown tag: {tag}") # pragma: no cover
        if dst not in self.ranks:
            raise ValueError(f"Unknown destination: {dst}") # pragma: no cover

        message = Message(self._send_serial, tag, self._rank, payload)
        self._send_serial += 1

        if log.isEnabledFor(logging.DEBUG):
            log.debug(f"Comm {self.name!r} player {self.rank} --> player {dst} {message.tag}#{message.serial:04}") # pragma: no cover

        # As a special-case, route messages sent to ourself directly to the incoming queue.
        if dst == self.rank:
            self._incoming.put(message, block=True, timeout=None)
        # Otherwise, send the message to the appropriate socket.
        else:
            try:
                raw_message = pickle.dumps(message)
                player = self._players[dst]
                player.send_timeout = nng_timeout(self._timeout)
                player.send(raw_message)
                player.recv()
                self._stats["bytes"]["sent"]["total"] += len(raw_message)
                self._stats["messages"]["sent"]["total"] += 1
            except pynng.exceptions.Timeout:
                log.error(f"Comm {self.name!r} player {self.rank} tag {message.tag!r} to receiver {dst} timed-out after {self._timeout}s.")
            except Exception as e:
                log.error(f"Comm {self.name!r} player {self.rank} exception: {e}")


    def all_gather(self, value):
        log.debug(f"Comm {self.name!r} player {self.rank} all_gather()")

        self._require_unrevoked()
        value = self._require_value(value)

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
        log.debug(f"Comm {self.name!r} player {self.rank} barrier()")

        self._require_unrevoked()

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
        log.debug(f"Comm {self.name!r} player {self.rank} broadcast(src={src})")

        self._require_unrevoked()
        src = self._require_rank(src)
        value = self._require_optional_value(value)

        # Broadcast the value to all players.
        if self.rank == src:
            for rank in self.ranks:
                self._send(tag="broadcast", payload=value, dst=rank)

        # Receive the broadcast value.
        message = self._receive(tag="broadcast", sender=src, block=True)
        return message.payload


    def free(self):
        # Calling free() multiple times is a no-op.
        if self._freed:
            return
        self._freed = True

        # Stop receiving.
        self._receiver.close()
        self._receiver = None
        # The following blocks intermittently when doing CI with Github
        # actions, for reasons I don't understand.
        #self._receiving_thread.join()

        # Stop handling incoming messages.
        self._incoming.put(NNGCommunicator._Done())
        self._queueing_thread.join()

        # Close outgoing sockets.
        for player in self._players:
            player.close()
        self._players = None

        log.info(f"Comm {self.name!r} player {self.rank} communicator freed.")


    def gather(self, *, value, dst):
        log.debug(f"Comm {self.name!r} player {self.rank} gather(dst={dst})")

        self._require_unrevoked()
        value = self._require_value(value)
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
        log.debug(f"Comm {self.name!r} player {self.rank} gatherv(src={src}, dst={dst})")

        self._require_unrevoked()
        src = self._require_rank_list(src)
        value = self._require_value(value)
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
        log.debug(f"Comm {self.name!r} player {self.rank} irecv(src={src})")

        self._require_unrevoked()
        src = self._require_rank(src)

        class Result:
            def __init__(self, communicator, sender):
                self._communicator = communicator
                self._sender = sender
                self._message = None

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
                    raise RuntimeError("Call not completed.")
                return self._message.payload

            def wait(self):
                if self._message is None:
                    self._message = self._communicator._receive(tag="send", sender=self._sender, block=True)

        return Result(self, src)


    def isend(self, *, value, dst):
        log.debug(f"Comm {self.name!r} player {self.rank} isend(dst={dst})")

        self._require_unrevoked()
        value = self._require_value(value)
        dst = self._require_rank(dst)

        self._send(tag="send", payload=value, dst=dst)

        # This is safe, because we pickle the value before returning; thus,
        # nothing the caller can do to the value will have unexpected
        # side-effects.
        class Result:
            def is_completed(self):
                return True
            def wait(self):
                pass

        return Result()


    def log_stats(self):
        """Log statistics about the number and size of messages handled by this communicator."""
        messages_sent = self._stats["messages"]["sent"]["total"]
        messages_received = self._stats["messages"]["received"]["total"]
        bytes_sent = self._stats["bytes"]["sent"]["total"]
        bytes_received = self._stats["bytes"]["received"]["total"]

        log.info(f"Comm {self.name!r} player {self._rank} sent {messages_sent} messages / {bytes_sent} bytes, received {messages_received} messages / {bytes_received} bytes.")


    @property
    def name(self):
        """The name of this communicator, which can be used for logging / debugging.

        Returns
        -------
        name: string
        """
        return self._name


    @property
    def rank(self):
        return self._rank


    def recv(self, *, src):
        log.debug(f"Comm {self.name!r} player {self.rank} recv(src={src})")

        self._require_unrevoked()
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
        log.debug(f"Comm {self.name!r} player {self.rank} revoke()")

        # Notify all players that the communicator is revoked.
        for rank in self.ranks:
            try:
                self._send(tag="revoke", payload=None, dst=rank)
            except Exception as e:
                # We handle this here instead of propagating it to the
                # application layer because we expect some recipients to be
                # missing, else there'd be no reason to call revoke().
                log.error(f"Comm {self.name!r} player {self.rank} timeout revoking player {rank}.")


    @staticmethod
    def run(world_size):
        """Decorator for functions that should be run in parallel using sub-processes on the local host.

        This is extremely useful for running examples and regression tests on one machine.

        The decorated function *must* accept a communicator as its first
        argument.  Additional positional and keyword arguments may follow the
        communicator.

        To run computations across multiple hosts, you should use the
        :ref:`cicada-exec` command line executable instead.

        Parameters
        ----------
        world_size: integer, required
            The number of players to run the decorated function.

        Returns
        -------
        results: list
            The return value from the decorated function for each player, in
            rank order.  If a player process terminates unexpectedly, the
            result will be an instance of :class:`Terminated`, which can be
            used to access the process exit code.  If the player process raises
            a Python exception, the result will be an instance of
            :class:`Failed`, which can be used to access the Python exception
            and a traceback of the failing code.
        """
        def launch(*, world_size, link_addr, rank, host_addr, queue, func, args, kwargs):
            log = logging.getLogger(__name__)
            communicator = NNGCommunicator(world_size=world_size, link_addr=link_addr, rank=rank, host_addr=host_addr)
            try:
                result = func(communicator, *args, **kwargs)
                communicator.free()
            except Exception as e: # pragma: no cover
                result = Failed(e, traceback.format_exc())
            queue.put((rank, result))


        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                addresses = []
                for rank in range(world_size):
                    addr = cicada.bind.loopback_ip()
                    port = cicada.bind.random_port(addr)
                    addresses.append(f"tcp://{addr}:{port}")

                context = multiprocessing.get_context(method="fork")

                queue = context.Queue()

                # Start per-player processes.
                processes = []
                for rank in range(world_size):
                    processes.append(context.Process(target=launch, kwargs=dict(world_size=world_size, link_addr=addresses[0], rank=rank, host_addr=addresses[rank], queue=queue, func=func, args=args, kwargs=kwargs)))
                for process in processes:
                    process.daemon = True
                    process.start()

                # Wait until every process terminates.
                for process in processes:
                    process.join()

                # Collect a result for every process, but don't block in case
                # there are missing results.
                results = []
                for process in processes:
                    try:
                        results.append(queue.get(block=False))
                    except:
                        break

                # Return the output of each rank, in rank order, with a sentinel object for missing outputs.
                output = [Terminated(process.exitcode) for process in processes]
                for rank, result in results:
                    output[rank] = result

                # Log the results for each player.
                for rank, result in enumerate(output):
                    if isinstance(result, Failed):
                        log.error(f"Player {rank} failed: {result.exception!r}")
                    elif isinstance(result, Exception):
                        log.error(f"Player {rank} failed: {result!r}")
                    else:
                        log.info(f"Player {rank} returned: {result}")

                # Print a traceback for players that failed.
                for rank, result in enumerate(output):
                    if isinstance(result, Failed):
                        log.error("*" * 80)
                        log.error(f"Player {rank} traceback:")
                        log.error(result.traceback)

                return output


            return wrapper
        return decorator


    def scatter(self, *, src, values):
        log.debug(f"Comm {self.name!r} player {self.rank} scatter(src={src})")

        self._require_unrevoked()
        src = self._require_rank(src)
        if self.rank == src:
            values = [self._require_value(value) for value in values]
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
        log.debug(f"Comm {self.name!r} player {self.rank} scatterv(src={src}, dst={dst})")

        self._require_unrevoked()
        src = self._require_rank(src)
        dst = self._require_rank_list(dst)

        if self.rank == src:
            values = [self._require_value(value) for value in values]
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
        log.debug(f"Comm {self.name!r} player {self.rank} send(dst={dst})")

        self._require_unrevoked()
        value = self._require_value(value)
        dst = self._require_rank(dst)

        self._send(tag="send", payload=value, dst=dst)


    def shrink(self, timeout=None, name=None):
        """Create a new communicator containing surviving players.

        This method should be called as part of a failure-recovery phase by as
        many players as possible (ideally, every player still running).  It
        will attempt to rendezvous with the other players and return a new
        communicator, but the process could fail and raise an exception
        instead.  In that case it is up to the application to decide how to
        proceed.
        """
        log.debug(f"Comm {self.name!r} player {self.rank} shrink()")

        # Set a default timeout of 2 seconds.
        if timeout is None:
            timeout = 2

        # Create a default name for the new communicator.
        if name is None:
            name = f"shrunk_{self.name}"

        # Our goal is to identify which players still exist.
        remaining_ranks = set()

        # Notify players that we're alive.
        for rank in self.ranks:
            self._send(tag="shrink-enter", payload=None, dst=rank)

        # Collect notifications from the other players during a window of time.
        start = time.time()
        while True:
            for rank in self.ranks:
                try:
                    message = self._receive(tag="shrink-enter", sender=rank, block=False)
                    remaining_ranks.add(rank)
                except Exception as e:
                    log.debug(f"Comm {self.name!r} player {self.rank} exception {e}")
            if time.time() - start > timeout:
                break
            time.sleep(0.1)

        # Sort the remaining ranks; the lowest rank will become rank 0 in the new communicator.
        remaining_ranks = sorted(list(remaining_ranks))
        #log.info(f"Comm {self.name!r} player {self.rank} remaining players: {remaining_ranks}")

        # Generate a token based on a hash of the remaining ranks that we can
        # use to ensure that every player is in agreement on who's remaining.
        token = hashlib.sha3_256()
        for rank in remaining_ranks:
            token.update(rank.to_bytes(math.ceil(rank.bit_length() / 8), byteorder="big"))
        token = token.hexdigest()

        # Generate new connection information.
        new_world_size=len(remaining_ranks)
        new_rank = remaining_ranks.index(self.rank)

        protocol, addr = self._host_addr.split("//")
        addr, port = addr.split(":")
        port = cicada.bind.random_port(addr)
        new_host_addr = f"{protocol}//{addr}:{port}"

        if self.rank == remaining_ranks[0]:
            for remaining_rank in remaining_ranks:
                self._send(tag="shrink-exit", payload=new_host_addr, dst=remaining_rank)
        new_link_addr = self._receive(tag="shrink-exit", sender=remaining_ranks[0], block=True).payload

        return NNGCommunicator(name=name, world_size=new_world_size, rank=new_rank, link_addr=new_link_addr, host_addr=new_host_addr, token=token), remaining_ranks


    def split(self, *, group):
        """Partition players into groups, and create new communicators for each.

        Each player supplies a group identifier - which can be any hashable
        Python type (string, integer, etc) - and a new communicator is created
        for each distinct group, with those players as members.  If a player
        supplies `None`, they will not be a part of any group, and this
        method will return `None`.

        .. note::
            This is a collective operation that *must* be called by every member
            of the communicator, even if they aren't going to be a member of any
            of the resulting groups!

        Parameters
        ----------
        group: hashable object, required
            Group identifier, or `None`.

        Returns
        -------
        communicator: a new :class:`Communicator` instance, or `None`
        """
        log.debug(f"Comm {self.name!r} player {self.rank} split(group={group})")

        self._require_unrevoked()

        # Generate a new address.
        protocol, addr = self._host_addr.split("//")
        addr, port = addr.split(":")
        port = cicada.bind.random_port(addr)
        host_addr = f"{protocol}//{addr}:{port}"

        # Send group membership and new address to rank 0.
        my_group = group
        my_host_addr = host_addr
        self._send(tag="split-prepare", payload=(my_group, my_host_addr), dst=0)

        if self.rank == 0:
            # Collect group membership information and new addresses from all players.
            messages = [self._receive(tag="split-prepare", sender=rank, block=True) for rank in self.ranks]
            groups = [message.payload[0] for message in messages]
            host_addrs = [message.payload[1] for message in messages]

            # Identify world_size and link_addr for each group.
            world_sizes = collections.Counter()
            link_addrs = {}
            new_ranks = []
            for group, host_addr in zip(groups, host_addrs):
                new_ranks.append(world_sizes[group])
                world_sizes[group] += 1
                if group not in link_addrs:
                    link_addrs[group] = host_addr

            # Send world_size and link_addr to all players.
            for rank, group, new_rank in zip(self.ranks, groups, new_ranks):
                self._send(tag="split", payload=(world_sizes[group], link_addrs[group], new_rank), dst=rank)

        # Collect group information.
        world_size, link_addr, new_rank = self._receive(tag="split", sender=0, block=True).payload

        # Return a new communicator.
        if my_group is not None:
            return NNGCommunicator(name=my_group, world_size=world_size, rank=new_rank, link_addr=link_addr, host_addr=my_host_addr)


    @property
    def stats(self):
        """Nested dict containing communication statistics for logging / debugging."""
        return self._stats

    @property
    def timeout(self):
        """Amount of time allowed to elapse before blocking communications time-out.

        Returns
        -------
        timeout: number or `None`.
            The timeout in seconds, or `None` if there is no timeout.
        """
        return self._timeout


    @timeout.setter
    def timeout(self, timeout):
        self._timeout = timeout


    @contextlib.contextmanager
    def override(self, *, timeout):
        """Temporarily change send / receive timeout value.

        Parameters
        ----------
        timeout: number or `None`
            The timeout for subsequent send / receive operations, in seconds, or `None` to disable timeouts completely.

        Returns
        -------
        A context manager object that will restore the original timeout value when exited.
        """
        original_timeout, self._timeout = self._timeout, timeout
        try:
            yield original_timeout
        finally:
            self._timeout = original_timeout


    @property
    def world_size(self):
        return self._world_size


