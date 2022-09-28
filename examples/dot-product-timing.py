from cProfile import Profile
import pstats
import time

import numpy

from cicada.additive import AdditiveProtocolSuite
from cicada.shamir import ShamirProtocolSuite
from cicada.communicator import SocketCommunicator


def main(communicator, n):
    with Profile() as profile:
        proto = AdditiveProtocolSuite(communicator)
        #proto = ShamirProtocolSuite(communicator, threshold=2)

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
            stats.print_stats("cicada", 20)

SocketCommunicator.run(world_size=3, fn=main, args=[100000], timeout=100)

