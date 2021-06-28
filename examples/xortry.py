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
expected = [0,1/2**16,1/2**16,0]

logging.basicConfig(level=logging.INFO)

@cicada.communicator.NNGCommunicator.run(world_size=3)
def main(communicator):
    log = cicada.Logger(logging.getLogger(), communicator)

    #Works pretty reliably with a 54 bit prime, gets unstable in a hurry with bigger than 54 bits, very reliably with 48 bits or smaller
    #Suspicions lie with things getting inappropriately cast as Numpy ints again.
    # default 64 bit prime: 18446744073709551557 = (2^64)-59 
    # 56 bit prime: 72057594037927931 = (2^56-5) or 52304857833066023 a safe prime
    # 54 bit prime: 10420223883547487
    # 48 bit prime: 149418408868787
    # 32 bit prime: 4034875883
    # small prime: 7919
    encoder = cicada.encoder.FixedFieldEncoder()     
    protocol = cicada.additive.AdditiveProtocol(communicator)

    secret1 = protocol.secret(encoder=encoder, src=0, value=numpy.array([1/2**16, 1/2**16, 0, 0]))
    secret0 = protocol.secret(encoder=encoder, src=0, value=numpy.array([1/2**16, 0, 1/2**16, 0])) 
    revealedsecret = protocol.reveal(secret1) 
    log.info(f"Player {communicator.rank} revealed: {revealedsecret} expected: {[1/2**16, 1/2**16, 0, 0]}")
#    print('top op: ', secretly32)
    secretMuld = protocol.xor_matvec_elementwise(op1 = secret1, op2 = secret0)
    revealedSecretTruncd = protocol.reveal(secretMuld)
    log.info(f"Player {communicator.rank} revealed: {revealedSecretTruncd} expected: {expected}")

main()
