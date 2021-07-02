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
from random import randint, choice
logging.basicConfig(level=logging.INFO)

NUMROUNDS = 100

@cicada.communicator.NNGCommunicator.run(world_size=3)
def main(communicator):
    log = cicada.Logger(logging.getLogger(), communicator)
    protocol = cicada.additive.AdditiveProtocol(communicator)
    generator = numpy.random.default_rng()

    zero_share = protocol.share(src=0, secret=numpy.zeros(shape=(4,4), dtype = object), shape=(4,4))
    ltz_times = []
    comp_times = []
    my_rank = communicator.rank
    errcount = 0
    for i in range(NUMROUNDS):
        if my_rank == 0: print(f'\033[1;37;40m\nRound {i}: ')
        fieldsize = 2**64-59
        rand1 = numpy.array(randint(0,fieldsize), dtype=object)
        rand2 = numpy.array(randint(0,fieldsize), dtype=object)
        rand1dec = protocol.encoder.decode(rand1)
        rand2dec = protocol.encoder.decode(rand2)
        secret_share1 = protocol.share(src=0, secret=(rand1), shape = ())
        secret_share2 = protocol.share(src=0, secret=(rand2), shape = ())
        min_share = protocol.min(secret_share1, secret_share2)
        max_share = protocol.max(secret_share1, secret_share2)
        secret1 = protocol.encoder.decode(protocol.reveal(secret_share1))
        secret2 = protocol.encoder.decode(protocol.reveal(secret_share2))

        min_rev = protocol.encoder.decode(protocol.reveal(min_share))
        max_rev = protocol.encoder.decode(protocol.reveal(max_share))
        if my_rank == 0:
            if min_rev != min(rand1dec, rand2dec):
                errcount += 1
                colorcode = "\033[1;31;40m "  
            else:
                colorcode = "\033[1;32;40m "
            print(f'{colorcode}\tmin({secret1}, {secret2}) = {min_rev}')

            colorcode = "\033[1;31;40m " if max_rev != max(rand1dec, rand2dec) else "\033[1;32;40m "
            print(f'{colorcode}\tmax({secret1}, {secret2}) = {max_rev}')
    if my_rank == 0:
        print(f'\033[1;37;40m There were {errcount} errors') 

main()

