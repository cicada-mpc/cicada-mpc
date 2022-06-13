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
import cicada.active

logging.basicConfig(level=logging.INFO)

def main(communicator):
    log = cicada.Logger(logging.getLogger(), communicator)
    protocol = cicada.active.ActiveProtocol(communicator, threshold=3)

    # Player 0 will provide a secret which is a scalar.
    secret = numpy.array([numpy.pi, 1,2,3]) if communicator.rank == 0 else None
    log.info(f"Player {communicator.rank} secret: {secret}")

    # Create shares for the secret.
    share = protocol.share(src=0, secret=protocol.encoder.encode(secret), shape=(4,))
    log.info(f"Player {communicator.rank} share: {share}")

    
    log.info(f"Player {communicator.rank} share consistency check: {protocol.check_consistency(share)}")
    if protocol.communicator.rank == 2:
        share[0].storage[0] += 1
    log.info(f"Player {communicator.rank} share consistency check: {protocol.check_consistency(share)}")

cicada.communicator.SocketCommunicator.run(world_size=5, fn=main)

