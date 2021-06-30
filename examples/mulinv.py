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
    generator = numpy.random.default_rng()

    secret_share = protocol.uniform(shape=(6,6))
    log.info(f"Player {communicator.rank} secret share: {secret_share}")

    secret = protocol.reveal(secret_share)
    log.info(f"Player {communicator.rank} secret: {secret}")

    secret_share_inv = protocol.multiplicative_inverse(secret_share)
    log.info(f"Player {communicator.rank} secret share inv: {secret_share_inv}")

    secret_inv = protocol.reveal(secret_share_inv)
    log.info(f"Player {communicator.rank} secret inv: {secret_inv}")

    product_share = protocol.untruncated_multiply(secret_share, secret_share_inv)
    log.info(f"Player {communicator.rank} product share: {product_share}")

    product = protocol.reveal(product_share)
    log.info(f"Player {communicator.rank} product: {product}")
main()

