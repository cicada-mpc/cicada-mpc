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


@then(u'it should be possible to setup a shamir protocol object {count} times')
def step_impl(context, count):
    count = eval(count)

    def operation(communicator):
        protocol = cicada.shamir.ShamirProtocol(communicator, threshold=2)

    for i in range(count):
        SocketCommunicator.run(world_size=context.players, fn=operation)


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


@given(u'binary operation shamir public-private addition')
def step_impl(context):
    def operation(communicator, a, b):
        protocol = cicada.shamir.ShamirProtocol(communicator, threshold=2)

        a = protocol.encoder.encode(numpy.array(a))
        b = protocol.encoder.encode(numpy.array(b))
        b = protocol.share(src=0, secret=b, shape=b.shape)
        c = protocol.public_private_add(a, b)

        return protocol.encoder.decode(protocol.reveal(c))
    context.binary_operation = functools.partial(SocketCommunicator.run, world_size=context.players, fn=operation)


@given(u'binary operation shamir private-private addition')
def step_impl(context):
    def operation(communicator, a, b):
        protocol = cicada.shamir.ShamirProtocol(communicator, threshold=2)

        a = protocol.encoder.encode(numpy.array(a))
        a = protocol.share(src=0, secret=a, shape=a.shape)
        b = protocol.encoder.encode(numpy.array(b))
        b = protocol.share(src=1, secret=b, shape=b.shape)
        c = protocol.add(a, b)

        return protocol.encoder.decode(protocol.reveal(c))
    context.binary_operation = functools.partial(SocketCommunicator.run, world_size=context.players, fn=operation)


@given(u'binary operation shamir private-private untruncated multiplication')
def step_impl(context):
    def operation(communicator, a, b):
        protocol = cicada.shamir.ShamirProtocol(communicator, threshold=2)

        a = protocol.encoder.encode(numpy.array(a))
        a = protocol.share(src=0, secret=a, shape=a.shape)
        b = protocol.encoder.encode(numpy.array(b))
        b = protocol.share(src=1, secret=b, shape=b.shape)
        logging.debug(f"Comm {communicator.name} player {communicator.rank} untruncated_multiply")
        c = protocol.untruncated_multiply(a, b)

        logging.debug(f"Comm {communicator.name} player {communicator.rank} reveal")
        return protocol.encoder.decode(protocol.reveal(c))
    context.binary_operation = functools.partial(SocketCommunicator.run, world_size=context.players, fn=operation)


@given(u'binary operation shamir private-private xor')
def step_impl(context):
    def operation(communicator, a, b):
        protocol = cicada.shamir.ShamirProtocol(communicator, threshold=2)

        a = numpy.array(a, dtype=protocol.encoder.dtype)
        a = protocol.share(src=0, secret=a, shape=a.shape)
        b = numpy.array(b, dtype=protocol.encoder.dtype)
        b = protocol.share(src=1, secret=b, shape=b.shape)
        c = protocol.logical_xor(a, b)
        return protocol.reveal(c)
    context.binary_operation = functools.partial(SocketCommunicator.run, world_size=context.players, fn=operation)


@given(u'binary operation shamir private-private or')
def step_impl(context):
    def operation(communicator, a, b):
        protocol = cicada.shamir.ShamirProtocol(communicator, threshold=2)

        a = numpy.array(a, dtype=protocol.encoder.dtype)
        a = protocol.share(src=0, secret=a, shape=a.shape)
        b = numpy.array(b, dtype=protocol.encoder.dtype)
        b = protocol.share(src=1, secret=b, shape=b.shape)
        c = protocol.logical_or(a, b)
        return protocol.reveal(c)
    context.binary_operation = functools.partial(SocketCommunicator.run, world_size=context.players, fn=operation)


@given(u'binary operation shamir max')
def step_impl(context):
    def operation(communicator, a, b):
        protocol = cicada.shamir.ShamirProtocol(communicator, threshold=2)

        a = numpy.array(a)
        a_share = protocol.share(src=0, secret=protocol.encoder.encode(a), shape=a.shape)
        b = numpy.array(b)
        b_share = protocol.share(src=1, secret=protocol.encoder.encode(b), shape=b.shape)
        c_share = protocol.max(a_share, b_share)

        return protocol.encoder.decode(protocol.reveal(c_share))
    context.binary_operation = functools.partial(SocketCommunicator.run, world_size=context.players, fn=operation)


@given(u'binary operation shamir min')
def step_impl(context):
    def operation(communicator, a, b):
        protocol = cicada.shamir.ShamirProtocol(communicator, threshold=2)

        a = numpy.array(a)
        a_share = protocol.share(src=0, secret=protocol.encoder.encode(a), shape=a.shape)
        b = numpy.array(b)
        b_share = protocol.share(src=1, secret=protocol.encoder.encode(b), shape=b.shape)
        c_share = protocol.min(a_share, b_share)

        return protocol.encoder.decode(protocol.reveal(c_share))
    context.binary_operation = functools.partial(SocketCommunicator.run, world_size=context.players, fn=operation)


@given(u'binary operation shamir private-private multiplication')
def step_impl(context):
    def operation(communicator, a, b):
        protocol = cicada.shamir.ShamirProtocol(communicator, threshold=2)

        a = protocol.encoder.encode(numpy.array(a))
        a = protocol.share(src=0, secret=a, shape=a.shape)
        b = protocol.encoder.encode(numpy.array(b))
        b = protocol.share(src=1, secret=b, shape=b.shape)
        c = protocol.untruncated_multiply(a, b)
        c = protocol.truncate(c)
        return protocol.encoder.decode(protocol.reveal(c))
    context.binary_operation = functools.partial(SocketCommunicator.run, world_size=context.players, fn=operation)


@given(u'binary operation shamir private-private equality')
def step_impl(context):
    def operation(communicator, a, b):
        protocol = cicada.shamir.ShamirProtocol(communicator, threshold=2)

        a = protocol.encoder.encode(numpy.array(a))
        a = protocol.share(src=0, secret=a, shape=a.shape)
        b = protocol.encoder.encode(numpy.array(b))
        b = protocol.share(src=1, secret=b, shape=b.shape)
        c = protocol.equal(a, b)
        return protocol.reveal(c)
    context.binary_operation = functools.partial(SocketCommunicator.run, world_size=context.players, fn=operation)


@given(u'unary operation shamir floor')
def step_impl(context):
    def operation(communicator, a):
        protocol = cicada.shamir.ShamirProtocol(communicator, threshold=2)

        a = numpy.array(a)
        a_share = protocol.share(src=0, secret=protocol.encoder.encode(a), shape=a.shape)
        b_share = protocol.floor(a_share)
        return protocol.encoder.decode(protocol.reveal(b_share))
    context.unary_operation = functools.partial(SocketCommunicator.run, world_size=context.players, fn=operation)


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


@given(u'binary operation shamir less')
def step_impl(context):
    def operation(communicator, a, b):
        protocol = cicada.shamir.ShamirProtocol(communicator, threshold=2)

        a = protocol.encoder.encode(numpy.array(a))
        a = protocol.share(src=0, secret=a, shape=a.shape)
        b = protocol.encoder.encode(numpy.array(b))
        b = protocol.share(src=0, secret=b, shape=b.shape)
        c = protocol.less(a, b)
        return protocol.reveal(c)
    context.binary_operation = functools.partial(SocketCommunicator.run, world_size=context.players, fn=operation)


@given(u'unary operation shamir relu')
def step_impl(context):
    def operation(communicator, a):
        protocol = cicada.shamir.ShamirProtocol(communicator, threshold=2)

        a = numpy.array(a)
        a_share = protocol.share(src=0, secret=protocol.encoder.encode(a), shape=a.shape)
        relu_share = protocol.relu(a_share)
        return protocol.encoder.decode(protocol.reveal(relu_share))
    context.unary_operation = functools.partial(SocketCommunicator.run, world_size=context.players, fn=operation)

@given(u'unary operation shamir zigmoid')
def step_impl(context):
    def operation(communicator, a):
        protocol = cicada.shamir.ShamirProtocol(communicator, threshold=2)

        a = numpy.array(a)
        a_share = protocol.share(src=0, secret=protocol.encoder.encode(a), shape=a.shape)
        zigmoid_share = protocol.zigmoid(a_share)
        return protocol.encoder.decode(protocol.reveal(zigmoid_share))
    context.unary_operation = functools.partial(SocketCommunicator.run, world_size=context.players, fn=operation)

@when(u'player {} performs private public subtraction on the shamir shared secret')
def step_impl(context, player):
    player = eval(player)

    def operation(communicator, secret, player, local):
        protocol = cicada.shamir.ShamirProtocol(communicator, threshold=2)
        share = protocol.share(src=0, secret=protocol.encoder.encode(secret), shape=secret.shape)
        result = protocol.private_public_subtract(share, protocol.encoder.encode(local))
        return protocol.encoder.decode(protocol.reveal(result))

    context.results = SocketCommunicator.run(world_size=context.players, fn=operation, args=(context.secret, player, context.local))


@given(u'binary operation shamir logical_and')
def step_impl(context):
    def operation(communicator, a, b):
        protocol = cicada.shamir.ShamirProtocol(communicator, threshold=2)

        a = numpy.array(a, dtype=object)
        a = protocol.share(src=0, secret=a, shape=a.shape)
        b = numpy.array(b, dtype=object)
        b = protocol.share(src=0, secret=b, shape=b.shape)
        c = protocol.logical_and(a, b)
        return protocol.reveal(c)
    context.binary_operation = functools.partial(SocketCommunicator.run, world_size=context.players, fn=operation)


@given(u'binary operation shamir private_public_power')
def step_impl(context):
    def operation(communicator, a, b):
        protocol = cicada.shamir.ShamirProtocol(communicator, threshold=2)

        a = protocol.encoder.encode(numpy.array(a))
        a = protocol.share(src=0, secret=a, shape=a.shape)
        b = numpy.array(b)
        c = protocol.private_public_power(a, b)
        return protocol.encoder.decode(protocol.reveal(c))
    context.binary_operation = functools.partial(SocketCommunicator.run, world_size=context.players, fn=operation)



@given(u'binary operation shamir untruncated_private_divide')
def step_impl(context):
    def operation(communicator, a, b):
        protocol = cicada.shamir.ShamirProtocol(communicator, threshold=2)

        a = protocol.encoder.encode(numpy.array(a))
        a = protocol.share(src=0, secret=a, shape=a.shape)
        b = protocol.encoder.encode(numpy.array(b))
        b = protocol.share(src=0, secret=b, shape=b.shape)
        c = protocol.untruncated_private_divide(a, b)
        c = protocol.truncate(c)
        return protocol.encoder.decode(protocol.reveal(c))
    context.binary_operation = functools.partial(SocketCommunicator.run, world_size=context.players, fn=operation)
