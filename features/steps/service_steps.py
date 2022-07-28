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
import urllib.parse

import numpy

from cicada.calculator import main as calculator_main
from cicada.communicator import SocketCommunicator


logging.basicConfig(level=logging.INFO)


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

    # Receive results
    results = []
    for sock in sockets:
        results.append(pickle.loads(sock.recv(4096)))

    return results


@given(u'an MPC service with world size {world_size}')
def step_impl(context, world_size):
    world_size = eval(world_size)

    addresses = SocketCommunicator.run(world_size=world_size, fn=calculator_main, use_listen_socket=True, return_addresses=True, return_results=False)

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

