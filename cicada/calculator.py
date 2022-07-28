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

from cicada import Logger
from cicada.additive import AdditiveProtocol


def main(listen_socket, communicator):
    """Implements a privacy-preserving RPN calculator service.

    This is an example of MPC-as-a-service, for cases where that is
    desirable.  Run this function using::

        SocketCommunicator.run(world_size=n, fn=cicada.calculator.main, use_listen_socket=True, return_addresses=True, return_results=False)

    ... which will start the service and return a set of socket addresses.
    Client code can then use those addressess to connect to the service and
    issue commands, which will be executed by the service players.

    The service implements an RPN calculator where communicators, protocols,
    and operands are pushed and popped from stacks.
    """
    listen_socket.setblocking(True)
    log = Logger(logger=logging.getLogger(), communicator=communicator)

    protocol_stack = []
    argument_stack = []

    while True:
        client, addr = listen_socket.accept()
        command = pickle.loads(client.recv(4096))
        log.info(f"Player {communicator.rank} received command: {command}")
        if command[0] == "create":
            if command[1] == "AdditiveProtocol":
                protocol_stack.append(AdditiveProtocol(communicator))
        elif command[0] == "share":
            protocol = protocol_stack[-1]
            player = command[1]
            secret = command[2]
            shape = command[3]
            share = protocol.share(src=player, secret=protocol.encoder.encode(secret), shape=shape)
            argument_stack.append(share)
        elif command[0] == "private-private-add":
            protocol = protocol_stack[-1]
            b = argument_stack.pop()
            a = argument_stack.pop()
            share = protocol.add(a, b)
            argument_stack.append(share)
        elif command[0] == "reveal":
            protocol = protocol_stack[-1]
            share = argument_stack.pop()
            secret = protocol.encoder.decode(protocol.reveal(share))
            argument_stack.append(secret)
        elif command[0] == "compare":
            rhs = command[1]
            lhs = argument_stack[-1]
            assert(lhs == rhs)
        else:
            log.error(f"Player {communicator.rank} unknown command: {command}")
        client.sendall(pickle.dumps("OK"))


