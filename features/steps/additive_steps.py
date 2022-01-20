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
import unittest.mock

from behave import *
import numpy

import cicada.additive
import cicada.communicator
import cicada.interactive

import test


@then(u'it should be possible to setup an additive protocol object {count} times')
def step_impl(context, count):
    count = eval(count)

    @cicada.communicator.SocketCommunicator.run(world_size=context.players)
    def operation(communicator):
        protocol = cicada.additive.AdditiveProtocol(communicator)

    for i in range(count):
        operation()


@when(u'secret sharing the same value for {count} sessions')
def step_impl(context, count):
    count = eval(count)

    @cicada.communicator.SocketCommunicator.run(world_size=context.players)
    def operation(communicator):
        protocol = cicada.additive.AdditiveProtocol(communicator)
        share = protocol.share(src=0, secret=protocol.encoder.encode(numpy.array(5)), shape=())
        return int(share.storage)

    context.shares = []
    for i in range(count):
        context.shares.append(operation())
    context.shares = numpy.array(context.shares, dtype=numpy.object)


@when(u'secret sharing the same value {count} times in one session')
def step_impl(context, count):
    count = eval(count)

    @cicada.communicator.SocketCommunicator.run(world_size=context.players)
    def operation(communicator, count):
        protocol = cicada.additive.AdditiveProtocol(communicator)
        shares = [protocol.share(src=0, secret=protocol.encoder.encode(numpy.array(5)), shape=()) for i in range(count)]
        return numpy.array([int(share.storage) for share in shares], dtype=numpy.object)

    context.shares = numpy.column_stack(operation(count))


@then(u'the shares should never be repeated')
def step_impl(context):
    for i in range(len(context.shares)):
        for j in range(i+1, len(context.shares)):
            with numpy.testing.assert_raises(AssertionError):
                numpy.testing.assert_almost_equal(context.shares[i], context.shares[j], decimal=4)


@when(u'player {} receives secret input {}')
def step_impl(context, player, text):
    player = eval(player)
    text = eval(text)

    @cicada.communicator.SocketCommunicator.run(world_size=context.players)
    def operation(communicator, player, text):
        protocol = cicada.additive.AdditiveProtocol(communicator)
        cicada.interactive.input = unittest.mock.MagicMock(return_value=text)
        share = cicada.interactive.secret_input(protocol=protocol, encoder=protocol.encoder, src=player)
        return protocol.encoder.decode(protocol.reveal(share))

    context.result = operation(player, text)


@given(u'secret value {}')
def step_impl(context, secret):
	context.secret = numpy.array(eval(secret))


@given(u'local value {}')
def step_impl(context, local):
    context.local = numpy.array(eval(local))


@when(u'player {} performs local in-place addition on the shared secret')
def step_impl(context, player):
    player = eval(player)

    @cicada.communicator.SocketCommunicator.run(world_size=context.players)
    def operation(communicator, secret, player, local):
        protocol = cicada.additive.AdditiveProtocol(communicator)
        share = protocol.share(src=0, secret=protocol.encoder.encode(secret), shape=secret.shape)
        if communicator.rank == player:
            protocol.encoder.inplace_add(share.storage, protocol.encoder.encode(local))
        return protocol.encoder.decode(protocol.reveal(share))

    context.result = operation(context.secret, player, context.local)


@when(u'player {} performs local in-place subtraction on the shared secret')
def step_impl(context, player):
    player = eval(player)

    @cicada.communicator.SocketCommunicator.run(world_size=context.players)
    def operation(communicator, secret, player, local):
        protocol = cicada.additive.AdditiveProtocol(communicator)
        share = protocol.share(src=0, secret=protocol.encoder.encode(secret), shape=secret.shape)
        if communicator.rank == player:
            protocol.encoder.inplace_subtract(share.storage, protocol.encoder.encode(local))
        return protocol.encoder.decode(protocol.reveal(share))

    context.result = operation(context.secret, player, context.local)


@then(u'the group should return {}')
def step_impl(context, result):
    result = numpy.array(eval(result))
    group = numpy.array(context.result)

    if issubclass(result.dtype.type, numpy.number) and issubclass(group.dtype.type, numpy.number):
        numpy.testing.assert_almost_equal(result, group, decimal=4)
    else:
        numpy.testing.assert_array_equal(result, group)


@given(u'binary operation public-private addition')
def step_impl(context):
    @cicada.communicator.SocketCommunicator.run(world_size=context.players)
    def operation(communicator, a, b):
        protocol = cicada.additive.AdditiveProtocol(communicator)

        a = protocol.encoder.encode(numpy.array(a))
        b = protocol.encoder.encode(numpy.array(b))
        b = protocol.share(src=0, secret=b, shape=b.shape)
        c = protocol.public_private_add(a, b)

        return protocol.encoder.decode(protocol.reveal(c))
    context.binary_operation = operation


@given(u'binary operation private-private addition')
def step_impl(context):
    @cicada.communicator.SocketCommunicator.run(world_size=context.players)
    def operation(communicator, a, b):
        protocol = cicada.additive.AdditiveProtocol(communicator)

        a = protocol.encoder.encode(numpy.array(a))
        a = protocol.share(src=0, secret=a, shape=a.shape)
        b = protocol.encoder.encode(numpy.array(b))
        b = protocol.share(src=1, secret=b, shape=b.shape)
        c = protocol.add(a, b)

        return protocol.encoder.decode(protocol.reveal(c))
    context.binary_operation = operation


@given(u'binary operation private-private untruncated multiplication')
def step_impl(context):
    @cicada.communicator.SocketCommunicator.run(world_size=context.players)
    def operation(communicator, a, b):
        protocol = cicada.additive.AdditiveProtocol(communicator)

        a = protocol.encoder.encode(numpy.array(a))
        a = protocol.share(src=0, secret=a, shape=a.shape)
        b = protocol.encoder.encode(numpy.array(b))
        b = protocol.share(src=1, secret=b, shape=b.shape)
        logging.debug(f"Comm {communicator.name!r} player {communicator.rank} untruncated_multiply")
        c = protocol.untruncated_multiply(a, b)

        logging.debug(f"Comm {communicator.name!r} player {communicator.rank} reveal")
        return protocol.encoder.decode(protocol.reveal(c))
    context.binary_operation = operation


@given(u'binary operation private-private xor')
def step_impl(context):
    @cicada.communicator.SocketCommunicator.run(world_size=context.players)
    def operation(communicator, a, b):
        protocol = cicada.additive.AdditiveProtocol(communicator)

        a = numpy.array(a, dtype=protocol.encoder.dtype)
        a = protocol.share(src=0, secret=a, shape=a.shape)
        b = numpy.array(b, dtype=protocol.encoder.dtype)
        b = protocol.share(src=1, secret=b, shape=b.shape)
        c = protocol.logical_xor(a, b)
        return protocol.reveal(c)
    context.binary_operation = operation


@given(u'binary operation private-private or')
def step_impl(context):
    @cicada.communicator.SocketCommunicator.run(world_size=context.players)
    def operation(communicator, a, b):
        protocol = cicada.additive.AdditiveProtocol(communicator)

        a = numpy.array(a, dtype=protocol.encoder.dtype)
        a = protocol.share(src=0, secret=a, shape=a.shape)
        b = numpy.array(b, dtype=protocol.encoder.dtype)
        b = protocol.share(src=1, secret=b, shape=b.shape)
        c = protocol.logical_or(a, b)
        return protocol.reveal(c)
    context.binary_operation = operation


@given(u'binary operation max')
def step_impl(context):
    @cicada.communicator.SocketCommunicator.run(world_size=context.players)
    def operation(communicator, a, b):
        protocol = cicada.additive.AdditiveProtocol(communicator)

        a = numpy.array(a)
        a_share = protocol.share(src=0, secret=protocol.encoder.encode(a), shape=a.shape)
        b = numpy.array(b)
        b_share = protocol.share(src=1, secret=protocol.encoder.encode(b), shape=b.shape)
        c_share = protocol.max(a_share, b_share)

        return protocol.encoder.decode(protocol.reveal(c_share))
    context.binary_operation = operation


@given(u'binary operation min')
def step_impl(context):
    @cicada.communicator.SocketCommunicator.run(world_size=context.players)
    def operation(communicator, a, b):
        protocol = cicada.additive.AdditiveProtocol(communicator)

        a = numpy.array(a)
        a_share = protocol.share(src=0, secret=protocol.encoder.encode(a), shape=a.shape)
        b = numpy.array(b)
        b_share = protocol.share(src=1, secret=protocol.encoder.encode(b), shape=b.shape)
        c_share = protocol.min(a_share, b_share)

        return protocol.encoder.decode(protocol.reveal(c_share))
    context.binary_operation = operation


@given(u'binary operation private-private multiplication')
def step_impl(context):
    @cicada.communicator.SocketCommunicator.run(world_size=context.players)
    def operation(communicator, a, b):
        protocol = cicada.additive.AdditiveProtocol(communicator)

        a = protocol.encoder.encode(numpy.array(a))
        a = protocol.share(src=0, secret=a, shape=a.shape)
        b = protocol.encoder.encode(numpy.array(b))
        b = protocol.share(src=1, secret=b, shape=b.shape)
        c = protocol.untruncated_multiply(a, b)
        c = protocol.truncate(c)
        return protocol.encoder.decode(protocol.reveal(c))
    context.binary_operation = operation


@given(u'operands {a} and {b}')
def step_impl(context, a, b):
    context.a = eval(a)
    context.b = eval(b)


@given(u'operand {a}')
def step_impl(context, a):
    context.a = eval(a)


@when(u'the binary operation is executed {count} times')
def step_impl(context, count):
    count = eval(count)

    context.result = []
    for i in range(count):
        context.result.append(context.binary_operation(context.a, context.b))


@given(u'unary operation floor')
def step_impl(context):
    @cicada.communicator.SocketCommunicator.run(world_size=context.players)
    def operation(communicator, a):
        protocol = cicada.additive.AdditiveProtocol(communicator)

        a = numpy.array(a)
        a_share = protocol.share(src=0, secret=protocol.encoder.encode(a), shape=a.shape)
        b_share = protocol.floor(a_share)
        return protocol.encoder.decode(protocol.reveal(b_share))
    context.unary_operation = operation


@when(u'the unary operation is executed {count} times')
def step_impl(context, count):
    count = eval(count)

    context.result = []
    for i in range(count):
        context.result.append(context.unary_operation(context.a))



@when(u'player {player} shares and reveals {count} random secrets, the revealed secrets should match the originals')
def step_impl(context, player, count):
    player = eval(player)
    count = eval(count)

    @cicada.communicator.SocketCommunicator.run(world_size=context.players)
    def operation(communicator, secret):
        protocol = cicada.additive.AdditiveProtocol(communicator)
        share = protocol.share(src=player, secret=protocol.encoder.encode(numpy.array(secret)), shape=())
        return protocol.encoder.decode(protocol.reveal(share))

    for index in range(count):
        secret = numpy.array(numpy.random.uniform(-100000, 100000))
        results = operation(secret)
        for result in results:
            numpy.testing.assert_almost_equal(secret, result, decimal=4)

@then(u'generating {bits} random bits with players {src} and seed {seed} produces a valid result')
def step_impl(context, bits, src, seed):
    bits = eval(bits)
    src = eval(src)
    seed = eval(seed)

    @cicada.communicator.SocketCommunicator.run(world_size=context.players)
    def operation(communicator, bits, src, seed):
        protocol = cicada.additive.AdditiveProtocol(communicator)
        generator = numpy.random.default_rng(seed + communicator.rank)
        bit_share, secret_share = protocol.random_bitwise_secret(generator=generator, bits=bits, src=src)

        bits = protocol.reveal(bit_share)
        secret = protocol.reveal(secret_share)
        return bits, secret

    result = operation(bits, src, seed)
    for bits, secret in result:
        test.assert_equal(secret, numpy.sum(numpy.power(2, numpy.arange(len(bits))[::-1]) * bits))

