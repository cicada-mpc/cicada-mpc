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

from cicada.calculator import Client, PlayerError, main
from cicada.communicator import SocketCommunicator

import test

#logging.basicConfig(level=logging.INFO)


def _print_stacks(context, player=None):
    results = context.calculator.command("opstack", player=player)
    stacks = _require_success(results)
    players, results = results

    for rank, stack in zip(players, stacks):
        print(f"====== Remote stack (player {rank}) ======")
        for level, item in zip(range(len(stack)-1, -1, -1), stack):
            print(f"Level {level}: {item}")


def _require_success(results):
    players, results = results

    exceptions = {}
    for rank, result in zip(players, results):
        if isinstance(result, PlayerError):
            print(f"====== Remote traceback (player {rank}) ======\n{result.traceback}")
            exceptions[rank] = result

    if exceptions:
        raise RuntimeError(f"{len(exceptions)} players raised exceptions.")

    return results


@given(u'a calculator service with {world_size} players')
def step_impl(context, world_size):
    world_size = eval(world_size)
    addresses, processes = SocketCommunicator.run_forever(world_size=world_size, fn=main)
    context.calculator = Client(addresses)
    context.calculator_processes = processes


@given(u'a calculator service with {world_size} players using unix domain sockets')
def step_impl(context, world_size):
    world_size = eval(world_size)
    addresses, processes = SocketCommunicator.run_forever(world_size=world_size, fn=main, family="file")
    context.calculator = Client(addresses)
    context.calculator_processes = processes


@given(u'a new {name} protocol suite')
def step_impl(context, name):
    _require_success(context.calculator.command("protopush", name=name))


@given(u'public value {value}')
def step_impl(context, value):
    value = numpy.array(eval(value))
    _require_success(context.calculator.command("oppush", value=value))


@given(u'player {player} secret shares the bits {secret}')
def step_impl(context, player, secret):
    player = eval(player)
    secret = numpy.array(eval(secret))

    for rank in context.calculator.ranks:
        _require_success(context.calculator.command("oppush", value=secret if player == rank else None, player=rank))
    _require_success(context.calculator.command("protocol", subcommand="share_bits", src=player, shape=secret.shape))


@given(u'player {player} secret shares {secret}')
def step_impl(context, player, secret):
    player = eval(player)
    secret = numpy.array(eval(secret))

    for rank in context.calculator.ranks:
        _require_success(context.calculator.command("oppush", value=secret if player == rank else None, player=rank))
    _require_success(context.calculator.command("protocol", subcommand="share", src=player, shape=secret.shape))


@given(u'the players reshare the secret')
def step_impl(context):
    _require_success(context.calculator.command("protocol", subcommand="reshare"))


@given(u'player {player} tampers with the additive portion of its ActiveArrayShare')
def step_impl(context, player):
    player = eval(player)
    _require_success(context.calculator.command("opdup", player=player))
    _require_success(context.calculator.command("share", subcommand="getstorage", player=player))
    _require_success(context.calculator.command("opsplit", player=player))
    _require_success(context.calculator.command("opswap", player=player))
    _require_success(context.calculator.command("opdup", player=player))
    _require_success(context.calculator.command("share", subcommand="getstorage", player=player))
    _require_success(context.calculator.command("oppush", value=numpy.array(1), player=player))
    _require_success(context.calculator.command("add", player=player))
    _require_success(context.calculator.command("share", subcommand="setstorage", player=player))
    _require_success(context.calculator.command("opswap", player=player))
    _require_success(context.calculator.command("opcatn", player=player, n=2))
    _require_success(context.calculator.command("share", subcommand="setstorage", player=player))


@given(u'player {player} tampers with the shamir portion of its ActiveArrayShare')
def step_impl(context, player):
    player = eval(player)
    _require_success(context.calculator.command("opdup", player=player))
    _require_success(context.calculator.command("share", subcommand="getstorage", player=player))
    _require_success(context.calculator.command("opsplit", player=player))
    _require_success(context.calculator.command("opdup", player=player))
    _require_success(context.calculator.command("share", subcommand="getstorage", player=player))
    _require_success(context.calculator.command("oppush", value=numpy.array(1), player=player))
    _require_success(context.calculator.command("add", player=player))
    _require_success(context.calculator.command("share", subcommand="setstorage", player=player))
    _require_success(context.calculator.command("opcatn", player=player, n=2))
    _require_success(context.calculator.command("share", subcommand="setstorage", player=player))


@when(u'player {player} adds {value} to the share in-place')
def step_impl(context, player, value):
    player = eval(player)
    value = numpy.array(eval(value))
    _require_success(context.calculator.command("oppush", value=value, player=player))
    _require_success(context.calculator.command("protocol", subcommand="encode", player=player))
    _require_success(context.calculator.command("protocol", subcommand="inplace_add", player=player))


@when(u'player {player} subtracts {value} from the share in-place')
def step_impl(context, player, value):
    player = eval(player)
    value = numpy.array(eval(value))
    _require_success(context.calculator.command("oppush", value=value, player=player))
    _require_success(context.calculator.command("protocol", subcommand="encode", player=player))
    _require_success(context.calculator.command("protocol", subcommand="inplace_subtract", player=player))


@when(u'the players add the shares')
def step_impl(context):
    _require_success(context.calculator.command("protocol", subcommand="add"))


@when(u'the players compare the shares for equality')
def step_impl(context):
    _require_success(context.calculator.command("protocol", subcommand="equal"))


@when(u'the players compare the shares with less than')
def step_impl(context):
    _require_success(context.calculator.command("protocol", subcommand="less"))


@when(u'the players compare the shares with less than zero')
def step_impl(context):
    _require_success(context.calculator.command("protocol", subcommand="less_than_zero"))


@when(u'the players compute the absolute value of the share')
def step_impl(context):
    _require_success(context.calculator.command("protocol", subcommand="absolute"))


@when(u'the players compute the additive inverse')
def step_impl(context):
    _require_success(context.calculator.command("protocol", subcommand="additive_inverse"))


@when(u'the players compute the composition of the shared bits')
def step_impl(context):
    _require_success(context.calculator.command("protocol", subcommand="bit_compose"))


@when(u'the players compute the decomposition of the shared secrets')
def step_impl(context):
    _require_success(context.calculator.command("protocol", subcommand="bit_decompose"))


@when(u'the players compute the dot product of the shares')
def step_impl(context):
    _require_success(context.calculator.command("protocol", subcommand="dot"))


@when(u'the players compute the floor of the share')
def step_impl(context):
    _require_success(context.calculator.command("protocol", subcommand="floor"))


@when(u'the players compute the logical and of the shares')
def step_impl(context):
    _require_success(context.calculator.command("protocol", subcommand="logical_and"))


@when(u'the players compute the logical exclusive or of the shares')
def step_impl(context):
    _require_success(context.calculator.command("protocol", subcommand="logical_xor"))


@when(u'the players compute the logical not of the share')
def step_impl(context):
    _require_success(context.calculator.command("protocol", subcommand="logical_not"))


@when(u'the players compute the logical or of the shares')
def step_impl(context):
    _require_success(context.calculator.command("protocol", subcommand="logical_or"))


@when(u'the players compute the maximum of the shares')
def step_impl(context):
    _require_success(context.calculator.command("protocol", subcommand="max"))


@when(u'the players compute the minimum of the shares')
def step_impl(context):
    _require_success(context.calculator.command("protocol", subcommand="min"))


@when(u'the players compute the multiplicative inverse')
def step_impl(context):
    _require_success(context.calculator.command("opdup"))
    _require_success(context.calculator.command("protocol", subcommand="multiplicative_inverse"))


@when(u'the players compute the relu of the share')
def step_impl(context):
    _require_success(context.calculator.command("protocol", subcommand="relu"))


@when(u'the players compute the sum of the share')
def step_impl(context):
    _require_success(context.calculator.command("protocol", subcommand="sum"))


@when(u'the players compute the zigmoid of the share')
def step_impl(context):
    _require_success(context.calculator.command("protocol", subcommand="zigmoid"))


@when(u'the players divide the shares')
def step_impl(context):
    _require_success(context.calculator.command("protocol", subcommand="divide"))


@given(u'the players extract the share storage')
def step_impl(context):
    _require_success(context.calculator.command("share", subcommand="getstorage"))


@when(u'the players generate {bits} random bits')
def step_impl(context, bits):
    bits = eval(bits)
    _require_success(context.calculator.command("oppush", value=bits))
    _require_success(context.calculator.command("protocol", subcommand="random_bitwise_secret"))


@when(u'the players generate a private uniform array with shape {shape}')
def step_impl(context, shape):
    shape = eval(shape)
    _require_success(context.calculator.command("protocol", subcommand="uniform", shape=shape))


@when(u'the players multiply the shares')
def step_impl(context):
    _require_success(context.calculator.command("protocol", subcommand="multiply"))


@when(u'the players multiply the shares without truncation')
def step_impl(context):
    _require_success(context.calculator.command("protocol", subcommand="untruncated_multiply"))


@when(u'the players raise the share to the public power')
def step_impl(context):
    _require_success(context.calculator.command("protocol", subcommand="private_public_power"))


@when(u'the players raise the share to the public power in the field')
def step_impl(context):
    _require_success(context.calculator.command("protocol", subcommand="private_public_power_field"))


@when(u'the players reveal the secret')
def step_impl(context):
    _require_success(context.calculator.command("protocol", subcommand="reveal"))


@when(u'the players reveal the secret bits')
def step_impl(context):
    _require_success(context.calculator.command("protocol", subcommand="reveal_bits"))


@when(u'the players reveal the field values')
def step_impl(context):
    _require_success(context.calculator.command("protocol", subcommand="reveal_field"))


@when(u'the players subtract the shares')
def step_impl(context):
    _require_success(context.calculator.command("protocol", subcommand="subtract"))


@when(u'the players swap')
def step_impl(context):
    _require_success(context.calculator.command("opswap"))


@when(u'the players verify the share')
def step_impl(context):
    _require_success(context.calculator.command("protocol", subcommand="verify"))


@then(u'{count} {name} protocol objects can be created without error')
def step_impl(context, count, name):
    count = eval(count)
    for index in range(count):
        _require_success(context.calculator.command("protopush", name=name))


@then(u'the players can retrieve a complete copy of the operand stack')
def step_impl(context):
    context.opstack = _require_success(context.calculator.command("opstack"))


@then(u'the stack should match {stack} for all players')
def step_impl(context, stack):
    stack = eval(stack)
    for playerstack in context.opstack:
        test.assert_equal(len(stack), len(playerstack))
        for lhs, rhs in zip(stack, playerstack):
            numpy.testing.assert_array_equal(lhs, rhs)


@then(u'the result should match {rhs} to within {digits} digits')
def step_impl(context, rhs, digits):
    rhs = eval(rhs)
    digits = eval(digits)

    for lhs in _require_success(context.calculator.command("opget")):
        numpy.testing.assert_array_almost_equal(lhs, rhs, decimal=digits)

@then(u'the results should match {rhs} to within {digits} digits')
def step_impl(context, rhs, digits):
    rhs = eval(rhs)
    digits = eval(digits)

    for lhs in _require_success(context.calculator.command("opget")):
        print(lhs)
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

    for bits, value in zip(bits, values):
        test.assert_equal(value, numpy.sum(numpy.power(2, numpy.arange(len(bits))[::-1]) * bits))


@when(u'the players raise {exception}')
def step_impl(context, exception):
    exception = eval(exception)
    players, results = context.calculator.command("raise", exception=exception)
    context.errors = results


@then(u'the returned exceptions should match {exception}')
def step_impl(context, exception):
    exception = eval(exception)
    for error in context.errors:
        test.assert_is(type(error.exception), type(exception))
        test.assert_equal(error.exception.args, exception.args)


@then(u'the results should match shape {shape}')
def step_impl(context, shape):
    shape = eval(shape)
    results = _require_success(context.calculator.command("opget"))
    for result in results:
        test.assert_equal(shape, result.shape)


