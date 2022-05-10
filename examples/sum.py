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
import pprint

import numpy

import cicada.communicator
import cicada.encoder
import cicada.additive

logging.basicConfig(level=logging.INFO)

def main(communicator):
    log = cicada.Logger(logging.getLogger(), communicator)
    protocol = cicada.additive.AdditiveProtocol(communicator)

    secret_a = numpy.array(2) if communicator.rank == 0 else None
    secret_b = numpy.array(3.5) if communicator.rank == 1 else None

    log.info(f"Player {communicator.rank} secret a: {secret_a}", src=0)
    log.info(f"Player {communicator.rank} secret b: {secret_b}", src=1)

    a_share = protocol.share(src=0, secret=protocol.encoder.encode(secret_a), shape=())
    b_share = protocol.share(src=1, secret=protocol.encoder.encode(secret_b), shape=())

    log.info(f"Player {communicator.rank} share of a: {a_share}")
    log.info(f"Player {communicator.rank} share of b: {b_share}")

    sum_share = protocol.add(a_share, b_share)

    log.info(f"Player {communicator.rank} share of sum: {sum_share}")

    sum = protocol.encoder.decode(protocol.reveal(sum_share))

    log.info(f"Player {communicator.rank} sum: {sum}")
    log.info(f"Player {communicator.rank} stats: {pprint.pformat(communicator.stats)}")

cicada.communicator.SocketCommunicator.run(world_size=3, fn=main)

