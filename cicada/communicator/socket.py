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
        self._messages = []
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
        messages = self._decoder.feed(raw)
        self._received_bytes += len(raw)
        self._received_messages += len(messages)
        self._messages += messages

    def fileno(self):
        """Return the file descriptor for the underlying socket.

        This allows :class:`NetstringSocket` to be used with :func:`select.select`.
        """
        return self._socket.fileno()

    def messages(self):
        """Return every message that has been received, if any."""
        result = self._messages
        self._messages = []
        return result

    def next_message(self, *, timeout):
        """Return the next available message, if any."""
        if not self._messages:
            ready, _, _ = select.select([self], [], [], timeout)
            if ready:
                self.feed()
        return self._messages.pop(0) if self._messages else None

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


class TokenMismatch(Exception):
    """Raised when players can't agree on a token for communicator creation."""
    pass


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
    name: :class:`str`, optional
        The name of this communicator, which is used strictly for logging
        and debugging.  If unspecified the default is "world".
    world_size: :class:`int`, optional
        The number of players that will be members of this communicator.
        Defaults to the value of the WORLD_SIZE environment variable.
    link_addr: :class:`str`, optional
        URL address of the root (rank 0) player.  The URL scheme *must* be
        `tcp`, and the address must be reachable by all of the other players.
        Defaults to the value of the LINK_ADDR environment variable.
    rank: :class:`int`, optional
        The rank of the local player, in the range [0, world_size).  Defaults
        to the value of the RANK environment variable.
    host_addr: :class:`str`, optional
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
    timeout: :class:`numbers.Number`
        Maximum time to wait for communication to complete, in seconds.
    startup_timeout: :class:`numbers.Number`
        Maximum time to wait for communicator initialization, in seconds.
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
        "split-begin",
        "split-end",
        ]


    def __init__(self, *, name=None, world_size=None, rank=None, link_addr=None, host_addr=None, host_socket=None, token=0, timeout=5, startup_timeout=5):
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
        # We allow the host port to be unspecified on players other than root,
        # in which case we will choose one at random
        if rank == 0:
            if host_addr.port is None:
                raise ValueError("Player 0 host_addr port must be specified.") # pragma: no cover

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

        if not isinstance(timeout, numbers.Number):
            raise ValueError(f"timeout must be a number, got {timeout} instead.") # pragma: no cover
        if not isinstance(startup_timeout, numbers.Number):
            raise ValueError(f"startup_timeout must be a number, got {startup_timeout} instead.") # pragma: no cover

        # Setup internal state.
        self._name = name
        self._world_size = world_size
        self._rank = rank
        self._host_addr = host_addr
        self._timeout = timeout
        self._startup_timeout = startup_timeout
        self._revoked = False
        self._log = LoggerAdapter(log, name, rank)

        self._startup(name=name, world_size=world_size, rank=rank, link_addr=link_addr, host_addr=host_addr, host_socket=host_socket, token=token, timeout=timeout, startup_timeout=startup_timeout)


    def _startup(self, *, name, world_size, rank, link_addr, host_addr, host_socket, token, timeout, startup_timeout):
        # Set aside storage for connections to the other players.
        self._players = {}

        # Track elapsed time during setup.
        timer = Timer(threshold=startup_timeout)

        ###########################################################################
        # Phase 1: Every player sets-up a socket to listen for connections.

        if host_socket is None:
            while not timer.expired:
                try:
                    host_socket = socket.create_server((host_addr.hostname, host_addr.port or 0))
                    break
                except Exception as e: # pragma: no cover
                    self._log.warning(f"exception creating host socket: {e}")
                    time.sleep(0.1)
            else: # pragma: no cover
                raise Timeout(f"Comm {name!r} player {rank} timeout creating host socket.")

        host_socket.setblocking(False)
        host_socket.listen(world_size)
        self._log.debug(f"listening for connections.")

        # Update host_addr to include the (possibly randomly-chosen) port.
        host, port = host_socket.getsockname()
        host_addr = urllib.parse.urlparse(f"tcp://{host}:{port}")
        self._log.info(f"rendezvous with {link_addr.geturl()} from {host_addr.geturl()}")

        ###########################################################################
        # Phase 2: Every player (except root) makes a connection to root.

        if rank != 0:
            while not timer.expired:
                try:
                    other_player = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    other_player.connect((link_addr.hostname, link_addr.port))
                    other_player = NetstringSocket(other_player)
                    self._players[0] = other_player
                    break
                except ConnectionRefusedError as e: # pragma: no cover
                    # This happens regularly, particularly when starting on
                    # separate hosts, so no need to log a warning.
                    time.sleep(0.1)
                except Exception as e: # pragma: no cover
                    self._log.warning(f"exception connecting to player 0: {e}")
                    time.sleep(0.1)
            else: # pragma: no cover
                raise Timeout(f"Comm {name!r} player {rank} timeout connecting to player 0.")

        ###########################################################################
        # Phase 3: Every player sends their listening address to root.

        if rank != 0:
            while not timer.expired:
                try:
                    self._players[0].send(pickle.dumps((rank, host_addr, token)))
                    break
                except Exception as e: # pragma: no cover
                    self._log.warning(f"exception sending address to player 0: {e}")
                    time.sleep(0.1)
            else: # pragma: no cover
                raise Timeout(f"Comm {name!r} player {rank} timeout sending address to player 0.")

        ###########################################################################
        # Phase 4: Root gathers addresses from every player.

        if rank == 0:
            # Accept a connection from every player.
            other_players = []
            while not timer.expired:
                if len(other_players) == world_size - 1: # We don't connect to ourself.
                    break

                try:
                    ready = select.select([host_socket], [], [], 0.1)
                    if ready:
                        other_player, _ = host_socket.accept()
                        other_player = NetstringSocket(other_player)
                        other_players.append(other_player)
                        self._log.debug(f"accepted connection from player.")
                except BlockingIOError as e: # pragma: no cover
                    # This happens regularly, particularly when starting on
                    # separate hosts, so no need to log a warning.
                    time.sleep(0.1)
                except Exception as e: # pragma: no cover
                    self._log.warning(f"exception waiting for connections from other players: {e}")
                    time.sleep(0.1)
            else: # pragma: no cover
                raise Timeout(f"Comm {name!r} player {rank} timeout waiting for player connections.")

            # Collect an address from every player.
            addresses = {rank: (host_addr, token)}
            for other_player in other_players:
                while not timer.expired:
                    try:
                        raw_message = other_player.next_message(timeout=0.1)
                        if raw_message is not None:
                            other_rank, other_addr, other_token = pickle.loads(raw_message)
                            self._players[other_rank] = other_player
                            addresses[other_rank] = (other_addr, other_token)
                            self._log.debug(f"received address from player {other_rank}.")
                            break
                    except Exception as e: # pragma: no cover
                        self._log.warning(f"exception receiving player address: {e}")
                        time.sleep(0.1)
                else: # pragma: no cover
                    raise Timeout(f"Comm {name!r} player {rank} timeout waiting for player address.")

        ###########################################################################
        # Phase 5: Root broadcasts the set of all addresses to every player.

        if rank == 0:
            for player in self._players.values():
                player.send(pickle.dumps(addresses))

        ###########################################################################
        # Phase 6: Every player receives the set of all addresses from root.

        if rank != 0:
            while not timer.expired:
                try:
                    raw_message = self._players[0].next_message(timeout=0.1)
                    if raw_message is not None:
                        addresses = pickle.loads(raw_message)
                        self._log.debug(f"received addresses from player 0.")
                        break
                except Exception as e: # pragma: no cover
                    self._log.warning(f"exception getting addresses from player 0: {e}")
                    time.sleep(0.1)
            else: # pragma: no cover
                raise Timeout(f"Comm {name!r} player {rank} timeout waiting for addresses from player 0.")

        ###########################################################################
        # Phase 7: Every player verifies that all tokens match.

        for other_rank, (other_address, other_token) in addresses.items():
            if other_token != token:
                raise TokenMismatch(f"Comm {self._name!r} player {self._rank} expected token {token!r}, received {other_token!r} from player {other_rank}.")

        ###########################################################################
        # Phase 8: Players setup connections with one another.

        for listener in range(1, world_size-1):
            if rank == listener:
                # Accept connections from higher-rank players.
                other_players = []
                while not timer.expired:
                    if len(other_players) == world_size - rank - 1: # We don't connect to ourself.
                        break

                    try:
                        ready = select.select([host_socket], [], [], 0.1)
                        if ready:
                            other_player, _ = host_socket.accept()
                            other_player = NetstringSocket(other_player)
                            other_players.append(other_player)
                            self._log.debug(f"accepted connection from player.")
                    except Exception as e: # pragma: no cover
                        self._log.warning(f"exception listening for other players: {e}")
                        time.sleep(0.1)

                # Collect ranks from the other players.
                for other_player in other_players:
                    while not timer.expired:
                        try:
                            raw_message = other_player.next_message(timeout=0.1)
                            if raw_message is not None:
                                other_rank = pickle.loads(raw_message)
                                self._players[other_rank] = other_player
                                self._log.debug(f"received rank from player {other_rank}.")
                                break
                        except Exception as e: # pragma: no cover
                            self._log.warning(f"exception receiving player rank.")
                            time.sleep(0.1)
                    else: # pragma: no cover
                        raise Timeout(f"Comm {name!r} player {rank} timeout waiting for player rank.")

            elif rank > listener:
                # Make a connection to the listener.
                while not timer.expired:
                    try:
                        other_player = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        other_player.connect((addresses[listener][0].hostname, addresses[listener][0].port))
                        other_player = NetstringSocket(other_player)
                        self._players[listener] = other_player
                        break
                    except Exception as e: # pragma: no cover
                        self._log.warning(f"exception connecting to player {listener}: {e}")
                        time.sleep(0.5)
                else: # pragma: no cover
                    raise Timeout(f"Comm {name!r} player {rank} timeout connecting to player {listener}.")

                # Send our rank to the listener.
                while not timer.expired:
                    try:
                        self._players[listener].send(pickle.dumps(rank))
                        break
                    except Exception as e: # pragma: no cover
                        self._log.warning(f"exception sending rank to player {listener}: {e}")
                        time.sleep(0.5)
                else: # pragma: no cover
                    raise Timeout(f"Comm {name!r} player {rank} timeout sending rank to player {listener}.")

        ###########################################################################
        # Phase 9: The mesh has been initialized, begin normal operation.

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
                self._log.error(f"dropping unexpected message: {message} exception: {e}")
                continue

            # Log queued messages.
            if self._log.isEnabledFor(logging.DEBUG):
                self._log.debug(f"<-- player {message.sender} {message.tag}#{message.serial:04}") # pragma: no cover

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
                    for raw_message in player.messages():
                        # Ignore unparsable messages.
                        try:
                            message = pickle.loads(raw_message)
                        except Exception as e: # pragma: no cover
                            self._log.error(f"ignoring unparsable message: {e}")
                            continue

                        self._log.debug(f"received {message}")

                        # Insert the message into the incoming queue.
                        self._incoming.put(message, block=True, timeout=None)
            except Exception as e: # pragma: no cover
                self._log.error(f"receive exception: {e}")

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
            except Exception as e: # pragma: no cover
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
        context:
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
            except Exception as e: # pragma: no cover
                # We handle this here instead of propagating it to the
                # application layer because we expect some recipients to be
                # missing, else there'd be no reason to call revoke().
                self._log.error(f"timeout revoking player {rank}.")


    @staticmethod
    def run(*, world_size, fn, args=(), kwargs={}, timeout=5, startup_timeout=5):
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
        startup_timeout: number or `None`
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
        def launch(*, link_addr_queue, result_queue, world_size, rank, fn, args, kwargs, timeout, startup_timeout):
            # Create a socket with a randomly-assigned port number.
            host_socket = socket.create_server((cicada.bind.loopback_ip(), 0))
            host, port = host_socket.getsockname()
            host_addr = f"tcp://{host}:{port}"

            # Send address information to our peers.
            if rank == 0:
                for index in range(world_size):
                    link_addr_queue.put(host_addr)

            link_addr = link_addr_queue.get()

            # Run the work function.
            try:
                communicator = SocketCommunicator(world_size=world_size, link_addr=link_addr, rank=rank, host_socket=host_socket, timeout=timeout, startup_timeout=startup_timeout)
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
                kwargs=dict(link_addr_queue=link_addr_queue, result_queue=result_queue, world_size=world_size, rank=rank, fn=fn, args=args, kwargs=kwargs, timeout=timeout, startup_timeout=startup_timeout),
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


    def shrink(self, *, name):
        """Create a new communicator containing surviving players.

        This method should be called as part of a failure-recovery phase by as
        many players as possible (ideally, every player still running).  It
        will attempt to rendezvous with the other players and return a new
        communicator, but the process could fail and raise an exception
        instead.  In that case it is up to the application to decide how to
        proceed.
        """
        self._log.debug(f"shrink()")

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

        host_socket = socket.create_server((self._host_addr.hostname, 0))
        host, port = host_socket.getsockname()
        host_addr = f"tcp://{host}:{port}"

        if self.rank == remaining_ranks[0]:
            for remaining_rank in remaining_ranks:
                self._send(tag="shrink-end", payload=host_addr, dst=remaining_rank)
        link_addr = self._receive(tag="shrink-end", sender=remaining_ranks[0], block=True).payload

        return SocketCommunicator(name=name, world_size=world_size, rank=rank, link_addr=link_addr, host_socket=host_socket, token=token, timeout=self._timeout, startup_timeout=self._startup_timeout), remaining_ranks


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
            host_socket = socket.create_server((self._host_addr.hostname, 0))
            host, port = host_socket.getsockname()
            host_addr = f"tcp://{host}:{port}"
        else:
            host_addr = None

        # Send names and addresses to rank 0.
        self._send(tag="split-begin", payload=(name, host_addr), dst=0)

        # Collect name membership information from all players and compute new communicator parameters.
        if self.rank == 0:
            messages = [self._receive(tag="split-begin", sender=rank, block=True) for rank in self.ranks]
            group_names = [message.payload[0] for message in messages]
            group_host_addrs = [message.payload[1] for message in messages]

            group_world_sizes = collections.Counter()
            group_ranks = []
            for group_name in group_names:
                group_ranks.append(group_world_sizes[group_name])
                group_world_sizes[group_name] += 1

            group_world_sizes = [group_world_sizes[group_name] for group_name in group_names]

            group_link_addrs = {}
            for group_name, group_host_addr in zip(group_names, group_host_addrs):
                if group_name not in group_link_addrs:
                    group_link_addrs[group_name] = group_host_addr
            group_link_addrs = [group_link_addrs[group_name] for group_name in group_names]

        # Send name, world_size, rank, and link_addr to all players.
        if self.rank == 0:
            for dst, (group_name, group_world_size, group_rank, group_link_addr) in enumerate(zip(group_names, group_world_sizes, group_ranks, group_link_addrs)):
                self._send(tag="split-end", payload=(group_name, group_world_size, group_rank, group_link_addr), dst=dst)

        # Collect name information.
        group_name, group_world_size, group_rank, group_link_addr = self._receive(tag="split-end", sender=0, block=True).payload
        # Return a new communicator.
        if group_name is not None:
            return SocketCommunicator(name=group_name, world_size=group_world_size, rank=group_rank, link_addr=group_link_addr, host_socket=host_socket, timeout=self._timeout, startup_timeout=self._startup_timeout)

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


