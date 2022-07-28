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
import multiprocessing
import pickle
import socket
import urllib.parse

import numpy

from cicada import Logger
from cicada.additive import AdditiveProtocol
from cicada.communicator import SocketCommunicator
from cicada.communicator.socket import connect


def service_main(listen_socket, communicator):
    log = Logger(logger=logging.getLogger(), communicator=communicator)

    protocol_stack = []
    argument_stack = []

    listen_socket.setblocking(True)
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


def service_command(context, command):
    if not isinstance(command, list):
        command = [command] * context.service_world_size

    commands = command

    # Establish connections
    sockets = []
    for rank, address in enumerate(context.service_addresses):
        address = urllib.parse.urlparse(address)
        sockets.append(socket.create_connection((address.hostname, address.port)))

    # Send commands
    for sock, command in zip(sockets, commands):
        sock.sendall(pickle.dumps(command))

#    # Receive results
#    results = []
#    for sock in sockets:
#        results.append(pickle.loads(sock.recv(4096)))
#
#    return results


@given(u'an MPC service with world size {world_size}')
def step_impl(context, world_size):
    world_size = eval(world_size)

    addresses = SocketCommunicator.run(world_size=world_size, fn=service_main, use_listen_socket=True, return_addresses=True, return_results=False)

    context.service_addresses = addresses
    context.service_ranks = list(range(world_size))
    context.service_world_size = world_size


@given(u'an AdditiveProtocol object')
def step_impl(context):
    service_command(context, command=("create", "AdditiveProtocol"))


@when(u'player {player} secret shares operand {operand}')
def step_impl(context, player, operand):
    player = eval(player)
    operand = numpy.array(eval(operand))
    command = [("share", player, operand, operand.shape) if player == rank else ("share", player, None, operand.shape) for rank in context.service_ranks]
    service_command(context, command=command)


@when(u'all players use private-private addition')
def step_impl(context):
    service_command(context, command=("private-private-add", ))


@when(u'all players reveal the result')
def step_impl(context):
    service_command(context, command=("reveal", ))


@then(u'the result should be {value}')
def step_impl(context, value):
    value = eval(value)
    service_command(context, command=("compare", value))

