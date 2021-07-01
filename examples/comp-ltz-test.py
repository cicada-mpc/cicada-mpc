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
from time import time
from statistics import mean, stdev

logging.basicConfig(level=logging.INFO)

NUMROUNDS = 10

@cicada.communicator.NNGCommunicator.run(world_size=3)
def main(communicator):
    log = cicada.Logger(logging.getLogger(), communicator)
    protocol = cicada.additive.AdditiveProtocol(communicator)
    generator = numpy.random.default_rng()

    zero_share = protocol.share(src=0, secret=numpy.zeros(shape=(4,4), dtype = object), shape=(4,4))
    ltz_times = []
    comp_times = []
    my_rank = communicator.rank
    for i in range(NUMROUNDS):
        if my_rank == 0: print(f'\nRound {i}: ')
        secret_share = protocol.uniform(shape=(4,4))
        t0 =time()
        ltz_share = protocol.less_than_zero(secret_share)
        t1 = time()
        ltz_times.append(t1-t0)
        print(f'\tltz time {my_rank}: {t1-t0}s')
        t0=time()
        comp_zero = protocol.less(secret_share, zero_share)
        t1 = time()
        comp_times.append(t1-t0)
        print(f'\tcomp time {my_rank}: {t1-t0}s')
    
    print(f'mean ltz_time {my_rank}: {mean(ltz_times)}\t stdev: {stdev(ltz_times)}')
    print(f'mean comp_time {my_rank}: {mean(comp_times)}\t stdev: {stdev(comp_times)}')

main()

