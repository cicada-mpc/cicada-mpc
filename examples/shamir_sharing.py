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
import cicada.shamir

logging.basicConfig(level=logging.INFO)

def main(communicator):
    log = cicada.Logger(logging.getLogger(), communicator)
    shamir = cicada.shamir.ShamirProtocol(communicator)
    encoder = cicada.encoder.FixedFieldEncoder()

    # Player 0 will provide a secret.
    secret = numpy.array(numpy.pi) if communicator.rank == 0 else None
    log.info(f"Player {communicator.rank} secret: {secret}")

    # Generate shares for four out of five players.
    share = shamir.share(src=0, k=3, secret=encoder.encode(secret), dst=[0, 2, 3, 4])
    log.info(f"Player {communicator.rank} share: {share}")

    # Reveal the secret to player one, using just three shares.
    revealed = encoder.decode(shamir.reveal(share, src=[2, 3, 4], dst=[1]))
    log.info(f"Player {communicator.rank} revealed: {revealed}")

cicada.communicator.SocketCommunicator.run(main, world_size=5)

