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
    testVal =numpy.array([0, 1, 2, 3])# 2**64 - 59 -7
    log = cicada.Logger(logging.getLogger(), communicator)
    protocol = cicada.additive.AdditiveProtocol(communicator)
    generator = numpy.random.default_rng()

    bit_share, secret_share = protocol.random_bitwise_secret(generator=generator, bits=4, shape=testVal.shape)
    print(type(testVal), type(bit_share), type(bit_share.storage))
    secret = protocol.reveal(secret_share)
    secret_bits = protocol.reveal(bit_share)
    #log.info(f'{[0]+[int(x) for x in bin(testVal)[2:]]}\n{secret_bits}')
    lt = protocol._public_bitwise_less_than_vectorized(lhspub=testVal, rhs=bit_share)
    print(f'type of lt: {type(lt)} {type(lt.storage)}, shape lt: {lt.storage.shape}, shape orig: {testVal.shape}')
    revealed_lt = protocol.reveal(lt)
    log.info(f"Player {communicator.rank} secret: {testVal} {['<' if x==1 else '>=' for x in revealed_lt]} {secret}")


main()

