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
import time
import cicada.communicator
import cicada.active
import cicada.additive
import cicada.shamir
from copy import deepcopy

logging.basicConfig(level=logging.INFO)

dumb_change = 0

smart_change = not dumb_change 

def main(communicator):
    log = cicada.Logger(logging.getLogger(), communicator)
    protocol = cicada.active.ActiveProtocolSuite(communicator, threshold=3)
    dp_len = 100000
    # Player 0 will provide a secret which is a scalar.
    secret = numpy.full((dp_len,),1) #if communicator.rank == 0 else None
    z = numpy.zeros(1) #if communicator.rank == 0 else None
    log.info(f"Player {communicator.rank} secret: {secret}")

    # Create shares for the secret.
    t0 =time.time()
    share = protocol.share(src=0, secret=protocol.encoder.encode(secret), shape=secret.shape)
    acc = protocol.share(src=0, secret=protocol.encoder.encode(z), shape=z.shape)
    #log.info(f"Player {communicator.rank} share: {share}")

    modulus = 2**64-59
    #log.info(f"Player {communicator.rank} share consistency check: {protocol.check_commit(share)}")
    pr = protocol.untruncated_multiply(share, share)
    print(pr, pr.storage)
    za=0
    zs=0

    for i in range(dp_len):
        #print((pr.storage[0].storage[i], pr.storage[1].storage[i]))
        za += pr.storage[0].storage[i]
        zs += pr.storage[1].storage[i]
    dp = cicada.active.ActiveArrayShare((cicada.additive.AdditiveArrayShare(numpy.array(za%protocol.encoder.modulus, dtype=object)), cicada.shamir.ShamirArrayShare(numpy.array(zs%protocol.encoder.modulus, dtype=object))))
    dp = protocol.truncate(dp)
    tf = time.time()
    log.info(f"Player {communicator.rank} DP reveal check: {protocol.encoder.decode(protocol.reveal(dp))}, in {tf-t0}s")

cicada.communicator.SocketCommunicator.run(world_size=5, fn=main)

