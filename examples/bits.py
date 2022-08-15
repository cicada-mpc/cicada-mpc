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

logging.basicConfig(level=logging.INFO)

def main(communicator):
    log = cicada.Logger(logging.getLogger(), communicator)
    encoder = cicada.encoder.FixedFieldEncoder()#modulus=11311, precision=2)
    protocol = cicada.additive.AdditiveProtocolSuite(communicator)#, modulus=11311, precision=2)


    # Player 0 will provide a secret.
    seed = 1234
    gen = numpy.random.default_rng(seed=seed)
    bits, share = protocol.random_bitwise_secret(bits=1, generator=gen)
    log.info(f"Player {communicator.rank} bits rev: {protocol.reveal(bits)}, secret rev: {protocol.reveal(share)}")

    seed = 1234
    gen = numpy.random.default_rng(seed=seed)
    bits, share = protocol.random_bitwise_secret(bits=2, generator=gen)
    log.info(f"Player {communicator.rank} bits rev: {protocol.reveal(bits)}, secret rev: {protocol.reveal(share)}")

    seed = 1234
    gen = numpy.random.default_rng(seed=seed)
    bits, share = protocol.random_bitwise_secret(bits=4, generator=gen)
    log.info(f"Player {communicator.rank} bits rev: {protocol.reveal(bits)}, secret rev: {protocol.reveal(share)}")

    seed = 1234
    gen = numpy.random.default_rng(seed=seed)
    bits, share = protocol.random_bitwise_secret(bits=8, generator=gen)
    log.info(f"Player {communicator.rank} bits rev: {protocol.reveal(bits)}, secret rev: {protocol.reveal(share)}")

cicada.communicator.SocketCommunicator.run(world_size=4, fn=main)

cicada.communicator.SocketCommunicator.run(world_size=14, fn=main)

cicada.communicator.SocketCommunicator.run(world_size=5, fn=main)
