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

    def launch(*, parent_queue, child_queue, rank, name="world", timeout=5, startup_timeout=5):
        # Run the work function.
        try:
            # Create a socket with a randomly-assigned port number.
            timer = connect.Timer(threshold=startup_timeout)
            listen_socket = connect.listen(name=name, rank=rank, address="tcp://127.0.0.1", timer=timer)
            address = connect.geturl(listen_socket)

            # Send our address to the parent process.
            parent_queue.put((rank, address))

            # Get all addresses from the parent process.
            addresses = child_queue.get()

            sockets=connect.direct(listen_socket=listen_socket, addresses=addresses, rank=rank, name=name, timer=timer)
            communicator = SocketCommunicator(sockets=sockets, name=name, timeout=timeout)
            log = Logger(logger=logging.getLogger(), communicator=communicator)

            protocol_stack = []
            argument_stack = []

            listen_socket.setblocking(True)
            while True:
                client, addr = listen_socket.accept()
                command = pickle.loads(client.recv(4096))
                log.info(f"Player {rank} received command: {command}")
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
                    log.error(f"Player {rank} unknown command: {command}")
                client.sendall(pickle.dumps("OK"))

            communicator.free()
        except Exception as e: # pragma: no cover
            result = Failed(e, traceback.format_exc())

        # Return results to the parent process.
        parent_queue.put((rank, result))

    # Setup the multiprocessing context.
    mp_context = multiprocessing.get_context(method="fork") # I don't remember why we prefer fork().

    # Create queues for IPC.
    parent_queue = mp_context.Queue()
    child_queue = mp_context.Queue()

    # Create per-player processes.
    processes = []
    for rank in range(world_size):
        processes.append(mp_context.Process(
            target=launch,
            kwargs=dict(parent_queue=parent_queue, child_queue=child_queue, rank=rank),
            ))

    # Start per-player processes.
    for process in processes:
        process.daemon = True
        process.start()

    # Collect addresses from every process.
    addresses = [None] * world_size
    for process in processes:
        rank, address = parent_queue.get(block=True)
        addresses[rank] = address

    # Send addresses to every process.
    for process in processes:
        child_queue.put(addresses)

    context.service_addresses = addresses
    context.service_processes = processes
    context.service_ranks = list(range(world_size))
    context.service_world_size = world_size
#
#    # Wait until every process terminates.
#    for process in processes:
#        process.join()
#
#    # Collect a result for every process, but don't block in case
#    # there are missing results.
#    results = []
#    for process in processes:
#        try:
#            results.append(parent_queue.get(block=False))
#        except:
#            break
#
#    # Return the output of each rank, in rank order, with a sentinel object for missing outputs.
#    output = [Terminated(process.exitcode) for process in processes]
#    for rank, result in results:
#        output[rank] = result
#
#    # Log the results for each player.
#    log = logging.getLogger(__name__)
#
#    for rank, result in enumerate(output):
#        if isinstance(result, Failed):
#            log.warning(f"Comm {name} player {rank} failed: {result.exception!r}")
#        elif isinstance(result, Exception):
#            log.warning(f"Comm {name} player {rank} failed: {result!r}")
#        else:
#            log.info(f"Comm {name} player {rank} result: {result}")
#
#    # Print a traceback for players that failed.
#    for rank, result in enumerate(output):
#        if isinstance(result, Failed):
#            log.error("*" * 80)
#            log.error(f"Comm {name} player {rank} traceback:")
#            log.error(result.traceback)
#
#    return output



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

