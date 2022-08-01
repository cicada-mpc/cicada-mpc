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

from cicada.calculator import Client, main
from cicada.communicator import SocketCommunicator

import test

#logging.basicConfig(level=logging.INFO)


def _require_success(results):
    for result in results:
        if isinstance(result, Exception):
            raise result
    return results


@given(u'a calculator service with {world_size} players')
def step_impl(context, world_size):
    world_size = eval(world_size)
    addresses, processes = SocketCommunicator.run_forever(world_size=world_size, fn=main)
    context.calculator = Client(addresses)
    context.calculator_processes = processes


@given(u'a new {name} protocol object')
def step_impl(context, name):
    _require_success(context.calculator.command("protopush", name=name))


@given(u'unencoded public value {value}')
def step_impl(context, value):
    value = numpy.array(eval(value))
    _require_success(context.calculator.command("oppush", value=value))


@given(u'public value {value}')
def step_impl(context, value):
    value = numpy.array(eval(value))
    _require_success(context.calculator.command("oppush", value=value))
    _require_success(context.calculator.command("encode"))


@given(u'player {player} secret shares {secret} without encoding')
def step_impl(context, player, secret):
    player = eval(player)
    secret = numpy.array(eval(secret))

    for rank in context.calculator.ranks:
        _require_success(context.calculator.command("oppush", value=secret if player == rank else None, player=rank))
    _require_success(context.calculator.command("binary-encode"))
    _require_success(context.calculator.command("share", src=player, shape=secret.shape))


@given(u'player {player} secret shares {secret}')
def step_impl(context, player, secret):
    player = eval(player)
    secret = numpy.array(eval(secret))

    for rank in context.calculator.ranks:
        _require_success(context.calculator.command("oppush", value=secret if player == rank else None, player=rank))
    _require_success(context.calculator.command("encode"))
    _require_success(context.calculator.command("share", src=player, shape=secret.shape))


@when(u'player {player} adds {value} to the share in-place')
def step_impl(context, player, value):
    player = eval(player)
    value = numpy.array(eval(value))
    _require_success(context.calculator.command("oppush", value=value, player=player))
    _require_success(context.calculator.command("encode", player=player))
    _require_success(context.calculator.command("inplace_add", player=player))


@when(u'player {player} subtracts {value} from the share in-place')
def step_impl(context, player, value):
    player = eval(player)
    value = numpy.array(eval(value))
    _require_success(context.calculator.command("oppush", value=value, player=player))
    _require_success(context.calculator.command("encode", player=player))
    _require_success(context.calculator.command("inplace_subtract", player=player))


@when(u'the players add the public value and the share')
def step_impl(context):
    _require_success(context.calculator.command("public_private_add"))


@when(u'the players add the shares')
def step_impl(context):
    _require_success(context.calculator.command("add"))


@when(u'the players compare the shares for equality')
def step_impl(context):
    _require_success(context.calculator.command("equal"))


@when(u'the players compare the shares with less than')
def step_impl(context):
    _require_success(context.calculator.command("less"))


@when(u'the players compute the dot product of the shares')
def step_impl(context):
    _require_success(context.calculator.command("dot"))


@when(u'the players compute the floor of the share')
def step_impl(context):
    _require_success(context.calculator.command("floor"))


@when(u'the players compute the logical and of the shares')
def step_impl(context):
    _require_success(context.calculator.command("logical_and"))


@when(u'the players compute the logical exclusive or of the shares')
def step_impl(context):
    _require_success(context.calculator.command("logical_xor"))


@when(u'the players compute the logical or of the shares')
def step_impl(context):
    _require_success(context.calculator.command("logical_or"))


@when(u'the players compute the maximum of the shares')
def step_impl(context):
    _require_success(context.calculator.command("max"))


@when(u'the players compute the minimum of the shares')
def step_impl(context):
    _require_success(context.calculator.command("min"))


@when(u'the players compute the multiplicative inverse')
def step_impl(context):
    _require_success(context.calculator.command("opdup"))
    _require_success(context.calculator.command("multiplicative_inverse"))


@when(u'the players compute the relu of the share')
def step_impl(context):
    _require_success(context.calculator.command("relu"))


@when(u'the players compute the sum of the share')
def step_impl(context):
    _require_success(context.calculator.command("sum"))


@when(u'the players compute the zigmoid of the share')
def step_impl(context):
    _require_success(context.calculator.command("zigmoid"))


@when(u'the players divide the shares')
def step_impl(context):
    _require_success(context.calculator.command("untruncated_divide"))
    _require_success(context.calculator.command("truncate"))


@given(u'the players extract the share storage')
def step_impl(context):
    _require_success(context.calculator.command("sharestorage"))


@when(u'the players generate {bits} random bits')
def step_impl(context, bits):
    bits = eval(bits)
    _require_success(context.calculator.command("oppush", value=bits))
    _require_success(context.calculator.command("random_bitwise_secret"))


@when(u'the players multiply the shares')
def step_impl(context):
    _require_success(context.calculator.command("untruncated_multiply"))
    _require_success(context.calculator.command("truncate"))


@when(u'the players multiply the shares without truncation')
def step_impl(context):
    _require_success(context.calculator.command("untruncated_multiply"))


@when(u'the players raise the share to a public power')
def step_impl(context):
    _require_success(context.calculator.command("private_public_power"))


@when(u'the players reveal the result')
def step_impl(context):
    _require_success(context.calculator.command("reveal"))
    _require_success(context.calculator.command("decode"))


@when(u'the players reveal the result without decoding')
def step_impl(context):
    _require_success(context.calculator.command("reveal"))


@when(u'the players swap')
def step_impl(context):
    _require_success(context.calculator.command("opswap"))


@when(u'the players subtract the public value from the share')
def step_impl(context):
    _require_success(context.calculator.command("private_public_subtract"))


@then(u'{count} {name} protocol objects can be created without error')
def step_impl(context, count, name):
    count = eval(count)
    for index in range(count):
        _require_success(context.calculator.command("protopush", name=name))


@then(u'the result should match {rhs} to within {digits} digits')
def step_impl(context, rhs, digits):
    rhs = eval(rhs)
    digits = eval(digits)

    for lhs in _require_success(context.calculator.command("opget")):
        numpy.testing.assert_array_almost_equal(lhs, rhs, decimal=digits)


@then(u'the result should match {rhs}')
def step_impl(context, rhs):
    rhs = eval(rhs)

    for lhs in _require_success(context.calculator.command("opget")):
        numpy.testing.assert_array_equal(lhs, rhs)


@then(u'the two values should not be equal')
def step_impl(context):
    values = _require_success(context.calculator.command("opgetn", n=2))
    for lhs, rhs in values:
        test.assert_false(numpy.array_equal(lhs, rhs))


@then(u'the value of the bits in big-endian order should match the random value.')
def step_impl(context):
    values = _require_success(context.calculator.command("oppop"))
    bits = _require_success(context.calculator.command("oppop"))
    print(bits, values)

    for bits, value in zip(bits, values):
        test.assert_equal(value, numpy.sum(numpy.power(2, numpy.arange(len(bits))[::-1]) * bits))

