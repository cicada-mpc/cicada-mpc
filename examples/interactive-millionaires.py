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

import numpy

import cicada.additive
import cicada.communicator
import cicada.interactive

logging.basicConfig(level=logging.INFO)

with cicada.communicator.SocketCommunicator(timeout=300) as communicator:
    log = cicada.Logger(logging.getLogger(), communicator)
    protocol = cicada.additive.AdditiveProtocol(communicator)

    winner = None
    winning_share = protocol.share(src=0, secret=protocol.encoder.zeros(shape=()), shape=())

    for rank in communicator.ranks:
        fortune_share = cicada.interactive.secret_input(protocol=protocol, encoder=protocol.encoder, src=rank, prompt="Fortune: ")
        less_share = protocol.less(fortune_share, winning_share)
        less = protocol.reveal(less_share)
        if not less:
            winner = rank
            winning_share = fortune_share

    log.info(f"Player {communicator.rank} winner: {winner}")

