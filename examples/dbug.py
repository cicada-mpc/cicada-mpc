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
    protocol = cicada.active.ActiveProtocol(communicator, threshold=3)#, modulus=11311, precision=2)


    # Player 0 will provide a secret.
    share3 = protocol.share(secret=protocol.encoder.encode(numpy.array(.3)), src=0, shape=())
    share5 = protocol.share(secret=protocol.encoder.encode(numpy.array(.5)), src=0, shape=())
    q = protocol.untruncated_divide(share5, share3)
    qtruncd = protocol.truncate(q)

    log.info(f"Player {communicator.rank} q: {protocol.encoder.decode(protocol.reveal(q))}")
    log.info(f"Player {communicator.rank} qtruncd: {protocol.encoder.decode(protocol.reveal(qtruncd))}")



cicada.communicator.SocketCommunicator.run(world_size=5, fn=main)

