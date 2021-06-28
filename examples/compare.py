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
from tqdm import *
from time import time
from statistics import mean, stdev
logging.basicConfig(level=logging.INFO)

#########################################
# set these values to change behavior, 
# if random_ops is true, testVal1 and 2 will be ignored 
# if random_ops is false, the values that will be compared are set by testVal1 and 2
random_ops = True
testVal1 = numpy.array(0)
testVal2 = numpy.array(-8)
numRuns = 10000
#########################################

results = []
errors = {}
times = []
@cicada.communicator.NNGCommunicator.run(world_size=3)
def main(communicator):
    log = cicada.Logger(logging.getLogger(), communicator)
    protocol = cicada.additive.AdditiveProtocol(communicator)
    generator = numpy.random.default_rng()
    for i in tqdm(range(numRuns)):
        if random_ops:
            bit_share1, secret_share1 = protocol.random_bitwise_secret(generator=generator, bits=64)
            bit_share2, secret_share2 = protocol.random_bitwise_secret(generator=generator, bits=64)
        else:
            secret_share1 = protocol.share(src=0, secret=protocol.encoder.encode(testVal1), shape=testVal1.shape)
            secret_share2 = protocol.share(src=0, secret=protocol.encoder.encode(testVal2), shape=testVal2.shape)
        secret1 = protocol.encoder.decode(protocol.reveal(secret_share1))
        secret2 = protocol.encoder.decode(protocol.reveal(secret_share2))
        t0 = time()
        lt = protocol.less_than(lhs=secret_share1, rhs=secret_share2)
        times.append(time()-t0)
        revealed_lt = protocol.reveal(lt)
        if revealed_lt == 1 and secret1 < secret2:
            results.append(True)
        elif revealed_lt == 0 and secret1 >= secret2:
            results.append(True)
        else:
            results.append(False)
            errors[i]=(secret1, secret2, revealed_lt)

    log.info(f"Player {communicator.rank} {secret1} {'<' if revealed_lt else '>='} {secret2}")
    if not all(results):
        print(f'Num errors: {sum([1 for x in results if x==False])}')
        for k, v in errors.items():
            if v[2] == 1:
                symbol = '<'
            elif v[2] == 0:
                symbol = '>='
            else:
                symbol = '?'
            print(f'Run # {k}\n\t{v[0]} {symbol} {v[1]}')
    else: 
        print('No Errors!')
    print(f'Avg time: {mean(times)}\nStdev time: {stdev(times)}')
main()

