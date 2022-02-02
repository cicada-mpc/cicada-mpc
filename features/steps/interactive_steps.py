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

import unittest.mock

from behave import *

import cicada.interactive
from cicada.communicator import SocketCommunicator


@when(u'player {} receives secret input {}')
def step_impl(context, player, text):
    player = eval(player)
    text = eval(text)

    def operation(communicator, player, text):
        cicada.interactive.input = unittest.mock.MagicMock(return_value=text)
        return cicada.interactive.secret_input(communicator=communicator, src=player)

    context.results = SocketCommunicator.run(world_size=context.players, fn=operation, args=(player, text))


