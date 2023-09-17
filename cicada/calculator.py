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

"""Implements a client and a server for an MPC-as-a-service calculator."""

import logging
import pickle
import socket
import traceback
import urllib

import numpy

from cicada import Logger


class Client(object):
    """Client for working with the privacy-preserving RPN calculator service.

    Parameters
    ----------
    addresses: sequence of :class:`str`, required
        Socket addresses of the players providing an RPN calculator service.
    """
    def __init__(self, addresses):
        self._addresses = addresses

    def command(self, command, *, player=None, **kwargs):
        """Sends a command to the players providing an RPN calculator service.

        Parameters
        ----------
        command: :class:`str`
            The command to be executed by the RPN calculator service.
        player: :class:`int` or sequence of :class:`int`, optional
            The player(s) that will execute the command.  By default, the
            command will be sent to all players.
        kwargs:
            Keyword arguments that will be included with the command.

        Returns
        -------
        results: sequence of :class:`object`
            Contains the result value returned by each `player`.
        """
        if player is None:
            player = self.ranks
        if not isinstance(player, list):
            player = [player]
        players = player

        # Establish connections
        sockets = []
        for player in players:
            address = self._addresses[player]
            address = urllib.parse.urlparse(address)
            if address.scheme == "file":
                sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                sock.connect(address.path)
                sockets.append(sock)
            elif address.scheme == "tcp":
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect((address.hostname, address.port))
                sockets.append(sock)

        # Send commands
        for sock in sockets:
            sock.sendall(pickle.dumps((command, kwargs)))

        # Receive results
        results = []
        for sock in sockets:
            result = b""
            while True:
                data = sock.recv(4096)
                if not data:
                    break
                result += data
            results.append(pickle.loads(result))

        return players, results


    @property
    def ranks(self):
        """Returns a :class:`list` of player ranks provided by the service."""
        return list(range(len(self._addresses)))


class PlayerError(Exception):
    """Returned from the RPN calculator service when a player raises an exception."""
    def __init__(self, exception, traceback):
        self.exception = exception
        self.traceback = traceback


def _send_result(client, result=None):
    client.sendall(pickle.dumps(result))
    client.close()


def main(listen_socket, communicator):
    """Implements a privacy-preserving RPN calculator service.

    This is an example of MPC-as-a-service, for cases where that is
    desirable.  Run this function using::

        SocketCommunicator.run_forever(world_size=n, fn=cicada.calculator.main)

    ... which will start the service and return a set of player addresses and
    processes.  Client code can use those addressess to connect to the service
    and issue commands, which will be executed by the service players.

    The service implements an RPN calculator where communicators, protocols,
    and operands are pushed and popped from stacks.
    """
    listen_socket.setblocking(True)
    log = Logger(logger=logging.getLogger(), communicator=communicator, sync=False)

    communicator_stack = [communicator]
    protocol_stack = []
    operand_stack = []

    while True:
        try:
            # Wait for a client to connect and send a command.
            client, addr = listen_socket.accept()
            command, kwargs = pickle.loads(client.recv(4096))

            pretty_args = ", ".join([f"{key}={value!r}" for key, value in kwargs.items()])
            pretty_command = f"{command}({pretty_args})"
            log.debug(f"Player {communicator.rank} received command: {pretty_command}")


            #############################################################
            # Commands related to the MPC service.

            # Exit the service immediately.
            if command == "quit":
                _send_result(client)
                break

            # Raise an exception for testing.
            elif command == "raise":
                raise kwargs["exception"]

            #############################################################
            # Commands related to the communicator stack.

            # Placeholder for operations to split, shrink, or connect
            # new communicators.

            #############################################################
            # Commands related to the protocol stack.

            # Push a new ActiveProtocolSuite object onto the protocol stack.
            elif command == "protopush" and kwargs["name"] == "Active":
                import cicada.active
                protocol_stack.append(cicada.active.ActiveProtocolSuite(communicator_stack[-1], threshold=2))
                _send_result(client)

            # Push a new AdditiveProtocolSuite onto the protocol stack.
            elif command == "protopush" and kwargs["name"] == "Additive":
                from cicada.additive import AdditiveProtocolSuite
                protocol_stack.append(AdditiveProtocolSuite(communicator_stack[-1]))
                _send_result(client)

            # Push a new ShamirProtocolSuite object onto the protocol stack.
            elif command == "protopush" and kwargs["name"] == "Shamir":
                from cicada.shamir import ShamirProtocolSuite
                protocol_stack.append(ShamirProtocolSuite(communicator_stack[-1], threshold=2))
                _send_result(client)

            #############################################################
            # Commands related to the operand stack.

            # Duplicate the value on top of the operand stack.
            elif command == "opdup":
                value = operand_stack[-1]
                operand_stack.append(value)
                _send_result(client)

            # Get the value on top of the operand stack.
            elif command == "opget":
                _send_result(client, operand_stack[-1])

            # Get n values from the top of the operand stack.
            elif command == "opgetn":
                n = kwargs["n"]
                _send_result(client, operand_stack[-n:])

            # Pop a value from the top of the operand stack.
            elif command == "oppop":
                value = operand_stack.pop()
                _send_result(client, value)

            # Push a new value on top of the operand stack.
            elif command == "oppush":
                operand = kwargs["value"]
                operand_stack.append(operand)
                _send_result(client)

            # Return a copy of the entire operand stack.
            elif command == "opstack":
                _send_result(client, operand_stack)

            # Swap the top two values on the operand stack
            elif command == "opswap":
                operand_stack[-1], operand_stack[-2] = operand_stack[-2], operand_stack[-1]
                _send_result(client)

            #############################################################
            # Commands related to secret shares.

            # Extract the storage from a secret share on top of the operand stack.
            elif command == "share" and kwargs["subcommand"] == "getstorage":
                share = operand_stack.pop()
                operand_stack.append(share.storage)
                _send_result(client)

            #############################################################
            # Commands related to protocol suites.

            # Secret share a value from the top of the operand stack.
            elif command == "protocol" and kwargs["subcommand"] == "reshare":
                protocol = protocol_stack[-1]
                secret = operand_stack.pop()
                share = protocol.reshare(secret)
                operand_stack.append(share)
                _send_result(client)

            # Reveal a secret shared value from the top of the operand stack.
            elif command == "protocol" and kwargs["subcommand"] == "reveal":
                encoding = kwargs.get("encoding", None)
                protocol = protocol_stack[-1]
                share = operand_stack.pop()
                secret = protocol.reveal(share, encoding=encoding)
                operand_stack.append(secret)
                _send_result(client)

            # Secret share a value from the top of the operand stack.
            elif command == "protocol" and kwargs["subcommand"] == "share":
                src = kwargs["src"]
                shape = kwargs["shape"]
                encoding = kwargs.get("encoding", None)
                protocol = protocol_stack[-1]
                secret = operand_stack.pop()
                share = protocol.share(src=src, secret=secret, shape=shape, encoding=encoding)
                operand_stack.append(share)
                _send_result(client)

            # Unary protocol suite operations.
            elif command == "protocol" and kwargs["subcommand"] in [
                "absolute",
                "bit_compose",
                "bit_decompose",
                "floor",
                "less_zero",
                "logical_not",
                "multiplicative_inverse",
                "negative",
                "relu",
                "sum",
                "truncate",
                "verify",
                "zigmoid",
                ]:
                protocol = protocol_stack[-1]
                a = operand_stack.pop()
                result = getattr(protocol, kwargs["subcommand"])(a)
                operand_stack.append(result)
                _send_result(client)

            # Binary protocol suite operations.
            elif command == "protocol" and kwargs["subcommand"] in [
                "add",
                "divide",
                "dot",
                "equal",
                "field_add",
                "field_dot",
                "field_multiply",
                "field_power",
                "field_subtract",
                "less",
                "logical_and",
                "logical_or",
                "logical_xor",
                "maximum",
                "minimum",
                "multiply",
                "power",
                "subtract",
                "untruncated_divide",
                ]:
                protocol = protocol_stack[-1]
                b = operand_stack.pop()
                a = operand_stack.pop()
                share = getattr(protocol, kwargs["subcommand"])(a, b)
                operand_stack.append(share)
                _send_result(client)

            # Random bitwise secret.
            elif command == "protocol" and kwargs["subcommand"] == "random_bitwise_secret":
                protocol = protocol_stack[-1]
                bits = operand_stack.pop()
                bits, secret = protocol.random_bitwise_secret(bits=bits)
                operand_stack.append(bits)
                operand_stack.append(secret)
                _send_result(client)

            # Uniform random secret generation.
            elif command == "protocol" and kwargs["subcommand"] == "field_uniform":
                protocol = protocol_stack[-1]
                shape = kwargs["shape"]
                secret = protocol.field_uniform(shape=shape)
                operand_stack.append(secret)
                _send_result(client)

            # Unknown command.
            else: # pragma: no cover
                raise ValueError(f"Unknown command {pretty_command}")

        # Something went wrong.
        except Exception as e: # pragma: no cover
            _send_result(client, PlayerError(e, traceback.format_exc()))

