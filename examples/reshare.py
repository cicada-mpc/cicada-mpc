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

from cicada.additive import AdditiveProtocolSuite
from cicada.communicator import SocketCommunicator
from cicada.logging import Logger

logging.basicConfig(level=logging.INFO)

def main(communicator):
    log = Logger(logging.getLogger(), communicator=communicator)
    protocol = AdditiveProtocolSuite(communicator=communicator)

    a = numpy.array(5.5)
    a_share = protocol.share(src=0, secret=a, shape=a.shape)
    log.info(f"Player {communicator.rank} share: {a_share}")
    log.info(f"Player {communicator.rank} revealed: {protocol.reveal(a_share)}")
    a_share = protocol.reshare(a_share)
    log.info(f"Player {communicator.rank} new share: {a_share}")
    log.info(f"Player {communicator.rank} revealed: {protocol.reveal(a_share)}")

SocketCommunicator.run(world_size=3, fn=main)
