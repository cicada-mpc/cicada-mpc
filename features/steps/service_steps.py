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
        sock.sendall(json.dumps(command).encode())

    # Receive results
    results = []
    for sock in sockets:
        result = b""
        while True:
            data = sock.recv(4096)
            if not data:
                break
            result += data
        results.append(json.loads(result))

    for result in results:
        if isinstance(result, list) and len(result) == 2 and result[0] == "unknown command":
            raise RuntimeError(f"Unknown command: {result[1]}")
        if isinstance(result, list) and len(result) == 2 and result[0] == "exception":
            raise RuntimeError(result[1])

    return results


@given(u'a calculator service with {world_size} players')
def step_impl(context, world_size):
    world_size = eval(world_size)

    addresses, processes = SocketCommunicator.run(world_size=world_size, fn=calculator_main, keep_listen_socket=True, return_results=False)

    context.service_addresses = addresses
    context.service_processes = processes
    context.service_ranks = list(range(world_size))
    context.service_world_size = world_size


@given(u'an AdditiveProtocol object')
def step_impl(context):
    service_command(context, command=("protopush", "AdditiveProtocol"))


@when(u'player {player} secret shares unencoded {secret}')
def step_impl(context, player, secret):
    player = eval(player)
    secret = numpy.array(eval(secret))

    command = [("push", secret.tolist()) if player == rank else ("push", None) for rank in context.service_ranks]
    service_command(context, command=command)
    service_command(context, command=("share unencoded", player, secret.shape))


@when(u'player {player} secret shares {secret}')
def step_impl(context, player, secret):
    player = eval(player)
    secret = numpy.array(eval(secret))

    command = [("push", secret.tolist()) if player == rank else ("push", None) for rank in context.service_ranks]
    service_command(context, command=command)
    service_command(context, command=("share", player, secret.shape))


@when(u'all players add the shares')
def step_impl(context):
    service_command(context, command="add")


@when(u'all players compute the dot product of the shares')
def step_impl(context):
    service_command(context, command="dot")


@when(u'all players compute the logical and of the shares')
def step_impl(context):
    service_command(context, command="logical and")


@when(u'all players reveal the result')
def step_impl(context):
    service_command(context, command="reveal")


@when(u'all players reveal the unencoded result')
def step_impl(context):
    service_command(context, command="reveal unencoded")


@then(u'the result should match {value}')
def step_impl(context, value):
    value = eval(value)
    service_command(context, command=("match", value))

