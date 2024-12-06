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

import io
import logging

from behave import *

from cicada.communicator import SocketCommunicator
import cicada.transcript

import test


@given(u'a default code message handler')
def step_impl(context):
    buffer = io.StringIO()
    context.handler = cicada.transcript.code_handler(logging.StreamHandler(buffer))


@given(u'a network message handler capturing sent messages')
def step_impl(context):
    buffer = io.StringIO()
    context.handler = cicada.transcript.net_handler(logging.StreamHandler(buffer), received=False)


@given(u'a network message handler capturing received messages')
def step_impl(context):
    buffer = io.StringIO()
    context.handler = cicada.transcript.net_handler(logging.StreamHandler(buffer), sent=False)


@when(u'transcription is enabled and player {src} broadcasts {value}')
def step_impl(context, src, value):
    src = eval(src)
    value = eval(value)

    def operation(communicator, handler):
        cicada.transcript.set_handler(logging.getLogger(), handler)
        communicator.broadcast(src=src, value=value)
        return handler.stream.getvalue()

    with cicada.transcript.record():
        context.transcripts = SocketCommunicator.run(world_size=context.players, fn=operation, kwargs=dict(handler=context.handler))


@when(u'transcription is enabled and player {src} generates an order {order} field array of {shape} ones')
def step_impl(context, src, order, shape):
    src = eval(src)
    order = eval(order)
    shape = eval(shape)

    def operation(communicator, handler):
        cicada.transcript.set_handler(logging.getLogger(), handler)
        array = cicada.arithmetic.Field(order=order).ones(shape)
        return handler.stream.getvalue()

    with cicada.transcript.record():
        context.transcripts = SocketCommunicator.run(world_size=context.players, fn=operation, kwargs=dict(handler=context.handler))


@then(u'the transcript for player {rank} should match {result}')
def step_impl(context, rank, result):
    rank = eval(rank)
    result = eval(result)

    transcript = context.transcripts[rank]
    test.assert_equal(transcript.strip(), result)


