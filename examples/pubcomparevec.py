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
from random import randint

logging.basicConfig(level=logging.INFO)
numinarray = 1000000
@cicada.communicator.NNGCommunicator.run(world_size=3)
def main(communicator):
    testVal =numpy.array([x for x in range(numinarray)])# 2**64 - 59 -7
    log = cicada.Logger(logging.getLogger(), communicator)
    protocol = cicada.additive.AdditiveProtocol(communicator)
    generator = numpy.random.default_rng()

    bit_share, secret_share = protocol.random_bitwise_secret(generator=generator, bits=20, shape=testVal.shape)
    print(type(testVal), type(bit_share), type(bit_share.storage))
    secret = protocol.reveal(secret_share)
    secret_bits = protocol.reveal(bit_share)
    #log.info(f'{[0]+[int(x) for x in bin(testVal)[2:]]}\n{secret_bits}')
    lt = protocol._public_bitwise_less_than_vectorized(lhspub=testVal, rhs=bit_share)
    print(f'type of lt: {type(lt)} {type(lt.storage)}, shape lt: {lt.storage.shape}, shape orig: {testVal.shape}')
    revealed_lt = protocol.reveal(lt)
    comp_str = []
    for i in range(numinarray):
        if revealed_lt[i] == 0:
            comp_str.append(' >= ')
        elif revealed_lt[i] == 1:
            comp_str.append(' < ')
        else:
            comp_str.append(' ##### ERROR ##### ')


    log.info(f"Player {communicator.rank} secret: {[str(testVal[i])+comp_str[i]+str(secret[i]) for i in range(numinarray)]}")
    test_result = []
    for i in range(numinarray):
        try:
            if testVal[i] < secret[i] and revealed_lt[i]:
                test_result.append(True)
            elif testVal[i] >= secret[i] and not revealed_lt[i]:
                test_result.append(True)
            else:
                test_result.append(False)
        except:
            print(i, testVal[i] , secret[i] , revealed_lt[i])
    print(all(test_result))



main()

