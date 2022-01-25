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

import cicada.communicator


@given(u'{} players')
def step_impl(context, players):
	context.players = eval(players)


@given(u'cicada.communicator.SocketCommunicator')
def step_impl(context):
    context.communicator_cls = cicada.communicator.SocketCommunicator


@when(u'the players enter a barrier at different times')
def step_impl(context):
    def operation(communicator):
        time.sleep(communicator.rank * 0.1)
        enter = time.time()
        communicator.barrier()
        exit = time.time()

        return enter, exit

    context.result = context.communicator_cls.run(world_size=context.players, fn=operation)


@then(u'the players should exit the barrier at roughly the same time')
def step_impl(context):
    enter_delta, exit_delta = numpy.max(context.result, axis=0) - numpy.min(context.result, axis=0)
    logging.info(f"Enter delta: {enter_delta} exit delta: {exit_delta}.")
    # Every process should exit the barrier at around the same time.
    numpy.testing.assert_almost_equal(exit_delta, 0, decimal=2)


@when(u'player {} broadcasts {}')
def step_impl(context, src, value):
    src = eval(src)
    value = numpy.array(eval(value))

    def operation(communicator, src, value):
        if communicator.rank != src:
            value = None
        return communicator.broadcast(src=src, value=value)

    context.result = context.communicator_cls.run(world_size=context.players, fn=operation, args=(src, value))


@when(u'player {dst} gathers {values} from {src}')
def step_impl(context, src, values, dst):
    src = numpy.array(eval(src))
    values = eval(values)
    dst = eval(dst)

    def operation(communicator):
        return communicator.gatherv(src=src, value=values[communicator.rank], dst=dst)

    context.result = context.communicator_cls.run(world_size=context.players, fn=operation)


@when(u'player {dst} gathers {values}')
def step_impl(context, dst, values):
    dst = eval(dst)
    values = [value for value in numpy.array(eval(values))]

    def operation(communicator, values, dst):
        return communicator.gather(value=values[communicator.rank], dst=dst)

    context.result = context.communicator_cls.run(world_size=context.players, fn=operation, args=(values, dst))


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

    context.stats = context.communicator_cls.run(world_size=context.players, fn=operation, args=(src, count))


@when(u'player {} scatters {} to {}')
def step_impl(context, src, values, dst):
    src = eval(src)
    values = [numpy.array(value) for value in eval(values)]
    dst = eval(dst)

    def operation(communicator, src, values, dst):
        if communicator.rank != src:
            values = None
        return communicator.scatterv(src=src, values=values, dst=dst)

    context.result = context.communicator_cls.run(world_size=context.players, fn=operation, args=(src, values, dst))


@when(u'player {} scatters {}')
def step_impl(context, src, values):
    src = eval(src)
    values = [value for value in numpy.array(eval(values))]

    def operation(communicator, src, values):
        if communicator.rank != src:
            values = None
        return communicator.scatter(src=src, values=values)

    context.result = context.communicator_cls.run(world_size=context.players, fn=operation, args=(src, values))


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

    context.result = context.communicator_cls.run(world_size=context.players, fn=operation, args=(src, value, dst))


@then(u'player {src} should have sent exactly {sent} messages')
def step_impl(context, src, sent):
    src = eval(src)
    sent = eval(sent)
    test.assert_equal(context.stats[src]["sent"]["messages"], sent)


@then(u'every player other than {src} should receive exactly {received} messages')
def step_impl(context, src, received):
    src = eval(src)
    received = eval(received)
    for index, player in enumerate(context.stats):
        if index != src:
            test.assert_equal(player["received"]["messages"], received)


@then(u'it should be possible to start and stop a communicator {count} times')
def step_impl(context, count):
    count = eval(count)

    def operation(communicator):
        pass

    for i in range(count):
        context.communicator_cls.run(world_size=context.players, fn=operation)


@when(u'the players split based on names {names}')
def step_impl(context, names):
    names = eval(names)

    def operation(communicator, groups):
        newcomm = communicator.split(name=groups[communicator.rank])
        if newcomm is not None:
            return newcomm.name, newcomm.world_size
        else:
            return None, None

    results = context.communicator_cls.run(world_size=context.players, fn=operation, args=(names,))
    context.names, context.world_sizes = zip(*results)


@then(u'the resulting communicators should have {world_size} players')
def step_impl(context, world_size):
    world_size = eval(world_size)
    test.assert_equal(list(context.world_sizes), list(world_size))


@then(u'the resulting communicator names should match {names}')
def step_impl(context, names):
    names = eval(names)
    test.assert_equal(list(context.names), list(names))

