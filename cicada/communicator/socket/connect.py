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

import json
import logging
import numbers
import os
import pickle
import pprint
import select
import socket
import ssl
import time
import urllib.parse

import pynetstring


class CommunicatorEvents(object):
    def __init__(self, name, rank):
        self.name = name
        self.rank = rank

    def filter(self, record):
        record.comm = self.name
        record.rank = self.rank
        return True


class EncryptionFailed(Exception):
    """Raised if an encrypted connection can't be established with another player."""
    pass


class LoggerAdapter(logging.LoggerAdapter):
    """Wraps a Python logger for consistent formatting of communicator log entries.

    logger: :class:`logging.Logger`, required
        Python logger to wrap.
    name: :class:`str`, required
        Communicator name.
    rank: :class:`int`, required
        Communicator rank
    """
    def __init__(self, logger, name, rank):
        super().__init__(logger, extra={"name": name, "rank": rank})

    def process(self, msg, kwargs):
        return message(self.extra["name"], self.extra["rank"], msg), kwargs


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
        self._sent_bytes += len(raw)
        self._sent_messages += 1
        while raw:
            _, ready, _ = select.select([], [self], [])
            if ready:
                sent = self._socket.send(raw)
                raw = raw[sent:]

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


def certformat(cert, indent=""):
    """Format an X509 certificate for easy reading.

    Parameters
    ----------
    cert: :class:`dict`, required
        X509 certificate returned from :meth:`ssl.SSLSocket.getpeercert` or similar.
    indent: :class:`str`, optional
        Optional indenting to be added to the output.

    Returns
    -------
    prettycert: :class:`str`
        The contents of the certificate, formatted for easy reading by humans.
    """
    mapping = {"countryName": "C", "stateOrProvinceName": "ST", "localityName": "L", "organizationName": "O", "commonName": "CN"}

    issuer = [b for a in cert.get("issuer") for b in a]
    issuer = [f"{mapping.get(item[0], item[0])}={item[1]}" for item in issuer]
    issuer = ", ".join(issuer)

    subject = [b for a in cert.get("subject") for b in a]
    subject = [f"{mapping.get(item[0], item[0])}={item[1]}" for item in subject]
    subject = ", ".join(subject)

    return f"""{indent}Serial: {cert.get("serialNumber")}
{indent}Issuer: {issuer}
{indent}Subject: {subject}
{indent}Valid From: {cert.get("notBefore")} Until: {cert.get("notAfter")}"""


def connect(*, address, rank, other_rank, name="world", tls=None):
    """Given an address, create a socket and make a connection.

    Parameters
    ----------
    address: :class:`urllib.parse.ParseResult`, required
        The address URL.
    rank: :class:`int`, required
        Rank of the calling player.
    other_rank: :class:`int`, required
        Rank of the other player (the one we're connecting to).
    name: :class:`str`, optional
        Human readable label used for logging and error messages. Typically,
        this should be the same name that will be eventually used by a
        communicator instance. Defaults to "world".
    tls: pair of :class:`ssl.SSLContext`, optional
        If provided, the returned sockets will implement transport layer
        security.  Callers must provide a sequence containing one context
        configured for server connections, and one for configured for client
        connections, in that order.

    Returns
    -------
    socket: :class:`NetstringSocket`
        The newly-connected socket, ready for use.
    """
    log = getLogger(__name__, name, rank)

    if address.scheme == "file":
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect(address.path)

    elif address.scheme == "tcp":
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((address.hostname, address.port))

    else:
        raise ValueError(f"address.scheme must be file or tcp, got {address.scheme} instead.") # pragma: no cover

    sock.setblocking(True)


    # Optionally setup TLS.
    if tls is not None:
        sock = tls[1].wrap_socket(sock, server_side=False)
        log.info(f"{geturl(sock)} connected to player {other_rank} {getpeerurl(sock)}, received certificate:\n{certformat(sock.getpeercert(), indent='    ')}")
    else:
        log.info(f"{geturl(sock)} connected to player {other_rank} {getpeerurl(sock)}")

    return NetstringSocket(sock)


def direct(*, listen_socket, addresses, rank, name="world", timer=None, tls=None):
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
    timer: :class:`Timer`, optional
        Determines the maximum time to wait for player connections.  Defaults
        to five seconds.
    tls: pair of :class:`ssl.SSLContext`, optional
        If provided, the returned sockets will implement transport layer
        security.  Callers must provide a sequence containing one context
        configured for server connections, and one for configured for client
        connections, in that order.

    Raises
    ------
    :class:`EncryptionFailed`
        If there are problems establishing an encrypted connection with another
        player.
    :class:`Timeout`
        If `timer` expires before all connections are established.
    :class:`ValueError`
        If there are problems with input parameters.

    Returns
    -------
    sockets: :class:`dict` of :class:`NetstringSocket`
        Dictionary mapping player ranks to connected sockets.
    """

    for address in addresses:
        if not isinstance(address, str):
            raise ValueError(message(name, rank, f"address must be a string, got {address} instead.")) # pragma: no cover

    addresses = [urllib.parse.urlparse(address) for address in addresses]

    for address in addresses:
        if address.scheme not in ["file", "tcp"]:
            raise ValueError(message(name, rank, f"address scheme must be file or tcp, got {address.scheme} instead.")) # pragma: no cover
        if address.scheme == "tcp" and not address.port:
            raise ValueError(message(name, rank, f"port must be specified for tcp addresses, got {address} instead.")) # pragma: no cover
        if address.scheme != addresses[0].scheme:
            raise ValueError(message(name, rank, f"address schemes must match.")) # pragma: no cover

    world_size = len(addresses)

    if not isinstance(rank, int):
        raise ValueError(message(name, rank, f"rank must be an integer, got {rank} instead.")) # pragma: no cover
    if rank < 0 or rank >= world_size:
        raise ValueError(message(name, rank, f"rank must be in the range [0, {world_size}), got {rank} instead.")) # pragma: no cover

    if not isinstance(name, str):
        raise ValueError(message(name, rank, f"name must be a string, got {name} instead.")) # pragma: no cover

    if timer is None:
        timer = Timer(threshold=5)
    if not isinstance(timer, Timer):
        raise ValueError(message(name, rank, f"timer must be an instance of Timer, got {timer} instead.")) # pragma: no cover

    # Setup logging
    log = getLogger(__name__, name, rank)
    log.info(f"direct connect with {[address.geturl() for address in addresses]}.")

    # Set aside storage for connections to the other players.
    players = {}

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
                        sock, _ = listen_socket.accept()
                        if tls is not None:
                            sock = tls[0].wrap_socket(sock, server_side=True)
                            log.info(f"{geturl(sock)} accepted connection from {getpeerurl(sock)}, received certificate:\n{certformat(sock.getpeercert(), indent='    ')}")
                        else:
                            log.info(f"{geturl(sock)} accepted connection from {getpeerurl(sock)}")
                        sock = NetstringSocket(sock)
                        other_players.append(sock)
                except ssl.SSLError as e:
                    # There was a problem setting up an encrypted connection with
                    # the other player, so there's no point in continuing.
                    raise EncryptionFailed(message(name, rank, f"remote player failed to connect: {e}"))
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
                            other_player.send(pickle.dumps("OK"))
                            break
                    except Exception as e: # pragma: no cover
                        log.warning(f"exception receiving player rank: {e}")
                        time.sleep(0.1)
                else: # pragma: no cover
                    raise Timeout(message(name, rank, "timeout waiting for player rank."))

        elif rank > listener:
            # Make a connection to the listener.
            while not timer.expired:
                try:
                    players[listener] = connect(address=addresses[listener], rank=rank, other_rank=listener, name=name, tls=tls)
                    break
                except ssl.SSLCertVerificationError as e:
                    # If this happens it means we couldn't verify the other
                    # player's certificate, so there's no point in continuing.
                    raise EncryptionFailed(message(name, rank, f"received invalid certificate from player {listener}."))
                except Exception as e: # pragma: no cover
                    log.warning(f"exception connecting to player {listener}: {e}")
                    time.sleep(0.5)
            else: # pragma: no cover
                raise Timeout(message(name, rank, f"timeout connecting to player {listener}."))

            # Send our rank to the listener.
            while not timer.expired:
                try:
                    players[listener].send(pickle.dumps(rank))
                    break
                except Exception as e: # pragma: no cover
                    log.warning(f"exception sending rank to player {listener}: {e}")
                    time.sleep(0.5)
            else: # pragma: no cover
                raise Timeout(message(name, rank, f"timeout sending rank to player {listener}."))

            # Receive a response from the listener.
            while not timer.expired:
                try:
                    raw_message = players[listener].next_message(timeout=0.1)
                    if raw_message is not None:
                        response = pickle.loads(raw_message)
                        log.debug(f"received response from player {listener}.")
                        break
                except Exception as e: # pragma: no cover
                    log.warning(f"exception waiting for response from player {listener}: {e}")
                    time.sleep(0.1)
            else: # pragma: no cover
                raise Timeout(message(name, rank, f"timeout waiting for response from player {listener}."))

    return players


def getLogger(name, comm, rank):
    logger = logging.getLogger(name)
    logger.addFilter(CommunicatorEvents(comm, rank))
    return LoggerAdapter(logger, comm, rank)


def getpeerurl(sock):
    """Return a socket's peer address as a URL.

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
        path = sock.getpeername()
        return f"file://{path}"

    if sock.family == socket.AF_INET:
        host, port = sock.getpeername()
        return f"tcp://{host}:{port}"

    raise ValueError(f"Unknown address family: {sock.family}") # pragma: no cover


def gettls(*, identity=None, trusted=None):
    """Construct a pair of :class:`ssl.SSLContext` instances.

    Parameters
    ----------
    identity: :class:`str`, optional
        Path to a private key and certificate in PEM format that will
        identify the local player.
    trusted: sequence of :class:`str`, optional
        Path to certificates in PEM format that will identify the other
        players.

    Returns
    -------
    tls: (server, client) tuple or :any:`None`
    """

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

        return (server, client)

    return None



def geturl(sock):
    """Return a socket's local address as a URL.

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

    raise ValueError(f"Unknown address family: {sock.family}") # pragma: no cover


def listen(*, address, rank, name="world", timer=None):
    """Create a listening socket from a URL.

    Typically, callers should use this function to create a listening socket
    for use with either :func:`direct` or :func:`rendezvous`.

    Parameters
    ----------
    address: :class:`str`, required
        Address to use for listening, in the form of a URL.  For example:
        `"tcp://127.0.0.1:59478"` to create a TCP socket, or
        `"file:///path/to/foo"` to create a Unix domain socket.
    rank: :class:`int`, required
        Integer rank of the caller.  Used for logging and error messages.
    name: :class:`str`, optional
        Human readable label.  Used for logging and error messages.  Typically,
        this should match the name used elsewhere to create a communicator.
    timer: :class:`Timer`, optional
        Determines the maximum time to wait for socket creation.  Defaults to
        five seconds.

    Raises
    ------
    :class:`ValueError`
        If there are problems with input parameters.
    :class:`Timeout`
        If `timer` expires before all connections are established.

    Returns
    -------
    socket: :class:`socket.socket`
        A non-blocking socket, bound to `address`, listening for connections.
    """
    if not isinstance(address, str):
        raise ValueError(message(name, rank, f"address must be a string, got {address} instead.")) # pragma: no cover
    address = urllib.parse.urlparse(address)
    if address.scheme not in ["file", "tcp"]:
        raise ValueError(message(name, rank, f"address scheme must be file or tcp, got {address.scheme} instead.")) # pragma: no cover

    if not isinstance(rank, int):
        raise ValueError(message(name, rank, f"rank must be an integer, got {rank} instead.")) # pragma: no cover

    if not isinstance(name, str):
        raise ValueError(message(name, rank, f"name must be a string, got {name} instead.")) # pragma: no cover

    if timer is None:
        timer = Timer(threshold=5)
    if not isinstance(timer, Timer):
        raise ValueError(message(name, rank, f"timer must be an instance of Timer, got {timer} instead.")) # pragma: no cover

    # Setup logging
    log = getLogger(__name__, name, rank)

    # Create the socket.
    while not timer.expired:
        try:
            if address.scheme == "tcp":
                listen_socket = socket.create_server((address.hostname, address.port or 0))
                address = urllib.parse.urlparse(geturl(listen_socket)) # Recreate the address in case the port was assigned at random.
            elif address.scheme == "file":
                if os.path.exists(address.path):
                    os.unlink(address.path) # pragma: no cover
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
        raise Timeout(message(name, rank, f"timeout creating listening socket."))

    return listen_socket


def message(name, rank, msg):
    """Format a message for logging and error handling."""
    return f"Comm {name} player {rank} {msg}"


def rendezvous(*, listen_socket, root_address, world_size, rank, name="world", token=0, timer=None, tls=None):
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
    timer: :class:`Timer`, optional
        Determines the maximum time to wait for socket creation.  Defaults to
        five seconds.
    tls: pair of :class:`ssl.SSLContext`, optional
        If provided, the returned sockets will implement transport layer
        security.  Callers must provide a sequence containing one context
        configured for server connections, and one for configured for client
        connections, in that order.

    Raises
    ------
    :class:`EncryptionFailed`
        If there are problems establishing an encrypted connection with another
        player.
    :class:`Timeout`
        If `timer` expires before all connections are established.
    :class:`TokenMismatch`
        If every player doesn't call this function with the same token.
    :class:`ValueError`
        If there are problems with input parameters.

    Returns
    -------
    sockets: :class:`dict` of :class:`NetstringSocket`
        Dictionary mapping player ranks to connected sockets.
    """
    if not isinstance(root_address, str):
        raise ValueError(message(name, rank, f"root_address must be a string, got {root_address} instead.")) # pragma: no cover
    root_address = urllib.parse.urlparse(root_address)
    if root_address.scheme not in ["file", "tcp"]:
        raise ValueError(message(name, rank, f"root_address scheme must be file or tcp, got {root_address.scheme} instead.")) # pragma: no cover
    if rank == 0 and root_address.geturl() != geturl(listen_socket):
        raise ValueError(message(name, rank, f"Player 0 root_address {root_address} must match listen_socket.")) # pragma: no cover

    if not isinstance(world_size, int):
        raise ValueError(message(name, rank, f"world_size must be an integer, got {world_size} instead.")) # pragma: no cover
    if not world_size > 0:
        raise ValueError(message(name, rank, f"world_size must be greater than zero, got {world_size} instead.")) # pragma: no cover

    if not isinstance(rank, int):
        raise ValueError(message(name, rank, f"rank must be an integer, got {rank} instead.")) # pragma: no cover
    if rank < 0 or rank >= world_size:
        raise ValueError(message(name, rank, f"rank must be in the range [0, {world_size}), got {rank} instead.")) # pragma: no cover

    if not isinstance(name, str):
        raise ValueError(message(name, rank, f"name must be a string, got {name} instead.")) # pragma: no cover

    if timer is None:
        timer = Timer(threshold=5)
    if not isinstance(timer, Timer):
        raise ValueError(message(name, rank, f"timer must be an instance of Timer, got {timer} instead.")) # pragma: no cover

    # Setup logging
    log = getLogger(__name__, name, rank)
    log.info(f"rendezvous with {root_address.geturl()} from {geturl(listen_socket)}")

    # Set aside storage for connections to the other players.
    players = {}

    ###########################################################################
    # Phase 1: Every player (except root) makes a connection to root.

    if rank != 0:
        while not timer.expired:
            try:
                players[0] = connect(address=root_address, rank=rank, other_rank=0, name=name, tls=tls)
                break
            except ConnectionRefusedError as e: # pragma: no cover
                # This happens regularly, particularly when starting on
                # separate hosts, so no need to log a warning.
                time.sleep(0.1)
            except ssl.SSLCertVerificationError as e:
                # If this happens it means we couldn't verify the other
                # player's certificate, so there's no point in continuing.
                raise EncryptionFailed(message(name, rank, "received invalid certificate from player 0."))
            except Exception as e: # pragma: no cover
                log.warning(f"exception connecting to player 0: {e}")
                time.sleep(0.1)
        else: # pragma: no cover
            raise Timeout(message(name, rank, "timeout connecting to player 0."))

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
            raise Timeout(message(name, rank, f"timeout sending address to player 0."))

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
                    sock, _ = listen_socket.accept()
                    if tls is not None:
                        sock = tls[0].wrap_socket(sock, server_side=True)
                        log.info(f"{geturl(sock)} accepted connection from {getpeerurl(sock)}, received certificate:\n{certformat(sock.getpeercert(), indent='    ')}")
                    else:
                        log.debug(f"{geturl(sock)} accepted connection from {getpeerurl(sock)}.")
                    sock = NetstringSocket(sock)
                    other_players.append(sock)
            except ssl.SSLError as e:
                # There was a problem setting up an encrypted connection with
                # the other player, so there's no point in continuing.
                raise EncryptionFailed(message(name, rank, f"remote player failed to connect: {e}"))
            except BlockingIOError as e: # pragma: no cover
                # This happens regularly, particularly when starting on
                # separate hosts, so no need to log a warning.
                time.sleep(0.1)
            except Exception as e: # pragma: no cover
                log.warning(f"exception waiting for connections from other players: {type(e)} {e}")
                time.sleep(0.1)
        else: # pragma: no cover
            raise Timeout(message(name, rank, "timeout waiting for player connections."))

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
                raise Timeout(message(name, rank, "timeout waiting for player address."))

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
            except ssl.SSLError as e:
                # There was a problem setting up an encrypted connection with
                # the other player, so there's no point in continuing.
                raise EncryptionFailed(message(name, rank, f"failed getting addresses from player 0: {e}"))
            except Exception as e: # pragma: no cover
                log.warning(f"exception getting addresses from player 0: {e}")
                time.sleep(0.1)
        else: # pragma: no cover
            raise Timeout(message(name, rank, "timeout waiting for addresses from player 0."))

    addresses = {rank: (urllib.parse.urlparse(address), token) for rank, (address, token) in addresses.items()}

    ###########################################################################
    # Phase 6: Every player verifies that all tokens match.

    for other_rank, (other_address, other_token) in addresses.items():
        if other_token != token:
            raise TokenMismatch(message(name, rank, f"expected token {token!r}, received {other_token!r} from player {other_rank}."))

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
                        sock, _ = listen_socket.accept()
                        if tls is not None:
                            sock = tls[0].wrap_socket(sock, server_side=True)
                            log.info(f"{geturl(sock)} accepted connection from {getpeerurl(sock)}:\n{certformat(sock.getpeercert(), indent='    ')}")
                        else:
                            log.debug(f"{geturl(sock)} accepted connection from {getpeerurl(sock)}.")
                        sock = NetstringSocket(sock)
                        other_players.append(sock)
                except ssl.SSLError as e:
                    # There was a problem setting up an encrypted connection with
                    # the other player, so there's no point in continuing.
                    raise EncryptionFailed(message(name, rank, f"remote player failed to connect: {e}"))
                except Exception as e: # pragma: no cover
                    log.warning(f"exception listening for other players: {type(e)} {e}")
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
                        log.warning(f"exception receiving player rank: {e}")
                        time.sleep(0.1)
                else: # pragma: no cover
                    raise Timeout(message(name, rank, "timeout waiting for player rank."))

        elif rank > listener:
            # Make a connection to the listener.
            while not timer.expired:
                try:
                    players[listener] = connect(address=addresses[listener][0], rank=rank, other_rank=listener, name=name, tls=tls)
                    break
                except ssl.SSLCertVerificationError as e:
                    # If this happens it means we couldn't verify the other
                    # player's certificate, so there's no point in continuing.
                    raise EncryptionFailed(message(name, rank, f"received invalid certificate from player {listener}."))
                except Exception as e: # pragma: no cover
                    log.warning(f"exception connecting to player {listener}: {e}")
                    time.sleep(0.5)
            else: # pragma: no cover
                raise Timeout(message(name, rank, f"timeout connecting to player {listener}."))

            # Send our rank to the listener.
            while not timer.expired:
                try:
                    players[listener].send(pickle.dumps(rank))
                    break
                except Exception as e: # pragma: no cover
                    log.warning(f"exception sending rank to player {listener}: {e}")
                    time.sleep(0.5)
            else: # pragma: no cover
                raise Timeout(message(name, rank, f"timeout sending rank to player {listener}."))

    return players
