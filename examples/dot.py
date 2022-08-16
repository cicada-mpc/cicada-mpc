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

import argparse

import numpy

from cicada.communicator import SocketCommunicator
from cicada.additive import AdditiveProtcolSuite
from cicada.shamir import ShamirProtocolSuite
from cicada.active import ActiveProtocolSuite

parser = argparse.ArgumentParser(description="Dot product example.")
parser.add_argument("--seed", type=int, default=1234, help="Random seed. Default: %(default)s")
parser.add_argument("--timeout", type=float, default=10, help="Timeout. Default: %(default)ss")
parser.add_argument("--vector-size", "-v", type=int, default=10, help="Vector size. Default: %(default)s")
parser.add_argument("--world-size", "-n", type=int, default=3, help="Number of players. Default: %(default)s")
parser.add_argument("--protocol", "-p", default='additive', help="Protocol to use for SMC. Options are  \"additive\", \"shamir\", or \"active\". Default: %(default)s")
arguments = parser.parse_args()

def main(communicator):
    if arguments.protocol == 'additive':
        protocol = AdditiveProtcolSuite(communicator)
    elif arguments.protocol == 'shamir':
        t = ((arguments.world_size-1)//2)+1
        protocol = ShamirProtocolSuite(communicator, threshold=t)
    elif arguments.protocol == 'active':
        t = ((arguments.world_size-1)//2)+1
        protocol = ActiveProtocolSuite(communicator, threshold=t)
    else:
        raise ValueError('Invalid argument passed for protocol')
    generator = numpy.random.default_rng(seed=arguments.seed + communicator.rank)

    a = generator.uniform(size=arguments.vector_size)
    b = generator.uniform(size=arguments.vector_size)
    if communicator.rank == 0:
        print("  answer:", numpy.dot(a, b))

    ashare = protocol.share(src=0, secret=a, shape=arguments.vector_size)
    bshare = protocol.share(src=0, secret=b, shape=arguments.vector_size)
    cshare = protocol.dot(ashare, bshare)

    print("revealed:", protocol.reveal(cshare))

SocketCommunicator.run(world_size=arguments.world_size, fn=main, timeout=arguments.timeout)
