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

import sys
import time

from behave import *
import numpy.testing

import cicada.communicator


@given(u'{} players')
def step_impl(context, players):
	context.players = eval(players)


@when(u'the players enter a barrier at different times')
def step_impl(context):
    @cicada.communicator.NNGCommunicator.run(world_size=context.players)
    def operation(communicator):
        # Disable communicator timeouts
        communicator.timeout = None

        time.sleep(communicator.rank * 0.1)
        enter = time.time()
        communicator.barrier()
        exit = time.time()

        return enter, exit

    context.result = operation()


@then(u'the players should exit the barrier at roughly the same time')
def step_impl(context):
    enter_delta, exit_delta = numpy.max(context.result, axis=0) - numpy.min(context.result, axis=0)
    # Every process should enter the barrier near the expected time.
    numpy.testing.assert_almost_equal(enter_delta, 0.1 * (context.players - 1), decimal=2)
    # Every process should exit the barrier at around the same time.
    numpy.testing.assert_almost_equal(exit_delta, 0, decimal=2)


@when(u'player {} broadcasts {}')
def step_impl(context, src, value):
    src = eval(src)
    value = numpy.array(eval(value))

    @cicada.communicator.NNGCommunicator.run(world_size=context.players)
    def operation(communicator, src, value):
        if communicator.rank != src:
            value = None
        return communicator.broadcast(src=src, value=value)

    context.result = operation(src, value)


@when(u'player {dst} gathers {values} from {src}')
def step_impl(context, src, values, dst):
    src = numpy.array(eval(src))
    values = eval(values)
    dst = eval(dst)

    @cicada.communicator.NNGCommunicator.run(world_size=context.players)
    def operation(communicator):
        return communicator.gatherv(src=src, value=values[communicator.rank], dst=dst)

    context.result = operation()


@when(u'player {} gathers {}')
def step_impl(context, dst, values):
    dst = eval(dst)
    values = [value for value in numpy.array(eval(values))]

    @cicada.communicator.NNGCommunicator.run(world_size=context.players)
    def operation(communicator, values, dst):
        return communicator.gather(value=values[communicator.rank], dst=dst)

    context.result = operation(values, dst)


@when(u'player {} scatters {} to {}')
def step_impl(context, src, values, dst):
    src = eval(src)
    values = [numpy.array(value) for value in eval(values)]
    dst = eval(dst)

    @cicada.communicator.NNGCommunicator.run(world_size=context.players)
    def operation(communicator, src, values, dst):
        if communicator.rank != src:
            values = None
        return communicator.scatterv(src=src, values=values, dst=dst)

    context.result = operation(src, values, dst)


@when(u'player {} scatters {}')
def step_impl(context, src, values):
    src = eval(src)
    values = [value for value in numpy.array(eval(values))]

    @cicada.communicator.NNGCommunicator.run(world_size=context.players)
    def operation(communicator, src, values):
        if communicator.rank != src:
            values = None
        return communicator.scatter(src=src, values=values)

    context.result = operation(src, values)


@then(u'player {} can send {} to player {}')
def step_impl(context, src, value, dst):
    src = eval(src)
    value = numpy.array(eval(value))
    dst = eval(dst)

    @cicada.communicator.NNGCommunicator.run(world_size=context.players)
    def operation(communicator, src, value, dst):
        if communicator.rank == src:
            communicator.send(value=value, dst=dst)
        if communicator.rank == dst:
            result = communicator.recv(src=src)
            numpy.testing.assert_almost_equal(value, result, decimal=4)

    context.result = operation(src, value, dst)


