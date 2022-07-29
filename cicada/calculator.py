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
    argument_stack = []

    while True:
        try:
            client, addr = listen_socket.accept()
            command = client.recv(4096)
            command = json.loads(command)
            log.info(f"Player {communicator.rank} received command: {command}")

            if command == "quit":
                break

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

            # Push a new value onto the argument stack.
            if isinstance(command, list) and len(command) == 2 and command[0] == "push":
                operand = command[1]
                if operand is not None:
                    operand = numpy.array(operand)
                argument_stack.append(operand)
                _success(client)
                continue

            # Secret share a value from the argument stack.
            if isinstance(command, list) and len(command) == 3 and command[0] == "share":
                src = command[1]
                shape = tuple(command[2])
                protocol = protocol_stack[-1]
                secret = argument_stack.pop()
                share = protocol.share(src=src, secret=protocol.encoder.encode(secret), shape=shape)
                argument_stack.append(share)
                _success(client)
                continue

            # Secret share a value from the argument stack, without encoding.
            if isinstance(command, list) and len(command) == 3 and command[0] == "share-unencoded":
                src = command[1]
                shape = tuple(command[2])
                protocol = protocol_stack[-1]
                secret = numpy.array(argument_stack.pop(), dtype=object)
                share = protocol.share(src=src, secret=secret, shape=shape)
                argument_stack.append(share)
                _success(client)
                continue

            if command == "add":
                protocol = protocol_stack[-1]
                b = argument_stack.pop()
                a = argument_stack.pop()
                share = protocol.add(a, b)
                argument_stack.append(share)
                _success(client)
                continue

            if command == "dot":
                protocol = protocol_stack[-1]
                b = argument_stack.pop()
                a = argument_stack.pop()
                share = protocol.dot(a, b)
                argument_stack.append(share)
                _success(client)
                continue

            if command == "logical-and":
                protocol = protocol_stack[-1]
                b = argument_stack.pop()
                a = argument_stack.pop()
                share = protocol.logical_and(a, b)
                argument_stack.append(share)
                _success(client)
                continue

            if command == "logical-or":
                protocol = protocol_stack[-1]
                b = argument_stack.pop()
                a = argument_stack.pop()
                share = protocol.logical_or(a, b)
                argument_stack.append(share)
                _success(client)
                continue

            if command == "logical-xor":
                protocol = protocol_stack[-1]
                b = argument_stack.pop()
                a = argument_stack.pop()
                share = protocol.logical_xor(a, b)
                argument_stack.append(share)
                _success(client)
                continue

            if command == "relu":
                protocol = protocol_stack[-1]
                a = argument_stack.pop()
                share = protocol.relu(a)
                argument_stack.append(share)
                _success(client)
                continue

            if command == "reveal":
                protocol = protocol_stack[-1]
                share = argument_stack.pop()
                secret = protocol.encoder.decode(protocol.reveal(share))
                argument_stack.append(secret)
                _success(client)
                continue

            if command == "reveal-unencoded":
                protocol = protocol_stack[-1]
                share = argument_stack.pop()
                secret = protocol.reveal(share)
                argument_stack.append(secret)
                _success(client)
                continue

            if command == "zigmoid":
                protocol = protocol_stack[-1]
                a = argument_stack.pop()
                share = protocol.zigmoid(a)
                argument_stack.append(share)
                _success(client)
                continue

            if isinstance(command, list) and len(command) == 3 and command[0] == "assert-close":
                rhs = command[1]
                digits = command[2]
                lhs = argument_stack[-1]
                numpy.testing.assert_array_almost_equal(lhs, rhs, decimal=digits)
                _success(client)
                continue

            if isinstance(command, list) and len(command) == 2 and command[0] == "assert-equal":
                rhs = command[1]
                lhs = argument_stack[-1]
                numpy.testing.assert_array_equal(lhs, rhs)
                _success(client)
                continue

            log.error(f"Player {communicator.rank} unknown command: {command}")
            client.sendall(json.dumps(("unknown command", f"{command}")).encode())
            client.close()
        except Exception as e:
            log.error(f"Player {communicator.rank} exception: {e}")
            client.sendall(json.dumps(("exception", str(e))).encode())
            client.close()

