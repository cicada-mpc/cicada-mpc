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

import logging
import pickle
import socket
import traceback
import urllib

import numpy

from cicada import Logger


class Client(object):
    """Client for working with the privacy-preserving RPN calculator service.

    """
    def __init__(self, addresses):
        self._addresses = addresses

    def command(self, command, *, player=None, **kwargs):
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
            sockets.append(socket.create_connection((address.hostname, address.port)))

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

        return results


    @property
    def ranks(self):
        return list(range(len(self._addresses)))


class PlayerError(Exception):
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

            # Encode a binary value on the operand stack.
            if command == "binary-encode":
                protocol = protocol_stack[-1]
                value = operand_stack.pop()
                value = numpy.array(value, dtype=protocol.encoder.dtype)
                operand_stack.append(value)
                _send_result(client)
                continue

            # Peek at the communicator on the top of the communicator stack.
            elif command == "commget":
                _send_result(client, repr(communicator_stack[-1]))

            # View the entire contents of the communicator stack.
            elif command == "commstack":
                _send_result(client, [repr(communicator) for communicator in communicator_stack])

            # Decode a value on the operand stack.
            elif command == "decode":
                protocol = protocol_stack[-1]
                value = operand_stack.pop()
                value = protocol.encoder.decode(value)
                operand_stack.append(value)
                _send_result(client)

            # Encode a value on the operand stack.
            elif command == "encode":
                protocol = protocol_stack[-1]
                value = operand_stack.pop()
                value = protocol.encoder.encode(value)
                operand_stack.append(value)
                _send_result(client)

            # Duplicate the value on the top of the operand stack.
            elif command == "opdup":
                value = operand_stack[-1]
                operand_stack.append(value)
                _send_result(client)

            # Get the value on the top of the operand stack.
            elif command == "opget":
                _send_result(client, operand_stack[-1])

            # Get n values from the top of the operand stack.
            elif command == "opgetn":
                n = kwargs["n"]
                _send_result(client, operand_stack[-n:])

            # Pop a value from the operand stack.
            elif command == "oppop":
                value = operand_stack.pop()
                _send_result(client, value)

            # Push a new value onto the operand stack.
            elif command == "oppush":
                operand = kwargs["value"]
                operand_stack.append(operand)
                _send_result(client)

            # Return a copy of the operand stack.
            elif command == "opstack":
                _send_result(client, operand_stack)

            # Swap the topmost two values on the operand stack
            elif command == "opswap":
                operand_stack[-1], operand_stack[-2] = operand_stack[-2], operand_stack[-1]
                _send_result(client)

            # Push a new AdditiveProtocol object onto the protocol stack.
            elif command == "protopush" and kwargs["name"] == "Additive":
                from cicada.additive import AdditiveProtocol
                protocol_stack.append(AdditiveProtocol(communicator_stack[-1]))
                _send_result(client)

            # Push a new ShamirProtocol object onto the protocol stack.
            elif command == "protopush" and kwargs["name"] == "Shamir":
                from cicada.shamir import ShamirProtocol
                protocol_stack.append(ShamirProtocol(communicator_stack[-1], threshold=2))
                _send_result(client)

            # Push a new ActiveProtocol object onto the protocol stack.
            elif command == "protopush" and kwargs["name"] == "Active":
                import cicada.active
                protocol_stack.append(cicada.active.ActiveProtocol(communicator_stack[-1], threshold=2))
                _send_result(client)

            # Exit the service immediately.
            elif command == "quit":
                _send_result(client)
                break

            # Raise an exception (for testing).
            elif command == "raise":
                raise kwargs["exception"]

            # Reveal a secret shared value.
            elif command == "reveal":
                protocol = protocol_stack[-1]
                share = operand_stack.pop()
                secret = protocol.reveal(share)
                operand_stack.append(secret)
                _send_result(client)

            # Secret share a value from the operand stack.
            elif command == "share":
                src = kwargs["src"]
                shape = kwargs["shape"]
                protocol = protocol_stack[-1]
                secret = operand_stack.pop()
                share = protocol.share(src=src, secret=secret, shape=shape)
                operand_stack.append(share)
                _send_result(client)

            # Extract the storage from a secret share.
            elif command == "sharestorage":
                value = operand_stack.pop()
                operand_stack.append(value.storage)
                _send_result(client)

            # Unary operations.
            elif command in ["floor", "multiplicative_inverse", "relu", "sum", "truncate", "zigmoid"]:
                protocol = protocol_stack[-1]
                a = operand_stack.pop()
                share = getattr(protocol, command)(a)
                operand_stack.append(share)
                _send_result(client)

            # Binary operations.
            elif command in ["add", "dot", "equal", "less", "logical_and", "logical_or", "logical_xor", "max", "min", "private_public_power", "private_public_subtract", "public_private_add", "untruncated_divide", "untruncated_multiply"]:
                protocol = protocol_stack[-1]
                b = operand_stack.pop()
                a = operand_stack.pop()
                share = getattr(protocol, command)(a, b)
                operand_stack.append(share)
                _send_result(client)

            # Random bitwise secret.
            elif command == "random_bitwise_secret":
                bits = operand_stack.pop()
                protocol = protocol_stack[-1]
                bits, secret = protocol.random_bitwise_secret(bits=bits)
                operand_stack.append(bits)
                operand_stack.append(secret)
                _send_result(client)

            # Inplace addition.
            elif command == "inplace_add":
                protocol = protocol_stack[-1]
                b = operand_stack.pop()
                a = operand_stack.pop()
                protocol.encoder.inplace_add(a.storage, b)
                operand_stack.append(a)
                _send_result(client)

            # Inplace subtraction.
            elif command == "inplace_subtract":
                protocol = protocol_stack[-1]
                b = operand_stack.pop()
                a = operand_stack.pop()
                protocol.encoder.inplace_subtract(a.storage, b)
                operand_stack.append(a)
                _send_result(client)

            # Unknown command.
            else: # pragma: no cover
                raise ValueError(f"Unknown command {pretty_command}")

        # Something went wrong.
        except Exception as e: # pragma: no cover
            _send_result(client, PlayerError(e, traceback.format_exc()))

