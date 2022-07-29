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

import json
import logging
import pickle

import numpy

from cicada import Logger


def _success(client):
    client.sendall(json.dumps(None).encode())
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
            command = client.recv(4096)
            command = json.loads(command)
            log.info(f"Player {communicator.rank} received command: {command}")

            # Raise an exception if the top of the operand stack doesn't match a value to within n digits.
            if isinstance(command, list) and len(command) == 3 and command[0] == "assert-close":
                rhs = command[1]
                digits = command[2]
                lhs = operand_stack[-1]
                numpy.testing.assert_array_almost_equal(lhs, rhs, decimal=digits)
                _success(client)
                continue

            # Raise an exception if the top of the operand stack doesn't match a value exactly.
            if isinstance(command, list) and len(command) == 2 and command[0] == "assert-equal":
                rhs = command[1]
                lhs = operand_stack[-1]
                numpy.testing.assert_array_equal(lhs, rhs)
                _success(client)
                continue

            # Push a new value onto the operand stack.
            if isinstance(command, list) and len(command) == 2 and command[0] == "push-operand":
                operand = command[1]
                if operand is not None:
                    operand = numpy.array(operand)
                operand_stack.append(operand)
                _success(client)
                continue

            # Push a new protocol object onto the protocol stack.
            if isinstance(command, list) and len(command) == 2 and command[0] == "push-protocol":
                protocol = command[1]
                if protocol == "AdditiveProtocol":
                    from cicada.additive import AdditiveProtocol
                    protocol_stack.append(AdditiveProtocol(communicator))
                    _success(client)
                    continue
                if protocol == "ShamirProtocol":
                    from cicada.shamir import ShamirProtocol
                    protocol_stack.append(ShamirProtocol(communicator, threshold=2))
                    _success(client)
                    continue

            # Secret share a value from the operand stack.
            if isinstance(command, list) and len(command) == 3 and command[0] == "share":
                src = command[1]
                shape = tuple(command[2])
                protocol = protocol_stack[-1]
                secret = operand_stack.pop()
                share = protocol.share(src=src, secret=secret, shape=shape)
                operand_stack.append(share)
                _success(client)
                continue

            # Encode a binary value on the operand stack.
            if command == "binary-encode":
                protocol = protocol_stack[-1]
                value = operand_stack.pop()
                value = numpy.array(value, dtype=protocol.encoder.dtype)
                operand_stack.append(value)
                _success(client)
                continue

            # Decode a value on the operand stack.
            if command == "decode":
                protocol = protocol_stack[-1]
                value = operand_stack.pop()
                value = protocol.encoder.decode(value)
                operand_stack.append(value)
                _success(client)
                continue

            # Encode a value on the operand stack.
            if command == "encode":
                protocol = protocol_stack[-1]
                value = operand_stack.pop()
                value = protocol.encoder.encode(value)
                operand_stack.append(value)
                _success(client)
                continue

            # Reveal a secret shared value.
            if command == "reveal":
                protocol = protocol_stack[-1]
                share = operand_stack.pop()
                secret = protocol.reveal(share)
                operand_stack.append(secret)
                _success(client)
                continue

            # Exit the service immediately.
            if command == "quit":
                break

            # Unary operations.
            if command in ["floor", "relu", "sum", "truncate", "zigmoid"]:
                protocol = protocol_stack[-1]
                a = operand_stack.pop()
                share = getattr(protocol, command)(a)
                operand_stack.append(share)
                _success(client)
                continue

            # Binary operations.
            if command in ["add", "dot", "equal", "less", "logical_and", "logical_or", "logical_xor", "max", "min", "public_private_add", "untruncated_multiply"]:
                protocol = protocol_stack[-1]
                b = operand_stack.pop()
                a = operand_stack.pop()
                share = getattr(protocol, command)(a, b)
                operand_stack.append(share)
                _success(client)
                continue

            # Unknown command.
            log.error(f"Player {communicator.rank} unknown command: {command}")
            client.sendall(json.dumps(("unknown command", f"{command}")).encode())
            client.close()
        except Exception as e:
            log.error(f"Player {communicator.rank} exception: {e}")
            client.sendall(json.dumps(("exception", str(e))).encode())
            client.close()

