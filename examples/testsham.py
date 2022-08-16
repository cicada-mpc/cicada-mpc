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
    encoder = cicada.encoder.FixedFieldEncoder()#modulus=11311, precision=2)
    shamirk = cicada.shamir.ShamirBasic(communicator, threshold=2)#, modulus=11311, precision=2)
    shamir = cicada.shamir.ShamirProtocolSuite(communicator, threshold=2)#, modulus=11311, precision=2)

    print(f'indicies: {shamir.indices}')

    # Player 0 will provide a secret.
    secret = numpy.arange(24).reshape((2,3,4))
    log.info(f"Player {communicator.rank} secret: {secret}")

    share = shamirk.share(src=0, secret=encoder.encode(secret),shape=secret.shape)
    log.info(f"Kernel Player {communicator.rank} share shape: {share.storage.shape}, secret shape: {secret.shape}")

    log.info(f"Kernel Player {communicator.rank} share: {share}")#, src=0)
    # Reveal the secret to player one, using just three shares.
    #log.info(f"Player {communicator.rank} share: {share}")
    tmp = shamirk.reveal(share)#, src=[0, 2, 3], dst=[0])
    #log.info(f"Player {communicator.rank} encoded: {tmp}")
    revealed = encoder.decode(tmp)
    log.info(f"Kernel Player {communicator.rank} revealed: {revealed}")#, src=0)

    share = shamir.share(src=0, secret=encoder.encode(secret),shape=secret.shape)
    log.info(f"Player {communicator.rank} share shape: {share.storage.shape}, secret shape: {secret.shape}")

    log.info(f"Player {communicator.rank} share: {share}")#, src=0)
    # Reveal the secret to player one, using just three shares.
    #log.info(f"Player {communicator.rank} share: {share}")
    tmp = shamir.reveal(share)#, src=[0, 2, 3], dst=[0])
    #log.info(f"Player {communicator.rank} encoded: {tmp}")
    revealed = encoder.decode(tmp)
    log.info(f"Player {communicator.rank} revealed: {revealed}")#, src=0)

    summation = shamir.add(share, share)

    tmp = shamir.reveal(summation)
    #log.info(f"Player {communicator.rank} encoded: {tmp}")
    revealed = encoder.decode(tmp)
    log.info(f"Player {communicator.rank} revealed sum: {revealed}", src=0)

    product = shamir.untruncated_multiply(share, share)

    tmp = shamir.reveal(product)
    #log.info(f"Player {communicator.rank} encoded: {tmp}")
    revealed = encoder.decode(tmp)
    log.info(f"Player {communicator.rank} revealed product: {revealed}", src=0)

    zig = shamir.zigmoid(share)

    tmp = shamir.reveal(zig)
    #log.info(f"Player {communicator.rank} encoded: {tmp}")
    revealed = encoder.decode(tmp)
    log.info(f"Player {communicator.rank} revealed product: {revealed}", src=0)

    rand = shamir.uniform(shape=(2,2))

    tmp = shamir.reveal(rand)
    #log.info(f"Player {communicator.rank} encoded: {tmp}")
    revealed = encoder.decode(tmp)
    log.info(f"Player {communicator.rank} revealed uniform: {revealed}")

cicada.communicator.SocketCommunicator.run(world_size=5, fn=main)

