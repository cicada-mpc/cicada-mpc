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

logging.basicConfig(level=logging.INFO)

@cicada.communicator.SocketCommunicator.run(world_size=3)
def main(communicator):
    log = cicada.Logger(logging.getLogger(), communicator)

    communicator.barrier()

    log.info("")
    log.info("Protocol with default seed", src=0)
    log.info("   - shares are different every run:", src=0)
    protocol = cicada.additive.AdditiveProtocol(communicator)
    share = protocol.share(src=0, secret=protocol.encoder.encode(numpy.array(2)), shape=())
    log.info(f"Player {communicator.rank} share: {share}")

    log.info("")
    log.info("Protocol with explicit seed and default seed offset", src=0)
    log.info("   - shares are the same each run, but differ between players:", src=0)
    protocol = cicada.additive.AdditiveProtocol(communicator, seed=321)
    share = protocol.share(src=0, secret=protocol.encoder.encode(numpy.array(2)), shape=())
    log.info(f"Player {communicator.rank} share: {share}")

    log.info("")
    log.info("Protocol with explicit seed and explicit seed offset", src=0)
    log.info("   - every share is zero except for the owner of a secret:", src=0)
    protocol = cicada.additive.AdditiveProtocol(communicator, seed=321, seed_offset=0)
    share = protocol.share(src=0, secret=protocol.encoder.encode(numpy.array(2)), shape=())
    log.info(f"Player {communicator.rank} share: {share}")

    log.info("")
main()

