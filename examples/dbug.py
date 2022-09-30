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
import cicada.active

logging.basicConfig(level=logging.INFO)

def main(communicator):
    log = cicada.Logger(logging.getLogger(), communicator)
    encoder = cicada.encoder.FixedFieldEncoder()#modulus=11311, precision=2)
    protocol = cicada.active.ActiveProtocolSuite(communicator, threshold=3)#, modulus=11311, precision=2)


    # Player 0 will provide a secret.
    sharen = protocol.share(secret=numpy.array(44.0625), src=0, shape=())
    #sharen = protocol.share(secret=numpy.array(44), src=0, shape=())
    shared = protocol.share(secret=numpy.array(1), src=0, shape=())
    success = 0
    for i in range(100):
        try:
            q = protocol.untruncated_divide(sharen, shared)
            revq = protocol.reveal(q)
            qtruncd = protocol.truncate(q)
            revtruncdq = protocol.reveal(qtruncd)
            success += 1
            log.info(f"round {i} success", src=0)
        except:
            log.info(f"round {i} failed", src=0)
    log.info(f"Player {communicator.rank} q: {revq}")
    log.info(f"Player {communicator.rank} qtruncd: {protocol.reveal(qtruncd)}")
    log.info(f"Succeeded {success}%", src=0)



cicada.communicator.SocketCommunicator.run(world_size=5, fn=main)

