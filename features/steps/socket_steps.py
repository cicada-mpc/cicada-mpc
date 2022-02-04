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
import sys
import time

from behave import *
import numpy.testing
import test

from cicada.communicator.socket import Failed, NotRunning, Revoked, Timeout, TokenMismatch, SocketCommunicator, predefined, rendezvous


@given(u'{} players')
def step_impl(context, players):
	context.players = eval(players)


@when(u'the players enter a barrier at different times')
def step_impl(context):
    def operation(communicator):
        time.sleep(communicator.rank * 0.1)
        enter = time.time()
        communicator.barrier()
        exit = time.time()

        return enter, exit

    context.results = SocketCommunicator.run(world_size=context.players, fn=operation)


@then(u'the players should exit the barrier at roughly the same time')
def step_impl(context):
    enter_delta, exit_delta = numpy.max(context.results, axis=0) - numpy.min(context.results, axis=0)
    logging.info(f"Enter delta: {enter_delta} exit delta: {exit_delta}.")
    # Every process should exit the barrier at around the same time.
    numpy.testing.assert_almost_equal(exit_delta, 0, decimal=2)


@when(u'the players allgather {values}')
def step_impl(context, values):
    values = eval(values)

    def operation(communicator, values):
        return communicator.all_gather(value=values[communicator.rank])

    context.results = SocketCommunicator.run(world_size=context.players, fn=operation, args=(values,))


@when(u'player {src} broadcasts {value} after the communicator has been freed')
def step_impl(context, src, value):
    src = eval(src)
    value = numpy.array(eval(value))

    def operation(communicator, src, value):
        communicator.free()
        return communicator.broadcast(src=src, value=value)

    context.results = SocketCommunicator.run(world_size=context.players, fn=operation, args=(src, value))


@when(u'player {} broadcasts {}')
def step_impl(context, src, value):
    src = eval(src)
    value = numpy.array(eval(value))

    def operation(communicator, src, value):
        return communicator.broadcast(src=src, value=value)

    context.results = SocketCommunicator.run(world_size=context.players, fn=operation, args=(src, value))


@when(u'player {dst} gathers {values} from {src}')
def step_impl(context, src, values, dst):
    src = numpy.array(eval(src))
    values = eval(values)
    dst = eval(dst)

    def operation(communicator):
        return communicator.gatherv(src=src, value=values[communicator.rank], dst=dst)

    context.results = SocketCommunicator.run(world_size=context.players, fn=operation)


@when(u'player {dst} gathers {values}')
def step_impl(context, dst, values):
    dst = eval(dst)
    values = [value for value in numpy.array(eval(values))]

    def operation(communicator, values, dst):
        return communicator.gather(value=values[communicator.rank], dst=dst)

    context.results = SocketCommunicator.run(world_size=context.players, fn=operation, args=(values, dst))


@when(u'player {src} scatters messages to the other players {count} times')
def step_impl(context, src, count):
    src = eval(src)
    count = eval(count)

    def operation(communicator, src, count):
        others = set(range(communicator.world_size)) - set([src])
        for i in range(count):
            result = communicator.scatterv(src=src, values=others, dst=others)
        communicator.free()
        return communicator.stats

    context.stats = SocketCommunicator.run(world_size=context.players, fn=operation, args=(src, count))


@when(u'player {} scatters {} to {}')
def step_impl(context, src, values, dst):
    src = eval(src)
    values = [numpy.array(value) for value in eval(values)]
    dst = eval(dst)

    def operation(communicator, src, values, dst):
        if communicator.rank != src:
            values = None
        return communicator.scatterv(src=src, values=values, dst=dst)

    context.results = SocketCommunicator.run(world_size=context.players, fn=operation, args=(src, values, dst))


@when(u'player {} scatters {}')
def step_impl(context, src, values):
    src = eval(src)
    values = [value for value in numpy.array(eval(values))]

    def operation(communicator, src, values):
        if communicator.rank != src:
            values = None
        return communicator.scatter(src=src, values=values)

    context.results = SocketCommunicator.run(world_size=context.players, fn=operation, args=(src, values))


@then(u'player {} can send {} to player {}')
def step_impl(context, src, value, dst):
    src = eval(src)
    value = numpy.array(eval(value))
    dst = eval(dst)

    def operation(communicator, src, value, dst):
        if communicator.rank == src:
            communicator.send(value=value, dst=dst)
        if communicator.rank == dst:
            result = communicator.recv(src=src)
            numpy.testing.assert_almost_equal(value, result, decimal=4)

    context.results = SocketCommunicator.run(world_size=context.players, fn=operation, args=(src, value, dst))


@then(u'player {src} should have sent exactly {sent} messages')
def step_impl(context, src, sent):
    src = eval(src)
    sent = eval(sent)
    test.assert_equal(context.stats[src]["sent"]["messages"], sent)


@then(u'every player other than {src} should receive exactly {received} messages')
def step_impl(context, src, received):
    src = eval(src)
    received = eval(received)

    stats = [player for index, player in enumerate(context.stats) if index != src]
    for player, expected in zip(stats, received):
        test.assert_equal(player["received"]["messages"], expected)


@then(u'it should be possible to start and stop a communicator {count} times')
def step_impl(context, count):
    count = eval(count)

    def operation(communicator):
        pass

    for i in range(count):
        SocketCommunicator.run(world_size=context.players, fn=operation)


@when(u'the players split the communicator with names {names}')
def step_impl(context, names):
    names = eval(names)

    def operation(communicator, groups):
        comm = communicator.split(name=groups[communicator.rank])
        if comm is not None:
            return {"name": comm.name, "world_size": comm.world_size}
        else:
            return {}

    context.results = SocketCommunicator.run(world_size=context.players, fn=operation, args=(names,))


@then(u'the new communicator names should match {names}')
def step_impl(context, names):
    names = eval(names)
    test.assert_equal([result.get("name") for result in context.results], list(names))


@then(u'the new communicator world sizes should match {world_sizes}')
def step_impl(context, world_sizes):
    world_sizes = eval(world_sizes)
    test.assert_equal([result.get("world_size") for result in context.results], list(world_sizes))


@when(u'players {group} create a new communicator with world size {world_size} and name {name} and token {token}')
def step_impl(context, group, world_size, name, token):
    group = eval(group)
    world_size = eval(world_size)
    name = eval(name)
    token = eval(token)

    def operation(communicator, group, world_size, name, token):
        if communicator.rank in group:
            sockets=rendezvous(
                name=name,
                world_size=world_size,
                rank=communicator.rank,
                host_addr="tcp://127.0.0.1:25000" if communicator.rank == group[0] else "tcp://127.0.0.1",
                link_addr="tcp://127.0.0.1:25000",
                token=token,
                )
            comm = SocketCommunicator(sockets=sockets, name=name)
            return {"name": comm.name, "world_size": comm.world_size}
        return {}

    context.results = SocketCommunicator.run(world_size=context.players, fn=operation, args=(group, world_size, name, token))


@when(u'players {group} create a new communicator with world size {world_size} and name {name} and tokens {tokens}')
def step_impl(context, group, world_size, name, tokens):
    group = eval(group)
    world_size = eval(world_size)
    name = eval(name)
    tokens = eval(tokens)

    def operation(communicator, group, world_size, name):
        if communicator.rank in group:
            sockets=rendezvous(
                name=name,
                world_size=world_size,
                rank=communicator.rank,
                host_addr="tcp://127.0.0.1:25000" if communicator.rank == group[0] else "tcp://127.0.0.1",
                link_addr="tcp://127.0.0.1:25000",
                token=tokens[group.index(communicator.rank)]
                )
            comm = SocketCommunicator(sockets=sockets, name=name)
            return {"name": comm.name, "world_size": comm.world_size}
        return {}

    context.results = SocketCommunicator.run(world_size=context.players, fn=operation, args=(group, world_size, name))


@when(u'players {group} create a new communicator with name {name} and predefined addresses {addresses}')
def step_impl(context, group, name, addresses):
    group = eval(group)
    name = eval(name)
    addresses = eval(addresses)

    def operation(communicator, group, name, addresses):
        if communicator.rank in group:
            sockets=predefined(
                name=name,
                addresses=addresses,
                rank=communicator.rank,
                )
            comm = SocketCommunicator(sockets=sockets, name=name)
            return {"name": comm.name, "world_size": comm.world_size}
        return {}

    context.results = SocketCommunicator.run(world_size=context.players, fn=operation, args=(group, name, addresses))


@then(u'players {players} should timeout')
def step_impl(context, players):
    players = eval(players)
    for player in players:
        result = context.results[player]
        test.assert_is_instance(result, Failed)
        test.assert_is_instance(result.exception, Timeout)


@then(u'players {players} should fail with TokenMismatch errors')
def step_impl(context, players):
    players = eval(players)
    for player in players:
        result = context.results[player]
        test.assert_is_instance(result, Failed)
        test.assert_is_instance(result.exception, TokenMismatch)


@then(u'shrinking the communicator under normal conditions will return the same players in the same rank order')
def step_impl(context):
    def operation(communicator):
        comm, newranks = communicator.shrink(name="split")
        return(newranks)

    results = SocketCommunicator.run(world_size=context.players, fn=operation)
    for result in results:
        test.assert_equal(result, list(range(context.players)))


@when(u'players {group} shrink the communicator with name {name}')
def step_impl(context, group, name):
    group = eval(group)
    name = eval(name)
    def operation(communicator, group, name):
        if communicator.rank in group:
            comm, newranks = communicator.shrink(name=name)
            return {"name": comm.name, "world_size": comm.world_size}
        return {}

    context.results = SocketCommunicator.run(world_size=context.players, fn=operation, args=(group, name))


@when(u'player {player} revokes the communicator')
def step_impl(context, player):
    player = eval(player)
    def operation(communicator, player):
        while True:
            try:
                value = communicator.broadcast(src=0, value="foo")
                if communicator.rank == player:
                    communicator.revoke()
            except Timeout as e:
                logging.error(f"Player {communicator.rank} exception: {e}")
                continue
            except Exception as e:
                logging.error(f"Player {communicator.rank} exception: {e}")
                raise e

    context.results = SocketCommunicator.run(world_size=context.players, fn=operation, args=(player,))


@then(u'players {players} should fail with NotRunning errors')
def step_impl(context, players):
    players = eval(players)
    for player in players:
        result = context.results[player]
        test.assert_is_instance(result, Failed)
        test.assert_is_instance(result.exception, NotRunning)


@then(u'players {players} should fail with Revoked errors')
def step_impl(context, players):
    players = eval(players)
    for player in players:
        result = context.results[player]
        test.assert_is_instance(result, Failed)
        test.assert_is_instance(result.exception, Revoked)


@when(u'the communicator timeout is permanently changed to {timeout}')
def step_impl(context, timeout):
    timeout = eval(timeout)

    def operation(communicator, timeout):
        timeout1 = communicator.timeout
        communicator.timeout = timeout
        timeout2 = communicator.timeout

        return [timeout1, timeout2]

    context.timeouts = numpy.array(SocketCommunicator.run(world_size=context.players, fn=operation, args=(timeout,)))


@when(u'the communicator timeout is temporarily changed to {timeout}')
def step_impl(context, timeout):
    timeout = eval(timeout)

    def operation(communicator, timeout):
        timeout1 = communicator.timeout
        with communicator.override(timeout=timeout):
            timeout2 = communicator.timeout
        timeout3 = communicator.timeout

        return [timeout1, timeout2, timeout3]

    context.timeouts = numpy.array(SocketCommunicator.run(world_size=context.players, fn=operation, args=(timeout,)))


@then(u'the initial communicator timeouts should match {timeouts}')
def step_impl(context, timeouts):
    timeouts = eval(timeouts)
    numpy.testing.assert_array_equal(timeouts, context.timeouts[:, 0])


@then(u'the temporary communicator timeouts should match {timeouts}')
def step_impl(context, timeouts):
    timeouts = eval(timeouts)
    numpy.testing.assert_array_equal(timeouts, context.timeouts[:, 1])


@then(u'the final communicator timeouts should match {timeouts}')
def step_impl(context, timeouts):
    timeouts = eval(timeouts)
    numpy.testing.assert_array_equal(timeouts, context.timeouts[:, -1])


