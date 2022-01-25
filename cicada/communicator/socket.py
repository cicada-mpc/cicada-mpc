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
import functools
import hashlib
import logging
import math
import multiprocessing
import numbers
import os
import pickle
import queue
import select
import socket
import threading
import time
import traceback
import urllib.parse

import numpy
import pynetstring

from .interface import Communicator
import cicada
import cicada.bind

log = logging.getLogger(__name__)

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


class LoggerAdapter(logging.LoggerAdapter):
    """Wraps a Python logger for consistent formatting of communicator log entries.

    logger: :class:`logging.Logger`, required
        Python logger to wrap.
    name: class:`str`, required
        Communicator name.
    rank: class:`int`, required
        Communicator rank
    """
    def __init__(self, logger, name, rank):
        super().__init__(logger, extra={"name": name, "rank": rank})

    def process(self, msg, kwargs):
        return f"Comm {self.extra['name']!r} player {self.extra['rank']} {msg}", kwargs


class NetstringSocket(object):
    """Message-oriented socket that uses the Netstrings protocol."""
    def __init__(self, sock):
        self._socket = sock
        self._decoder = pynetstring.Decoder()
        self._decoded = []
        self._sent_bytes = 0
        self._sent_messages = 0
        self._received_bytes = 0
        self._received_messages = 0

    def close(self):
        """Close the underlying socket."""
        self._socket.close()

    def feed(self):
        """Read data from the underlying socket, decoding whatever is available."""
        raw = self._socket.recv(4096)
        decoded = self._decoder.feed(raw)
        self._received_bytes += len(raw)
        self._received_messages += len(decoded)
        self._decoded += decoded

    def fileno(self):
        """Return the file descriptor for the underlying socket.

        This allows :class:`NetstringSocket` to be used with :func:`select.select`.
        """
        return self._socket.fileno()

    def received(self):
        """Return every message that has been received, if any."""
        result = self._decoded
        self._decoded = []
        return result

    def receive_one(self):
        """Block until at least one message has been received."""
        while not self._decoded:
            self.feed()
        return self._decoded.pop(0)

    def send(self, msg):
        """Send a message."""
        raw = pynetstring.encode(msg)
        self._socket.sendall(raw)
        self._sent_bytes += len(raw)
        self._sent_messages += 1

    @property
    def stats(self):
        """Return a :class:`dict` containing statistics.

        Returns the number of bytes and messages that have been sent and received.
        """
        return {
            "sent": {"bytes": self._sent_bytes, "messages": self._sent_messages},
            "received": {"bytes": self._received_bytes, "messages": self._received_messages},
            }


class Revoked(Exception):
    """Raised calling an operation after the communicator has been revoked."""
    pass


class Terminated(Exception):
    """Used to indicate that a player process terminated unexpectedly without output."""
    def __init__(self, exitcode):
        self.exitcode = exitcode

    def __repr__(self):
        return f"Terminated(exitcode={self.exitcode!r})" # pragma: no cover


class Timeout(Exception):
    """Raised when an operation has timed-out."""
    pass


class Timer(object):
    """Tracks elapsed time.

    Parameters
    ----------
    threshold: number, required
        The maximum of number of elapsed seconds before this timer will be expired.
    """
    def __init__(self, threshold):
        self._start = time.time()
        self._threshold = threshold

    @property
    def elapsed(self):
        """Return the number of seconds since the :class:`Timer` was created."""
        return time.time() - self._start


    @property
    def expired(self):
        """Returns :any:`True` if the elapsed time has exceeded a threshold."""
        if self._threshold and (self.elapsed > self._threshold):
            return True
        return False


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
    name: string, optional
        The name of this communicator, which is used strictly for logging
        and debugging.  If unspecified the default is "world".
    world_size: integer, optional
        The number of players that will be members of this communicator.
        Defaults to the value of the WORLD_SIZE environment variable.
    link_addr: string, optional
        URL address of the root (rank 0) player.  The URL scheme *must* be
        `tcp`, and the address must be reachable by all of the other players.
        Defaults to the value of the LINK_ADDR environment variable.
    rank: integer, optional
        The rank of the local player, in the range [0, world_size).  Defaults
        to the value of the RANK environment variable.
    host_addr: string, optional
        URL address of the local player.  The URL scheme *must* be `tcp` and
        the address must be reachable by all of the other players.  Defaults to
        the address of host_socket if supplied, or the value of the HOST_ADDR
        environment variable.  Note that this value is ignored by the root
        player.
    host_socket: :class:`socket.socket`, optional
        Callers may optionally provide an existing socket for use by the
        communicator.  The provided socket *must* be created using `AF_INET`
        and `SOCK_STREAM`, and be bound to the same address and port specified
        by `host_addr`.
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


    def __init__(self, *, name=None, world_size=None, rank=None, link_addr=None, host_addr=None, host_socket=None, token=0, timeout=5, setup_timeout=5):
        # Enforce preconditions
        if name is None:
            name = "world"
        if not isinstance(name, str):
            raise ValueError("name must be a string, got {name} instead.") # pragma: no cover

        if world_size is None:
            world_size = int(os.environ["WORLD_SIZE"])
        if not isinstance(world_size, int):
            raise ValueError("world_size must be an integer, got {world_size} instead.") # pragma: no cover
        if not world_size > 0:
            raise ValueError("world_size must be an integer greater than zero, got {world_size} instead.") # pragma: no cover

        if rank is None:
            rank = int(os.environ["RANK"])
        if not isinstance(rank, int):
            raise ValueError("rank must be an integer, got {rank} instead.") # pragma: no cover
        if not (0 <= rank and rank < world_size):
            raise ValueError(f"rank must be in the range [0, {world_size}), got {rank} instead.") # pragma: no cover

        if link_addr is None:
            link_addr = os.environ["LINK_ADDR"]
        link_addr = urllib.parse.urlparse(link_addr)
        if link_addr.scheme != "tcp":
            raise ValueError("link_addr scheme must be tcp, got {link_addr.scheme} instead.") # pragma: no cover
        if link_addr.hostname is None:
            raise ValueError("link_addr hostname must be specified.") # pragma: no cover
        if link_addr.port is None:
            raise ValueError("link_addr port must be specified.") # pragma: no cover

        if host_addr is not None and host_socket is not None:
            raise ValueError("Specify host_addr or host_socket, but not both.") # pragma: no cover
        if host_addr is None and host_socket is not None:
            hostname, port = host_socket.getsockname()
            host_addr = f"tcp://{hostname}:{port}"
        if host_addr is None and host_socket is None:
            host_addr = os.environ["HOST_ADDR"]
        host_addr = urllib.parse.urlparse(host_addr)
        if host_addr.scheme != "tcp":
            raise ValueError("host_addr scheme must be tcp, got {host_addr.scheme} instead.") # pragma: no cover
        if host_addr.hostname is None:
            raise ValueError("host_addr hostname must be specified.") # pragma: no cover
        if host_addr.port is None:
            raise ValueError("host_addr port must be specified.") # pragma: no cover
        if rank == 0 and host_addr != link_addr:
            raise ValueError(f"Player 0 link_addr {link_addr} and host_addr {host_addr} must match.") # pragma: no cover

        if not isinstance(host_socket, (socket.socket, type(None))):
            raise ValueError(f"host_socket must be an instance of socket.socket or None.") # pragma: no cover
        if host_socket is not None and host_socket.family != socket.AF_INET:
            raise ValueError(f"host_socket must use AF_INET.") # pragma: no cover
        if host_socket is not None and host_socket.type != socket.SOCK_STREAM:
            raise ValueError(f"host_socket must use SOCK_STREAM.") # pragma: no cover
        if host_socket is not None and host_socket.getsockname()[0] != host_addr.hostname:
            raise ValueError(f"host_socket hostname must match host_addr.") # pragma: no cover
        if host_socket is not None and host_socket.getsockname()[1] != host_addr.port:
            raise ValueError(f"host_socket port must match host_addr.") # pragma: no cover

        if not isinstance(timeout, (numbers.Number, type(None))):
            raise ValueError(f"timeout must be a number or None, got {timeout} instead.") # pragma: no cover
        if not isinstance(setup_timeout, (numbers.Number, type(None))):
            raise ValueError(f"setup_timeout must be a number or None, got {setup_timeout} instead.") # pragma: no cover

        # Setup internal state.
        self._name = name
        self._world_size = world_size
        self._rank = rank
        self._host_addr = host_addr
        self._timeout = timeout
        self._setup_timeout = setup_timeout
        self._revoked = False
        self._log = LoggerAdapter(log, name, rank)

        # Set aside storage for connections to the other players.
        self._players = {}

        # Track elapsed time during setup.
        timer = Timer(threshold=setup_timeout)

        # Rendezvous with the other players.
        self._log.info(f"rendezvous with {link_addr.geturl()} from {host_addr.geturl()}.")

        ###########################################################################
        # Phase 1: Every player sets-up a socket to listen for connections.

        if host_socket is None:
            while True:
                if timer.expired:
                    raise Timeout(f"Comm {name!r} player {rank} timeout creating host socket.")

                try:
                    host_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    host_socket.bind((host_addr.hostname, host_addr.port or 0))
                    break
                except Exception as e:
                    self._log.warning(f"exception creating host socket: {e}")
                    time.sleep(0.1)

        host_socket.listen(world_size)
        self._log.debug(f"listening for connections.")

        ###########################################################################
        # Phase 2: Every player (except root) makes a connection to root.

        if rank != 0:
            while True:
                if timer.expired:
                    raise Timeout(f"Comm {name!r} player {rank} timeout connecting to player 0.")

                try:
                    other_player = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    other_player.connect((link_addr.hostname, link_addr.port))
                    other_player = NetstringSocket(other_player)
                    self._players[0] = other_player
                    break
                except Exception as e:
                    self._log.warning(f"exception connecting to player 0: {e}")
                    time.sleep(0.1)

        ###########################################################################
        # Phase 3: Every player sends their listening address to root.

        if rank != 0:
            while True:
                if timer.expired:
                    raise Timeout(f"Comm {name!r} player {rank} timeout sending address to player 0.")

                try:
                    self._players[0].send(pickle.dumps((rank, host_addr, token)))
                    break
                except Exception as e:
                    self._log.warning(f"exception sending address to player 0: {e}")
                    time.sleep(0.1)

        ###########################################################################
        # Phase 4: Root gathers addresses from every player.

        if rank == 0:
            # Gather an address from every player.
            addresses = {rank: host_addr}
            while len(addresses) < world_size:
                other_player, _ = host_socket.accept()
                other_player = NetstringSocket(other_player)
                other_rank, other_addr, other_token = pickle.loads(other_player.receive_one())
                self._players[other_rank] = other_player
                addresses[other_rank] = other_addr
                self._log.debug(f"received address from player {other_rank}.")

#                if other_token != token:
#                    raise RuntimeError(f"Comm {self._name!r} player {self._rank} expected token {token}, received {other_token} from player {other_rank}.")

        ###########################################################################
        # Phase 5: Root broadcasts the set of all addresses to every player.

        if rank == 0:
            for player in self._players.values():
                player.send(pickle.dumps(addresses))

        ###########################################################################
        # Phase 6: Every player receives the set of all addresses from root.

        if rank != 0:
            while True:
                if timer.expired:
                    raise Timeout(f"Comm {name!r} player {rank} timeout waiting for addresses from player 0.")

                try:
                    addresses = pickle.loads(self._players[0].receive_one())
                    self._log.debug(f"received addresses from player 0.")
                    break
                except Exception as e:
                    self._log.warning(f"exception getting addresses from player 0: {e}")
                    time.sleep(0.1)

        ###########################################################################
        # Phase 7: Players setup connections with one another.

        for listener in range(1, world_size-1):
            if rank == listener:
                # Listen for connections from the other players.
                while len(self._players) < world_size - 1: # we don't make a connection with ourself.
                    try:
                        other_player, _ = host_socket.accept()
                        other_player = NetstringSocket(other_player)
                        other_rank = pickle.loads(other_player.receive_one())
                        self._players[other_rank] = other_player
                        self._players[other_rank].send("ack")
                    except Exception as e:
                        self._log.warning(f"exception listening for other players: {e}")
                        time.sleep(0.1)

            elif rank > listener:
                while True:
                    if timer.expired:
                        raise Timeout(f"Comm {name!r} player {rank} timeout connecting to player {listener}.")

                    try:
                        # Send our rank to the listening player and listen for an ack.
                        other_player = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        other_player.connect((addresses[listener].hostname, addresses[listener].port))
                        other_player = NetstringSocket(other_player)
                        self._players[listener] = other_player

                        self._players[listener].send(pickle.dumps(rank))
                        ack = self._players[listener].receive_one()
                        break
                    except Exception as e:
                        self._log.warning(f"exception connecting to player {listener}: {e}")
                        time.sleep(0.5)

        ###########################################################################
        # Phase 8: The mesh has been initialized, setup normal operation.

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

#        # Log information about our peers.
#        for rank, player in sorted(self._players.items()):
#            host, port = player.getsockname()
#            otherhost, otherport = player.getpeername()
#            self._log.debug(f"tcp://{host}:{port} connected to player {rank} tcp://{otherhost}:{otherport}.")

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
                self._log.error(f"dropping unexpected message: {message} exception: {e}")
                continue

            # Log queued messages.
            if self._log.isEnabledFor(logging.DEBUG):
                self._log.debug(f"<-- player {message.sender} {message.tag}#{message.serial:04}")

            # Revoke messages don't get queued because they receive special handling.
            if message.tag == "revoke":
                if not self._revoked:
                    self._revoked = True
                    self._log.info(f"revoked by player {message.sender}")
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
                    for raw_message in player.received():
                        # Ignore unparsable messages.
                        try:
                            message = pickle.loads(raw_message)
                        except Exception as e: # pragma: no cover
                            self._log.error(f"ignoring unparsable message: {e}")
                            continue

                        self._log.debug(f"received {message}")

                        # Insert the message into the incoming queue.
                        self._incoming.put(message, block=True, timeout=None)
            except Exception as e:
                self._log.error(f"receive exception: {e}")

        # The communicator has been freed, so exit the thread.
        self._log.debug(f"receive thread closed.")



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
#            except pynng.exceptions.Timeout:
#                self._log.error(f"tag {message.tag!r} to receiver {dst} timed-out after {self._timeout}s.")
            except Exception as e:
                self._log.error(f"send exception: {e}")


    def all_gather(self, value):
        self._log.debug(f"all_gather()")

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
        self._log.debug(f"barrier()")

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
        self._log.debug(f"broadcast(src={src})")

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
        self._log.debug(f"gatherv(src={src}, dst={dst})")

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
        self._log.debug(f"irecv(src={src})")

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
        self._log.debug(f"isend(dst={dst})")

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


    @property
    def name(self):
        """The name of this communicator, which can be used for logging / debugging.

        Returns
        -------
        name: string
        """
        return self._name


    @contextlib.contextmanager
    def override(self, *, timeout):
        """Temporarily change the timeout value.

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
    def rank(self):
        return self._rank


    def recv(self, *, src):
        self._log.debug(f"recv(src={src})")

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
        self._log.debug(f"revoke()")

        # Notify all players that the communicator is revoked.
        for rank in self.ranks:
            try:
                self._send(tag="revoke", payload=None, dst=rank)
            except Exception as e:
                # We handle this here instead of propagating it to the
                # application layer because we expect some recipients to be
                # missing, else there'd be no reason to call revoke().
                self._log.error(f"timeout revoking player {rank}.")


    @staticmethod
    def run(*, world_size, fn, args=(), kwargs={}, timeout=5, setup_timeout=5):
        """Run a function in parallel using sub-processes on the local host.

        This is extremely useful for running examples and regression tests on one machine.

        The given function *must* accept a communicator as its first
        argument.  Additional positional and keyword arguments may follow the
        communicator.

        To run computations across multiple hosts, you should use the
        :ref:`cicada-exec` command line executable instead.

        Parameters
        ----------
        world_size: :class:`int`, required
            The number of players that will run the function.
        fn: callable object, required
            The function to execute in parallel.
        args: :class:`tuple`, optional
            Positional arguments to pass to `fn` when it is executed.
        kwargs: :class:`dict`, optional
            Keyword arguments to pass to `fn` when it is executed.
        timeout: number or `None`
            Maximum time to wait for normal communication to complete in seconds, or `None` to disable timeouts.
        setup_timeout: number or `None`
            Maximum time allowed to setup the communicator in seconds, or `None` to disable timeouts during setup.

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
        def launch(*, link_addr_queue, result_queue, world_size, rank, fn, args, kwargs, timeout, setup_timeout):
            # Create a socket with a randomly-assigned port number.
            host_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            host_socket.bind(("127.0.0.1", 0))
            host, port = host_socket.getsockname()
            host_addr = f"tcp://{host}:{port}"

            # Send address information to our peers.
            if rank == 0:
                for index in range(world_size):
                    link_addr_queue.put(host_addr)

            link_addr = link_addr_queue.get()

            # Run the work function.
            try:
                communicator = SocketCommunicator(world_size=world_size, link_addr=link_addr, rank=rank, host_socket=host_socket, timeout=timeout, setup_timeout=setup_timeout)
                result = fn(communicator, *args, **kwargs)
                communicator.free()
            except Exception as e: # pragma: no cover
                result = Failed(e, traceback.format_exc())

            # Return results to the parent process.
            result_queue.put((rank, result))

        # Setup the multiprocessing context.
        context = multiprocessing.get_context(method="fork") # I don't remember why we preferred fork().

        # Create queues for IPC.
        link_addr_queue = context.Queue()
        result_queue = context.Queue()

        # Create per-player processes.
        processes = []
        for rank in range(world_size):
            processes.append(context.Process(
                target=launch,
                kwargs=dict(link_addr_queue=link_addr_queue, result_queue=result_queue, world_size=world_size, rank=rank, fn=fn, args=args, kwargs=kwargs, timeout=timeout, setup_timeout=setup_timeout),
                ))

        # Start per-player processes.
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
                results.append(result_queue.get(block=False))
            except:
                break

        # Return the output of each rank, in rank order, with a sentinel object for missing outputs.
        output = [Terminated(process.exitcode) for process in processes]
        for rank, result in results:
            output[rank] = result

        # Log the results for each player.
        for rank, result in enumerate(output):
            if isinstance(result, Failed):
                log.info(f"Player {rank} failed: {result.exception!r}")
            elif isinstance(result, Exception):
                log.info(f"Player {rank} failed: {result!r}")
            else:
                log.info(f"Player {rank} return: {result}")

        # Print a traceback for players that failed.
        for rank, result in enumerate(output):
            if isinstance(result, Failed):
                log.error("*" * 80)
                log.error(f"Player {rank} traceback:")
                log.error(result.traceback)

        return output


    def scatter(self, *, src, values):
        self._log.debug(f"scatter(src={src})")

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
        self._log.debug(f"scatterv(src={src}, dst={dst})")

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
        self._log.debug(f"send(dst={dst})")

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
        self._log.debug(f"shrink()")

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
                    self._log.debug(f"exception {e}")
            if time.time() - start > timeout:
                break
            time.sleep(0.1)

        # Sort the remaining ranks; the lowest rank will become rank 0 in the new communicator.
        remaining_ranks = sorted(list(remaining_ranks))
        #self._log.info(f"remaining players: {remaining_ranks}")

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

        return SocketCommunicator(name=name, world_size=new_world_size, rank=new_rank, link_addr=new_link_addr, host_addr=new_host_addr, token=token), remaining_ranks


    def split(self, *, name):
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

        Returns
        -------
        communicator: a new :class:`SocketCommunicator` instance, or `None`
        """
        self._log.debug(f"split(name={name})")

        self._require_unrevoked()

        if not isinstance(name, (str, type(None))):
            raise ValueError(f"name must be a string or None, got {name} instead.") # pragma: no cover

        # Create a new socket with a randomly-assigned port number.
        if name is not None:
            host_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            host_socket.bind((self._host_addr.hostname, 0))
            host, port = host_socket.getsockname()

            my_name = name
            my_host_addr = f"tcp://{host}:{port}"
        else:
            my_name = None
            my_host_addr = None

        # Send names and addresses to rank 0.
        self._send(tag="split-prepare", payload=(my_name, my_host_addr), dst=0)

        # Collect name membership information from all players and compute new communicator parameters.
        if self.rank == 0:
            messages = [self._receive(tag="split-prepare", sender=rank, block=True) for rank in self.ranks]
            new_names = [message.payload[0] for message in messages]
            new_host_addrs = [message.payload[1] for message in messages]

            new_world_sizes = collections.Counter()
            new_ranks = []
            for new_name in new_names:
                new_ranks.append(new_world_sizes[new_name])
                new_world_sizes[new_name] += 1

            new_world_sizes = [new_world_sizes[new_name] for new_name in new_names]

            new_link_addrs = {}
            for new_name, new_host_addr in zip(new_names, new_host_addrs):
                if new_name not in new_link_addrs:
                    new_link_addrs[new_name] = new_host_addr
            new_link_addrs = [new_link_addrs[new_name] for new_name in new_names]

        # Send name, world_size, rank, and link_addr to all players.
        if self.rank == 0:
            for dst, (new_name, new_world_size, new_rank, new_link_addr) in enumerate(zip(new_names, new_world_sizes, new_ranks, new_link_addrs)):
                self._send(tag="split", payload=(new_name, new_world_size, new_rank, new_link_addr), dst=dst)

        # Collect name information.
        new_name, new_world_size, new_rank, new_link_addr = self._receive(tag="split", sender=0, block=True).payload
        # Return a new communicator.
        if new_name is not None:
            return SocketCommunicator(name=new_name, world_size=new_world_size, rank=new_rank, link_addr=new_link_addr, host_socket=host_socket, timeout=self._timeout, setup_timeout=self._setup_timeout)

        return None


    @property
    def stats(self):
        """Nested dict containing communication statistics for logging / debugging."""
        totals = {
            "sent": {"bytes": 0, "messages": 0},
            "received": {"bytes": 0, "messages": 0},
        }
        for player in self._players.values():
            stats = player.stats
            totals["sent"]["bytes"] += stats["sent"]["bytes"]
            totals["sent"]["messages"] += stats["sent"]["messages"]
            totals["received"]["bytes"] += stats["received"]["bytes"]
            totals["received"]["messages"] += stats["received"]["messages"]
        return totals


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


    @property
    def world_size(self):
        return self._world_size


