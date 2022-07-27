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
from cicada.additive import AdditiveProtocol

parser = argparse.ArgumentParser(description="Dot product example.")
parser.add_argument("--seed", type=int, default=1234, help="Random seed. Default: %(default)s")
parser.add_argument("--timeout", type=float, default=10, help="Timeout. Default: %(default)ss")
parser.add_argument("--vector-size", "-v", type=int, default=10, help="Vector size. Default: %(default)s")
parser.add_argument("--world-size", "-n", type=int, default=3, help="Number of players. Default: %(default)s")
arguments = parser.parse_args()

def main(communicator):
    protocol = AdditiveProtocol(communicator)
    generator = numpy.random.default_rng(seed=arguments.seed + communicator.rank)

    a = generator.uniform(size=arguments.vector_size)
    b = generator.uniform(size=arguments.vector_size)
    if communicator.rank == 0:
        print(numpy.dot(a, b))

    ashare = protocol.share(src=0, secret=protocol.encoder.encode(a), shape=arguments.vector_size)
    bshare = protocol.share(src=0, secret=protocol.encoder.encode(b), shape=arguments.vector_size)

    cshare = protocol.untruncated_multiply(ashare, bshare)
    cshare = protocol.sum(cshare)
    cshare = protocol.truncate(cshare)

    c = protocol.encoder.decode(protocol.reveal(cshare))
    print(c)

SocketCommunicator.run(world_size=arguments.world_size, fn=main, timeout=arguments.timeout)
