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

import cicada.shamir
import cicada.interactive
from cicada.communicator import SocketCommunicator

import test


@when(u'shamir secret sharing the same value for {count} sessions')
def step_impl(context, count):
    count = eval(count)

    def operation(communicator):
        protocol = cicada.shamir.ShamirProtocol(communicator, threshold=2)
        share = protocol.share(src=0, secret=protocol.encoder.encode(numpy.array(5)), shape=())
        return int(share.storage)

    context.shares = []
    for i in range(count):
        context.shares.append(SocketCommunicator.run(world_size=context.players, fn=operation))
    context.shares = numpy.array(context.shares, dtype=numpy.object)


@when(u'shamir secret sharing the same value {count} times in one session')
def step_impl(context, count):
    count = eval(count)

    def operation(communicator, count):
        protocol = cicada.shamir.ShamirProtocol(communicator, threshold=2)
        shares = [protocol.share(src=0, secret=protocol.encoder.encode(numpy.array(5)), shape=()) for i in range(count)]
        return numpy.array([int(share.storage) for share in shares], dtype=numpy.object)

    context.shares = numpy.column_stack(SocketCommunicator.run(world_size=context.players, fn=operation, args=(count,)))


@when(u'player {} performs local in-place addition on the shamir shared secret')
def step_impl(context, player):
    player = eval(player)

    def operation(communicator, secret, player, local):
        protocol = cicada.shamir.ShamirProtocol(communicator, threshold=2)
        share = protocol.share(src=0, secret=protocol.encoder.encode(secret), shape=secret.shape)
        protocol.encoder.inplace_add(share.storage, protocol.encoder.encode(local))
        return protocol.encoder.decode(protocol.reveal(share))

    context.results = SocketCommunicator.run(world_size=context.players, fn=operation, args=(context.secret, player, context.local))


@when(u'player {} performs local in-place subtraction on the shamir shared secret')
def step_impl(context, player):
    player = eval(player)

    def operation(communicator, secret, player, local):
        protocol = cicada.shamir.ShamirProtocol(communicator, threshold=2)
        share = protocol.share(src=0, secret=protocol.encoder.encode(secret), shape=secret.shape)
        protocol.encoder.inplace_subtract(share.storage, protocol.encoder.encode(local))
        return protocol.encoder.decode(protocol.reveal(share))

    context.results = SocketCommunicator.run(world_size=context.players, fn=operation, args=(context.secret, player, context.local))


@when(u'player {player} shamir shares and reveals random secrets, the revealed secrets should match the originals')
def step_impl(context, player):
    player = eval(player)

    def operation(communicator, secret, player):
        protocol = cicada.shamir.ShamirProtocol(communicator, threshold=2)
        share = protocol.share(src=player, secret=protocol.encoder.encode(numpy.array(secret)), shape=())
        return protocol.encoder.decode(protocol.reveal(share))

    for index in range(10):
        secret = numpy.array(numpy.random.uniform(-100000, 100000))
        results = SocketCommunicator.run(world_size=context.players, fn=operation, args=(secret, player))
        for result in results:
            numpy.testing.assert_almost_equal(secret, result, decimal=4)

@then(u'generating {bits} shamir random bits with all players produces a valid result')
def step_impl(context, bits):
    bits = eval(bits)
    #seed = eval(seed)

    def operation(communicator, bits):
        protocol = cicada.shamir.ShamirProtocol(communicator, threshold=2)
        #generator = numpy.random.default_rng(seed + communicator.rank)
        bit_share, secret_share = protocol.random_bitwise_secret(bits=bits)

        bits = protocol.reveal(bit_share)
        secret = protocol.reveal(secret_share)
        return bits, secret

    result = SocketCommunicator.run(world_size=context.players, fn=operation, args=(bits,))
    for bits, secret in result:
        test.assert_equal(secret, numpy.sum(numpy.power(2, numpy.arange(len(bits))[::-1]) * bits))


@given(u'unary operation shamir multiplicative_inverse')
def step_impl(context):
    def operation(communicator, a):
        protocol = cicada.shamir.ShamirProtocol(communicator, threshold=2)

        a = numpy.array(a)
        a_share = protocol.share(src=0, secret=protocol.encoder.encode(a), shape=a.shape)
        b_share = protocol.multiplicative_inverse(a_share)
        one_share = protocol.untruncated_multiply(a_share, b_share)
        return protocol.reveal(one_share)
    context.unary_operation = functools.partial(SocketCommunicator.run, world_size=context.players, fn=operation)


