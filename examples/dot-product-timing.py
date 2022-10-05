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

from cProfile import Profile
import pstats
import time

import numpy

from cicada.additive import AdditiveProtocolSuite
from cicada.shamir import ShamirProtocolSuite
from cicada.communicator import SocketCommunicator


def main(communicator, n):
    with Profile() as profile:
        proto = ShamirProtocolSuite(communicator, threshold=2)

        generator = numpy.random.default_rng()
        a = generator.uniform(size=n) if communicator.rank==0 else None
        b = generator.uniform(size=n) if communicator.rank==1 else None

        ashare = proto.share(src=0, secret=a, shape=n)
        bshare = proto.share(src=1, secret=b, shape=n)
        cshare = proto.dot(ashare, bshare)
        c = proto.reveal(cshare)

        if communicator.rank == 0:
            stats = pstats.Stats(profile)
            stats.sort_stats(pstats.SortKey.CUMULATIVE)
            stats.print_stats(30)

SocketCommunicator.run(world_size=3, fn=main, args=[100000], timeout=100)

