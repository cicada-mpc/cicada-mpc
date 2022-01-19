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

import cicada.communicator
import cicada.shamir

@given(u'a minimum of {k} shares to recover a secret')
def step_impl(context, k):
    context.k = int(k)


@when(u'shamir secret sharing the same value for {count} sessions')
def step_impl(context, count):
    count = eval(count)

    @cicada.communicator.SocketCommunicator.run(world_size=context.players)
    def operation(communicator):
        protocol = cicada.shamir.ShamirProtocol(communicator)
        share = protocol.share(src=0, k=context.k, secret=numpy.array(5))
        return share._storage

    context.shares = []
    for i in range(count):
        context.shares.append(operation())
    context.shares = numpy.array(context.shares)


@when(u'shamir secret sharing the same value {count} times in one session')
def step_impl(context, count):
    count = eval(count)

    @cicada.communicator.SocketCommunicator.run(world_size=context.players)
    def operation(communicator, count):
        protocol = cicada.shamir.ShamirProtocol(communicator)
        shares = [protocol.share(src=0, k=context.k, secret=numpy.array(5))._storage for i in range(count)]
        return shares

    context.shares = numpy.column_stack(operation(count))


@when(u'player {player} shamir shares {secret} with {recipients} and {senders} reveal their shares to {destinations}')
def step_impl(context, player, secret, recipients, senders, destinations):
    player = eval(player)
    secret = numpy.array(eval(secret))
    recipients = eval(recipients)
    senders = eval(senders)
    destinations = eval(destinations)

    @cicada.communicator.SocketCommunicator.run(world_size=context.players)
    def operation(communicator):
        protocol = cicada.shamir.ShamirProtocol(communicator)
        share = protocol.share(src=player, k=context.k, secret=secret)
        return protocol.reveal(src=senders, share=share, dst=destinations)

    context.result = operation()


