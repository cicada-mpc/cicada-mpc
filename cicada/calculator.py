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
import urllib

import numpy

from cicada import Logger


class Client(object):
    """Client for working with the privacy-preserving RPN calculator service.

    """
    def __init__(self, addresses):
        self._addresses = addresses

    def command(self, command, *args, player=None, **kwargs):
        if player is None:
            player = list(range(len(self._addresses)))
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
            sock.sendall(pickle.dumps((command, args, kwargs)))

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


    def decode(self):
        return self.command("decode")


    def encode(self):
        return self.command("encode")


    def peek(self):
        return self.command("peekop")


    def pop(self):
        return self.command("popop")


    def push(self, value):
        return self.command("pushop", value)


    def push_protocol(self, name):
        return self.command("pushproto", name)


    def quit(self):
        return self.command("quit")


    def reveal(self):
        return self.command("reveal")


    def share(self, *, src, shape):
        return self.command("share", src=src, shape=shape)


    def stack(self):
        return self.command("stackop")


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

    protocol_stack = []
    operand_stack = []

    while True:
        try:
            # Wait for a client to connect and send a command.
            client, addr = listen_socket.accept()
            command, args, kwargs = pickle.loads(client.recv(4096))

            pretty_args = ", ".join([repr(arg) for arg in args] + [f"{key!r}={value!r}" for key, value in kwargs.items()])
            pretty_command = f"{command}({pretty_args})"
            log.debug(f"Player {communicator.rank} received command: {pretty_command}")

#            # Raise an exception if the top of the operand stack doesn't match a value to within n digits.
#            if isinstance(command, list) and len(command) == 3 and command[0] == "assert-close":
#                rhs = command[1]
#                digits = command[2]
#                lhs = operand_stack[-1]
#                numpy.testing.assert_array_almost_equal(lhs, rhs, decimal=digits)
#                _send_result(client)
#                continue
#
#            # Raise an exception if the top of the operand stack doesn't match a value exactly.
#            if isinstance(command, list) and len(command) == 2 and command[0] == "assert-equal":
#                rhs = command[1]
#                lhs = operand_stack[-1]
#                numpy.testing.assert_array_equal(lhs, rhs)
#                _send_result(client)
#                continue
#
#            # Raise an exception if the top values on the operand stack are equal.
#            if command == "assert-unequal":
#                rhs = operand_stack[-1]
#                lhs = operand_stack[-2]
#                if numpy.array_equal(lhs, rhs):
#                    raise RuntimeError(f"Arrays should not be equal: {lhs} == {rhs}")
#                _send_result(client)
#                continue

            # Decode a value on the operand stack.
            if command == "decode":
                protocol = protocol_stack[-1]
                value = operand_stack.pop()
                value = protocol.encoder.decode(value)
                operand_stack.append(value)
                _send_result(client)
                continue

            # Encode a value on the operand stack.
            if command == "encode":
                protocol = protocol_stack[-1]
                value = operand_stack.pop()
                value = protocol.encoder.encode(numpy.array(value))
                operand_stack.append(value)
                _send_result(client)
                continue

            # Peek at the value on the top of the operand stack.
            if command == "peekop":
                _send_result(client, operand_stack[-1])
                continue

            # Pop a value from the operand stack.
            if command == "popop":
                value = operand_stack.pop()
                _send_result(client, value)
                continue

            # Push a new value onto the operand stack.
            if command == "pushop":
                operand = args[0]
                operand_stack.append(operand)
                _send_result(client)
                continue

            # Push a new protocol object onto the protocol stack.
            if command == "pushproto":
                protocol = args[0]
                if protocol == "AdditiveProtocol":
                    from cicada.additive import AdditiveProtocol
                    protocol_stack.append(AdditiveProtocol(communicator))
                    _send_result(client)
                    continue
                if protocol == "ShamirProtocol":
                    from cicada.shamir import ShamirProtocol
                    protocol_stack.append(ShamirProtocol(communicator, threshold=2))
                    _send_result(client)
                    continue

            # Exit the service immediately.
            if command == "quit":
                break

            # Reveal a secret shared value.
            if command == "reveal":
                protocol = protocol_stack[-1]
                share = operand_stack.pop()
                secret = protocol.reveal(share)
                operand_stack.append(secret)
                _send_result(client)
                continue

            # Secret share a value from the operand stack.
            if command == "share":
                src = kwargs["src"]
                shape = kwargs["shape"]
                protocol = protocol_stack[-1]
                secret = operand_stack.pop()
                share = protocol.share(src=src, secret=secret, shape=shape)
                operand_stack.append(share)
                _send_result(client)
                continue

            if command == "stackop":
                _send_result(client, operand_stack)
                continue

            # Encode a binary value on the operand stack.
            if command == "binary-encode":
                protocol = protocol_stack[-1]
                value = operand_stack.pop()
                value = numpy.array(value, dtype=protocol.encoder.dtype)
                operand_stack.append(value)
                _send_result(client)
                continue

            # Duplicate the value on the top of the operand stack.
            if command == "duplicate-operand":
                value = operand_stack[-1]
                operand_stack.append(value)
                _send_result(client)
                continue

            # Extract the storage from a secret share.
            if command == "extract-storage":
                value = operand_stack.pop()
                operand_stack.append(value.storage)
                _send_result(client)
                continue

#            # Unary operations.
#            if command in ["floor", "multiplicative_inverse", "relu", "sum", "truncate", "zigmoid"]:
#                protocol = protocol_stack[-1]
#                a = operand_stack.pop()
#                share = getattr(protocol, command)(a)
#                operand_stack.append(share)
#                _send_result(client)
#                continue
#
#            # Binary operations.
#            if command in ["add", "dot", "equal", "less", "logical_and", "logical_or", "logical_xor", "max", "min", "private_public_power", "private_public_subtract", "public_private_add", "untruncated_divide", "untruncated_multiply"]:
#                protocol = protocol_stack[-1]
#                b = operand_stack.pop()
#                a = operand_stack.pop()
#                share = getattr(protocol, command)(a, b)
#                operand_stack.append(share)
#                _send_result(client)
#                continue

            # Inplace operations.
            if command == "inplace_add":
                protocol = protocol_stack[-1]
                b = operand_stack.pop()
                a = operand_stack.pop()
                protocol.encoder.inplace_add(a.storage, b)
                operand_stack.append(a)
                _send_result(client)
                continue

            if command == "inplace_subtract":
                protocol = protocol_stack[-1]
                b = operand_stack.pop()
                a = operand_stack.pop()
                protocol.encoder.inplace_subtract(a.storage, b)
                operand_stack.append(a)
                _send_result(client)
                continue

            # Unknown command.
#            log.error(f"Player {communicator.rank} unknown command: {command}") # pragma: no cover
            client.sendall(pickle.dumps(RuntimeError(f"Unknown command {pretty_command}"))) # pragma: no cover
            client.close() # pragma: no cover
        except Exception as e: # pragma: no cover
#            log.error(f"Player {communicator.rank} exception: {e}")
            client.sendall(pickle.dumps(e))
            client.close()

