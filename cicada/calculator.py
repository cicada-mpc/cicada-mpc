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
            command, kwargs = pickle.loads(client.recv(4096))

            pretty_args = ", ".join([f"{key}={value!r}" for key, value in kwargs.items()])
            pretty_command = f"{command}({pretty_args})"
            log.debug(f"Player {communicator.rank} received command: {pretty_command}")

            # Raise an exception if the top of the operand stack doesn't match a value to within n digits.
            if command == "assertclose":
                rhs = kwargs["value"]
                digits = kwargs["digits"]
                lhs = operand_stack[-1]
                numpy.testing.assert_array_almost_equal(lhs, rhs, decimal=digits)
                _send_result(client)
                continue

            # Raise an exception if the top of the operand stack doesn't match a value exactly.
            if command == "assertequal":
                rhs = kwargs["value"]
                lhs = operand_stack[-1]
                numpy.testing.assert_array_equal(lhs, rhs)
                _send_result(client)
                continue

            # Raise an exception if the top values on the operand stack are equal.
            if command == "assertunequal":
                rhs = operand_stack[-1]
                lhs = operand_stack[-2]
                if numpy.array_equal(lhs, rhs):
                    raise RuntimeError(f"Arrays should not be equal: {lhs} == {rhs}")
                _send_result(client)
                continue

            # Encode a binary value on the operand stack.
            if command == "binary-encode":
                protocol = protocol_stack[-1]
                value = operand_stack.pop()
                value = numpy.array(value, dtype=protocol.encoder.dtype)
                operand_stack.append(value)
                _send_result(client)
                continue

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
                value = protocol.encoder.encode(value)
                operand_stack.append(value)
                _send_result(client)
                continue

            # Duplicate the value on the top of the operand stack.
            if command == "opdup":
                value = operand_stack[-1]
                operand_stack.append(value)
                _send_result(client)
                continue

            # Peek at the value on the top of the operand stack.
            if command == "oppeek":
                _send_result(client, operand_stack[-1])
                continue

            # Pop a value from the operand stack.
            if command == "oppop":
                value = operand_stack.pop()
                _send_result(client, value)
                continue

            # Push a new value onto the operand stack.
            if command == "oppush":
                operand = kwargs["value"]
                operand_stack.append(operand)
                _send_result(client)
                continue

            # Return a copy of the operand stack.
            if command == "opstack":
                _send_result(client, operand_stack)
                continue

            # Swap the topmost two values on the operand stack
            if command == "opswap":
                operand_stack[-1], operand_stack[-2] = operand_stack[-2], operand_stack[-1]
                _send_result(client)
                continue

            # Push a new protocol object onto the protocol stack.
            if command == "protopush":
                protocol = kwargs["name"]
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
                _send_result(client)
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

            # Extract the storage from a secret share.
            if command == "sharestorage":
                value = operand_stack.pop()
                operand_stack.append(value.storage)
                _send_result(client)
                continue

            # Unary operations.
            if command in ["floor", "multiplicative_inverse", "relu", "sum", "truncate", "zigmoid"]:
                protocol = protocol_stack[-1]
                a = operand_stack.pop()
                share = getattr(protocol, command)(a)
                operand_stack.append(share)
                _send_result(client)
                continue

            # Binary operations.
            if command in ["add", "dot", "equal", "less", "logical_and", "logical_or", "logical_xor", "max", "min", "private_public_power", "private_public_subtract", "public_private_add", "untruncated_divide", "untruncated_multiply"]:
                protocol = protocol_stack[-1]
                b = operand_stack.pop()
                a = operand_stack.pop()
                share = getattr(protocol, command)(a, b)
                operand_stack.append(share)
                _send_result(client)
                continue

            # Random bitwise secret.
            if command == "random_bitwise_secret":
                bits = kwargs["bits"]
                seed = kwargs["seed"]
                protocol = protocol_stack[-1]
                generator = numpy.random.default_rng(seed=seed)
                bits, secret = protocol.random_bitwise_secret(bits=bits, generator=generator)
                operand_stack.append(bits)
                operand_stack.append(secret)
                _send_result(client)
                continue

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
            client.sendall(pickle.dumps(RuntimeError(f"Unknown command {pretty_command}"))) # pragma: no cover
            client.close() # pragma: no cover

        # Something went wrong.
        except Exception as e: # pragma: no cover
            client.sendall(pickle.dumps(e))
            client.close()

