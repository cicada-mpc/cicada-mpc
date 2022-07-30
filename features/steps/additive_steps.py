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

import functools
import logging

from behave import *
import numpy

import cicada.additive
import cicada.interactive
from cicada.communicator import SocketCommunicator

import test


@then(u'the group should return {}')
def step_impl(context, result):
    result = numpy.array(eval(result))
    group = numpy.array(context.results)

    if issubclass(result.dtype.type, numpy.number) and issubclass(group.dtype.type, numpy.number):
        numpy.testing.assert_almost_equal(result, group, decimal=4)
    else:
        numpy.testing.assert_array_equal(result, group)


@given(u'operand {a}')
def step_impl(context, a):
    context.a = eval(a)


@when(u'the unary operation is executed {count} times')
def step_impl(context, count):
    count = eval(count)

    context.results = []
    for i in range(count):
        context.results.append(context.unary_operation(args=(context.a,)))



@when(u'player {player} shares and reveals {count} random secrets, the revealed secrets should match the originals')
def step_impl(context, player, count):
    player = eval(player)
    count = eval(count)

    def operation(communicator, secret):
        protocol = cicada.additive.AdditiveProtocol(communicator)
        share = protocol.share(src=player, secret=protocol.encoder.encode(numpy.array(secret)), shape=())
        return protocol.encoder.decode(protocol.reveal(share))

    for index in range(count):
        secret = numpy.array(numpy.random.uniform(-100000, 100000))
        results = SocketCommunicator.run(world_size=context.players, fn=operation, args=(secret,), identities=context.identities, trusted=context.trusted)
        for result in results:
            numpy.testing.assert_almost_equal(secret, result, decimal=4)

@then(u'generating {bits} random bits with players {src} and seed {seed} produces a valid result')
def step_impl(context, bits, src, seed):
    bits = eval(bits)
    src = eval(src)
    seed = eval(seed)

    def operation(communicator, bits, src, seed):
        protocol = cicada.additive.AdditiveProtocol(communicator)
        generator = numpy.random.default_rng(seed + communicator.rank)
        bit_share, secret_share = protocol.random_bitwise_secret(generator=generator, bits=bits, src=src)

        bits = protocol.reveal(bit_share)
        secret = protocol.reveal(secret_share)
        return bits, secret

    result = SocketCommunicator.run(world_size=context.players, fn=operation, args=(bits, src, seed), identities=context.identities, trusted=context.trusted)
    for bits, secret in result:
        test.assert_equal(secret, numpy.sum(numpy.power(2, numpy.arange(len(bits))[::-1]) * bits))


@given(u'unary operation multiplicative_inverse')
def step_impl(context):
    def operation(communicator, a):
        protocol = cicada.additive.AdditiveProtocol(communicator)

        a = numpy.array(a)
        a_share = protocol.share(src=0, secret=protocol.encoder.encode(a), shape=a.shape)
        b_share = protocol.multiplicative_inverse(a_share)
        one_share = protocol.untruncated_multiply(a_share, b_share)
        return protocol.reveal(one_share)
    context.unary_operation = functools.partial(SocketCommunicator.run, world_size=context.players, fn=operation, identities=context.identities, trusted=context.trusted)


