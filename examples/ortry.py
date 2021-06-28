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

numTruncBits =16
testVal = 2**14
expected = [1,1,1,0]

logging.basicConfig(level=logging.INFO)

@cicada.communicator.NNGCommunicator.run(world_size=3)
def main(communicator):
    log = cicada.Logger(logging.getLogger(), communicator)

    protocol = cicada.additive.AdditiveProtocol(communicator)
    op1 = numpy.array([1, 1, 0, 0], dtype=object)
    op2 = numpy.array([1, 0, 1, 0], dtype=object)
    secret1 = protocol.share(src=0, secret=op1, shape=op1.shape)
    secret0 = protocol.share(src=0, secret=op2, shape=op2.shape) 
    revealedsecret = protocol.reveal(secret1) 
    log.info(f"Player {communicator.rank} revealed: {revealedsecret} expected: {[1, 1, 0, 0]}")
    secretOrd = protocol.logical_or(lhs=secret1, rhs=secret0)
    revealedSecretOrd = protocol.reveal(secretOrd)
    log.info(f"Player {communicator.rank} revealed: {revealedSecretOrd} expected: {expected}")

main()
