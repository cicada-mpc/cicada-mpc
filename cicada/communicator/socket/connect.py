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

import logging
import numbers
import os
import pickle
import select
import socket
import time
import traceback
import urllib.parse

import pynetstring


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

    @property
    def family(self):
        """Return the underlying socket's address family.

        See :attr:`socket.socket.family`.
        """
        return self._socket.family

    def fileno(self):
        """Return the file descriptor for the underlying socket.

        This allows :class:`NetstringSocket` to be used with :func:`select.select`.
        """
        return self._socket.fileno()

    def getsockname(self):
        """Return the underlying socket's address.

        See :meth:`socket.socket.getsockname`.
        """
        return self._socket.getsockname()

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
    def sock(self):
        """Return the underlying :class:`socket.socket`."""
        return self._socket

    @property
    def stats(self):
        """Return a :class:`dict` containing statistics.

        Returns the number of bytes and messages that have been sent and received.
        """
        return {
            "sent": {"bytes": self._sent_bytes, "messages": self._sent_messages},
            "received": {"bytes": self._received_bytes, "messages": self._received_messages},
            }


class Timeout(Exception):
    """Raised when an operation has timed-out."""
    pass


class Timer(object):
    """Tracks elapsed time.

    Parameters
    ----------
    threshold: :class:`numbers.Number`, required
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


def geturl(sock):
    """Return a socket's address as a URL.

    Parameters
    ----------
    sock: :class:`socket.socket`, required

    Returns
    -------
    url: :class:`str`
        The socket's local address as a URL.  For example:
        `"tcp://127.0.0.1:59678"` for TCP sockets, or `"file:///path/to/foo"` for
        Unix domain sockets.
    """
    if sock.family == socket.AF_UNIX:
        path = sock.getsockname()
        return f"file://{path}"
    if sock.family == socket.AF_INET:
        host, port = sock.getsockname()
        return f"tcp://{host}:{port}"
    raise ValueError(f"Unknown address family: {sock.family}")


def listen(*, address, rank, name="world", timeout=5):
    """Create a listening socket from a URL.

    Typically, callers should use this function to create a listening socket
    for use with either :func:`direct` or :func:`rendezvous`.

    Parameters
    ----------
    address: :class:`str`, required
        Address to use for listening, in the form of a URL.  For example: `"tcp://127.0.0.1:59478"`
        to create a TCP socket, or `"file:///path/to/foo"` to create a Unix domain socket.
    rank: :class:`int`, required
        Integer rank of the caller.  Used for logging and error messages.
    name: :class:`str`, optional
        Human readable label.  Used for logging and error messages.  Typically, this should match the
        name used elsewhere to create a communicator.
    timeout: :class:`numbers.Number`, optional
        Maximum time to wait for socket creation, in seconds.

    Returns
    -------
    socket: :class:`socket.socket`
        A non-blocking socket, bound to `address`, listening for connections.
    """
    if not isinstance(address, str):
        raise ValueError(f"Comm {name!r} player {rank} address must be a string, got {address} instead.") # pragma: no cover

    address = urllib.parse.urlparse(address)

    if address.scheme not in ["file", "tcp"]:
        raise ValueError(f"Comm {name!r} player {rank} address scheme must be file or tcp, got {address.scheme} instead.") # pragma: no cover

    # Setup logging
    log = LoggerAdapter(logging.getLogger(__name__), name, rank)

    # Track elapsed time during setup.
    timer = Timer(threshold=timeout)

    # Create the socket.
    while not timer.expired:
        try:
            if address.scheme == "tcp":
                listen_socket = socket.create_server((address.hostname, address.port or 0))
                address = urllib.parse.urlparse(geturl(listen_socket)) # Recreate the address in case the port was assigned at random.
            elif address.scheme == "file":
                if os.path.exists(address.path):
                    os.unlink(address.path)
                listen_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                listen_socket.bind(address.path)
            listen_socket.setblocking(False)
            listen_socket.listen()
            log.info(f"listening to {address.geturl()} for connections.")
            break
        except Exception as e: # pragma: no cover
            log.warning(f"exception creating listening socket: {e}")
            time.sleep(0.1)
    else: # pragma: no cover
        raise Timeout(f"Comm {name!r} player {rank} timeout creating listening socket.")

    return listen_socket


def direct(*, listen_socket, addresses, rank, name="world", timeout=5):
    """Create socket connections given a list of player addresses.

    Parameters
    ----------
    listen_socket: :class:`socket.socket`, required
        A nonblocking Python socket or compatible object, already bound and
        listening for connections.  Typically created with :func:`listen`.
    addresses: :class:`list` of :class:`str`, required
        List of address URLs for every player in rank order.
    rank: :class:`int`, required
        Rank of the calling player.
    name: :class:`str`, optional
        Human readable label used for logging and error messages. Typically,
        this should be the same name assigned to the communicator that will use
        the :func:`direct` outputs.  Defaults to "world".
    timeout: :class:`numbers.Number`, optional
        Maximum time to wait for player connections, in seconds.

    Raises
    ------
    :class:`ValueError`
        If there are problems with input parameters.
    :class:`Timeout`
        If `timeout` seconds elapses before all connections are established.

    Returns
    -------
    sockets: :class:`dict` of :class:`NetstringSocket`
        Dictionary mapping player ranks to connected sockets.
    """

    for address in addresses:
        if not isinstance(address, str):
            raise ValueError(f"address must be a string, got {address} instead.") # pragma: no cover

    addresses = [urllib.parse.urlparse(address) for address in addresses]

    for address in addresses:
        if address.scheme not in ["file", "tcp"]:
            raise ValueError(f"address scheme must be file or tcp, got {address.scheme} instead.") # pragma: no cover
        if address.scheme == "tcp" and not address.port:
            raise ValueError(f"port must be specified for tcp addresses, got {address} instead.") # pragma: no cover
        if address.scheme != addresses[0].scheme:
            raise ValueError(f"address schemes must all be the same.") # pragma: no cover

    world_size = len(addresses)

    if not isinstance(rank, int):
        raise ValueError(f"rank must be an integer, got {rank} instead.") # pragma: no cover
    if rank < 0:
        raise ValueError(f"rank cannot be negative, but got {rank}.") # pragma: no cover
    if rank >= world_size:
        raise ValueError(f"rank must be less than {world_size}, got {rank} instead.") # pragma: no cover

    if not isinstance(name, str):
        raise ValueError("name must be a string, got {name} instead.") # pragma: no cover

    if not isinstance(timeout, numbers.Number):
        raise ValueError(f"timeout must be a number, got {timeout} instead.") # pragma: no cover
    if not timeout > 0:
        raise ValueError(f"timeout must be a positive number, got {timeout} instead.") # pragma: no cover

    # Setup logging
    log = LoggerAdapter(logging.getLogger(__name__), name, rank)
    log.info(f"direct connect with {[address.geturl() for address in addresses]}.")

    # Set aside storage for connections to the other players.
    players = {}

    # Track elapsed time during setup.
    timer = Timer(threshold=timeout)

    # Players setup connections with each other, in rank order.
    for listener in range(0, world_size-1):
        if rank == listener:
            # Accept connections from higher-rank players.
            other_players = []
            while not timer.expired:
                if len(other_players) == world_size - rank - 1: # We don't connect to ourself.
                    break

                try:
                    ready = select.select([listen_socket], [], [], 0.1)
                    if ready:
                        other_player, _ = listen_socket.accept()
                        other_player = NetstringSocket(other_player)
                        other_players.append(other_player)
                        log.debug(f"accepted connection from player.")
                except Exception as e: # pragma: no cover
                    log.warning(f"exception listening for other players: {e}")
                    time.sleep(0.1)

            # Collect ranks from the other players.
            for other_player in other_players:
                while not timer.expired:
                    try:
                        raw_message = other_player.next_message(timeout=0.1)
                        if raw_message is not None:
                            other_rank = pickle.loads(raw_message)
                            players[other_rank] = other_player
                            log.debug(f"received rank from player {other_rank}.")
                            break
                    except Exception as e: # pragma: no cover
                        log.warning(f"exception receiving player rank.")
                        time.sleep(0.1)
                else: # pragma: no cover
                    raise Timeout(f"Comm {name!r} player {rank} timeout waiting for player rank.")

        elif rank > listener:
            # Make a connection to the listener.
            while not timer.expired:
                try:
                    address = addresses[listener]
                    if address.scheme == "tcp":
                        other_player = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        other_player.connect((address.hostname, address.port))
                    elif address.scheme == "file":
                        other_player = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                        other_player.connect(address.path)

                    other_player = NetstringSocket(other_player)
                    players[listener] = other_player
                    break
                except Exception as e: # pragma: no cover
                    log.warning(f"exception connecting to player {listener}: {e}")
                    time.sleep(0.5)
            else: # pragma: no cover
                raise Timeout(f"Comm {name!r} player {rank} timeout connecting to player {listener}.")

            # Send our rank to the listener.
            while not timer.expired:
                try:
                    players[listener].send(pickle.dumps(rank))
                    break
                except Exception as e: # pragma: no cover
                    log.warning(f"exception sending rank to player {listener}: {e}")
                    time.sleep(0.5)
            else: # pragma: no cover
                raise Timeout(f"Comm {name!r} player {rank} timeout sending rank to player {listener}.")

    return players


def rendezvous(*, listen_socket, root_address, world_size, rank, name="world", token=0, timeout=5):
    """Create socket connections given just the address of the root player.

    Parameters
    ----------
    listen_socket: :class:`socket.socket`, required
        A nonblocking Python socket or compatible object, already bound and
        listening for connections.  Typically created with :func:`listen`.
    root_address: :class:`str`, required
        URL address of the root (rank 0) player.  The address must be reachable
        by all of the other players.
    world_size: :class:`int`, required
        The number of players that will be members of this communicator.
    rank: :class:`int`, required
        The rank of the caller, in the range [0, world_size).
    name: :class:`str`, optional
        Human readable label used for logging and debugging. Typically, this
        should be the same name assigned to the communicator that will use
        the :func:`rendezvous` outputs.  Defaults to "world".
    token: :class:`object`, optional
        All players provide an arbitrary token at startup; every player token
        must match, or a :class:`TokenMismatch` exception will be raised.
    timeout: :class:`numbers.Number`
        Maximum time to wait for socket creation, in seconds.

    Raises
    ------
    :class:`ValueError`
        If there are problems with input parameters.
    :class:`Timeout`
        If `timeout` seconds elapses before all connections are established.
    :class:`TokenMismatch`
        If every player doesn't call this function with the same token.

    Returns
    -------
    sockets: :class:`dict` of :class:`NetstringSocket`
        Dictionary mapping player ranks to connected sockets.
    """
    if not isinstance(name, str):
        raise ValueError("name must be a string, got {name} instead.") # pragma: no cover

#    if world_size is None:
#        world_size = int(os.environ["CICADA_WORLD_SIZE"])
    if not isinstance(world_size, int):
        raise ValueError("world_size must be an integer, got {world_size} instead.") # pragma: no cover
    if not world_size > 0:
        raise ValueError("world_size must be an integer greater than zero, got {world_size} instead.") # pragma: no cover

#    if rank is None:
#        rank = int(os.environ["CICADA_RANK"])
    if not isinstance(rank, int):
        raise ValueError("rank must be an integer, got {rank} instead.") # pragma: no cover
    if not (0 <= rank and rank < world_size):
        raise ValueError(f"rank must be in the range [0, {world_size}), got {rank} instead.") # pragma: no cover

#    if root_addr is None:
#        root_addr = os.environ["CICADA_ROOT_ADDR"]
    root_address = urllib.parse.urlparse(root_address)
    if root_address.scheme != "tcp":
        raise ValueError(f"root_address scheme must be tcp, got {root_address.scheme} instead.") # pragma: no cover
    if root_address.hostname is None:
        raise ValueError("root_address hostname must be specified.") # pragma: no cover
    if root_address.port is None:
        raise ValueError("root_address port must be specified.") # pragma: no cover

    if rank == 0 and root_address.geturl() != geturl(listen_socket):
        raise ValueError(f"Player 0 root_address {root_address} must match listen_socket.") # pragma: no cover

    if not isinstance(timeout, numbers.Number):
        raise ValueError(f"timeout must be a number, got {timeout} instead.") # pragma: no cover

    # Setup logging
    log = LoggerAdapter(logging.getLogger(__name__), name, rank)
    log.info(f"rendezvous with {root_address.geturl()} from {geturl(listen_socket)}")

    # Set aside storage for connections to the other players.
    players = {}

    # Track elapsed time during setup.
    timer = Timer(threshold=timeout)

    ###########################################################################
    # Phase 1: Every player (except root) makes a connection to root.

    if rank != 0:
        while not timer.expired:
            try:
                other_player = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                other_player.connect((root_address.hostname, root_address.port))
                other_player = NetstringSocket(other_player)
                players[0] = other_player
                break
            except ConnectionRefusedError as e: # pragma: no cover
                # This happens regularly, particularly when starting on
                # separate hosts, so no need to log a warning.
                time.sleep(0.1)
            except Exception as e: # pragma: no cover
                log.warning(f"exception connecting to player 0: {e}")
                time.sleep(0.1)
        else: # pragma: no cover
            raise Timeout(f"Comm {name!r} player {rank} timeout connecting to player 0.")

    ###########################################################################
    # Phase 2: Every player sends their listening address to root.

    if rank != 0:
        while not timer.expired:
            try:
                players[0].send(pickle.dumps((rank, geturl(listen_socket), token)))
                break
            except Exception as e: # pragma: no cover
                log.warning(f"exception sending address to player 0: {e}")
                time.sleep(0.1)
        else: # pragma: no cover
            raise Timeout(f"Comm {name!r} player {rank} timeout sending address to player 0.")

    ###########################################################################
    # Phase 3: Root gathers addresses from every player.

    if rank == 0:
        # Accept a connection from every player.
        other_players = []
        while not timer.expired:
            if len(other_players) == world_size - 1: # We don't connect to ourself.
                break

            try:
                ready = select.select([listen_socket], [], [], 0.1)
                if ready:
                    other_player, _ = listen_socket.accept()
                    other_player = NetstringSocket(other_player)
                    other_players.append(other_player)
                    log.debug(f"accepted connection from player.")
            except BlockingIOError as e: # pragma: no cover
                # This happens regularly, particularly when starting on
                # separate hosts, so no need to log a warning.
                time.sleep(0.1)
            except Exception as e: # pragma: no cover
                log.warning(f"exception waiting for connections from other players: {e}")
                time.sleep(0.1)
        else: # pragma: no cover
            raise Timeout(f"Comm {name!r} player {rank} timeout waiting for player connections.")

        # Collect an address from every player.
        addresses = {rank: (geturl(listen_socket), token)}
        for other_player in other_players:
            while not timer.expired:
                try:
                    raw_message = other_player.next_message(timeout=0.1)
                    if raw_message is not None:
                        other_rank, other_addr, other_token = pickle.loads(raw_message)
                        players[other_rank] = other_player
                        addresses[other_rank] = (other_addr, other_token)
                        log.debug(f"received address from player {other_rank}.")
                        break
                except Exception as e: # pragma: no cover
                    log.warning(f"exception receiving player address: {e}")
                    time.sleep(0.1)
            else: # pragma: no cover
                raise Timeout(f"Comm {name!r} player {rank} timeout waiting for player address.")

    ###########################################################################
    # Phase 4: Root broadcasts the set of all addresses to every player.

    if rank == 0:
        for player in players.values():
            player.send(pickle.dumps(addresses))

    ###########################################################################
    # Phase 5: Every player receives the set of all addresses from root.

    if rank != 0:
        while not timer.expired:
            try:
                raw_message = players[0].next_message(timeout=0.1)
                if raw_message is not None:
                    addresses = pickle.loads(raw_message)
                    log.debug(f"received addresses from player 0.")
                    break
            except Exception as e: # pragma: no cover
                log.warning(f"exception getting addresses from player 0: {e}")
                time.sleep(0.1)
        else: # pragma: no cover
            raise Timeout(f"Comm {name!r} player {rank} timeout waiting for addresses from player 0.")

    addresses = {rank: (urllib.parse.urlparse(address), token) for rank, (address, token) in addresses.items()}

    ###########################################################################
    # Phase 6: Every player verifies that all tokens match.

    for other_rank, (other_address, other_token) in addresses.items():
        if other_token != token:
            raise TokenMismatch(f"Comm {name!r} player {rank} expected token {token!r}, received {other_token!r} from player {other_rank}.")

    ###########################################################################
    # Phase 7: Players setup connections with one another.

    for listener in range(1, world_size-1):
        if rank == listener:
            # Accept connections from higher-rank players.
            other_players = []
            while not timer.expired:
                if len(other_players) == world_size - rank - 1: # We don't connect to ourself.
                    break

                try:
                    ready = select.select([listen_socket], [], [], 0.1)
                    if ready:
                        other_player, _ = listen_socket.accept()
                        other_player = NetstringSocket(other_player)
                        other_players.append(other_player)
                        log.debug(f"accepted connection from player.")
                except Exception as e: # pragma: no cover
                    log.warning(f"exception listening for other players: {e}")
                    time.sleep(0.1)

            # Collect ranks from the other players.
            for other_player in other_players:
                while not timer.expired:
                    try:
                        raw_message = other_player.next_message(timeout=0.1)
                        if raw_message is not None:
                            other_rank = pickle.loads(raw_message)
                            players[other_rank] = other_player
                            log.debug(f"received rank from player {other_rank}.")
                            break
                    except Exception as e: # pragma: no cover
                        log.warning(f"exception receiving player rank.")
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
                    players[listener] = other_player
                    break
                except Exception as e: # pragma: no cover
                    log.warning(f"exception connecting to player {listener}: {e}")
                    time.sleep(0.5)
            else: # pragma: no cover
                raise Timeout(f"Comm {name!r} player {rank} timeout connecting to player {listener}.")

            # Send our rank to the listener.
            while not timer.expired:
                try:
                    players[listener].send(pickle.dumps(rank))
                    break
                except Exception as e: # pragma: no cover
                    log.warning(f"exception sending rank to player {listener}: {e}")
                    time.sleep(0.5)
            else: # pragma: no cover
                raise Timeout(f"Comm {name!r} player {rank} timeout sending rank to player {listener}.")

    return players
