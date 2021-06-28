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

import cicada.communicator
import cicada.encoder
import cicada.additive

logging.basicConfig(level=logging.INFO)

@cicada.communicator.NNGCommunicator.run(world_size=3)
def main(communicator):
    log = cicada.Logger(logging.getLogger(), communicator)
    encoder = cicada.encoder.FixedFieldEncoder()
    protocol = cicada.additive.AdditiveProtocol(communicator)

    value = numpy.random.choice(2, size=8) if communicator.rank == 0 else numpy.zeros(shape=8)
    log.info(f"Player {communicator.rank} value: {value}")
    share = protocol.secret(encoder=encoder, src=0, value=value)
    revealed = protocol.reveal(share)
    log.info(f"Player {communicator.rank} revealed: {revealed}, type:{type(share._share._storage[0])}")


main()
