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

@cicada.communicator.NNGCommunicator.run(world_size=3)
def main(communicator):
    log = cicada.Logger(logging.getLogger(), communicator)
    protocol = cicada.additive.AdditiveProtocol(communicator)

    secret_a = numpy.array(35, dtype=object) if communicator.rank == 0 else None
    b = numpy.array(7, dtype=object)
    b_enc = protocol.encoder.encode(b)

    log.info(f"Player {communicator.rank} secret a: {secret_a}", src=0)
    log.info(f"Player {communicator.rank} b: {b}", src=1)

    a_share = protocol.share(src=0, secret=secret_a, shape=())#secret=protocol.encoder.encode(secret_a), shape=())

    quotient_share = protocol.division_private_public(a_share, b)

    quotient = protocol.encoder.decode(protocol.reveal(quotient_share))
    log.info(f"Player {communicator.rank} quotient: {quotient}")

main()

