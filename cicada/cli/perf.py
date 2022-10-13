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

"""Provides a command line interface for running Cicada performance benchmarks.
"""

import argparse
import logging
import os
import sys
import time

import numpy

import cicada.additive
from cicada.communicator import SocketCommunicator


class Timer(object):
    def __init__(self):
        self._start = time.time()

    def elapsed(self):
        return time.time() - self._start


def identities(arguments):
    results = []
    for rank in range(arguments.world_size):
        identity = arguments.identity.format(rank=rank, world_size=arguments.world_size)
        if os.path.exists(identity):
            results.append(identity)
    if results:
        return results


def trusted(arguments):
    results = []
    for rank in range(arguments.world_size):
        trusted = arguments.trusted.format(rank=rank, world_size=arguments.world_size)
        if os.path.exists(trusted):
            results.append(trusted)
    if results:
        return results


def print_times(case, times):
    print(f"{case} min: {numpy.min(times):.3f}s mean: {numpy.mean(times):.3f}s max: {numpy.max(times):.3f}s stddev: {numpy.std(times):.3f}s")


def nonnegative_integer(string):
    value = int(string)
    if value < 1:
        raise ValueError("A positive integer is required.")
    return value


def positive_integer(string):
    value = int(string)
    if value < 1:
        raise ValueError("A positive integer is required.")
    return value


parser = argparse.ArgumentParser(description="Cicada MPC performance tests.")
subparsers = parser.add_subparsers(title="commands (choose one)", dest="command")

# broadcast
broadcast_subparser = subparsers.add_parser("broadcast", help="Test broadcast performance on the local machine.")
broadcast_subparser.add_argument("--count", default=10000, type=positive_integer, help="Number of broadcast operations. Default: %(default)s")
broadcast_subparser.add_argument("--identity", default="player-{rank}.pem", help="Player private key and certificate in PEM format. Default: %(default)s file, if it exists.")
broadcast_subparser.add_argument("--seed", default=1234, type=positive_integer, help="Random seed. Default: %(default)s")
broadcast_subparser.add_argument("--size", default=1000, type=positive_integer, help="Broadcast message size in bytes. Default: %(default)s")
broadcast_subparser.add_argument("--src", default=0, type=nonnegative_integer, help="Broadcast src player. Default: %(default)s")
broadcast_subparser.add_argument("--trusted", default="player-{rank}.cert", help="Trusted certificates in PEM format. Default: %(default)s files, if they exist.")
broadcast_subparser.add_argument("--world-size", "-n", type=int, default=3, help="Number of players. Default: %(default)s")

# floor
floor_subparser = subparsers.add_parser("floor", help="Test floor() performance on the local machine.")
floor_subparser.add_argument("--count", default=1, type=positive_integer, help="Number of floor() operations. Default: %(default)s")
floor_subparser.add_argument("--identity", default="player-{rank}.pem", help="Player private key and certificate in PEM format. Default: %(default)s file, if it exists.")
floor_subparser.add_argument("--seed", default=1234, type=positive_integer, help="Random seed. Default: %(default)s")
floor_subparser.add_argument("--trusted", default="player-{rank}.cert", help="Trusted certificates in PEM format. Default: %(default)s files, if they exist.")
floor_subparser.add_argument("--world-size", "-n", type=int, default=3, help="Number of players. Default: %(default)s")

# gather
gather_subparser = subparsers.add_parser("gather", help="Test gather performance on the local machine.")
gather_subparser.add_argument("--count", default=10000, type=positive_integer, help="Number of gather operations. Default: %(default)s")
gather_subparser.add_argument("--dst", default=0, type=nonnegative_integer, help="Gather dst player. Default: %(default)s")
gather_subparser.add_argument("--identity", default="player-{rank}.pem", help="Player private key and certificate in PEM format. Default: %(default)s file, if it exists.")
gather_subparser.add_argument("--seed", default=1234, type=positive_integer, help="Random seed. Default: %(default)s")
gather_subparser.add_argument("--size", default=1000, type=positive_integer, help="Gather message size in bytes. Default: %(default)s")
gather_subparser.add_argument("--trusted", default="player-{rank}.cert", help="Trusted certificates in PEM format. Default: %(default)s files, if they exist.")
gather_subparser.add_argument("--world-size", "-n", type=int, default=3, help="Number of players. Default: %(default)s")

# scatterv
scatterv_subparser = subparsers.add_parser("scatterv", help="Test scatterv performance on the local machine.")
scatterv_subparser.add_argument("--count", default=10000, type=positive_integer, help="Number of scatterv operations. Default: %(default)s")
scatterv_subparser.add_argument("--src", default=0, type=nonnegative_integer, help="Scatterv src player. Default: %(default)s")
scatterv_subparser.add_argument("--identity", default="player-{rank}.pem", help="Player private key and certificate in PEM format. Default: %(default)s file, if it exists.")
scatterv_subparser.add_argument("--seed", default=1234, type=positive_integer, help="Random seed. Default: %(default)s")
scatterv_subparser.add_argument("--size", default=1000, type=positive_integer, help="Scatterv message size in bytes. Default: %(default)s")
scatterv_subparser.add_argument("--trusted", default="player-{rank}.cert", help="Trusted certificates in PEM format. Default: %(default)s files, if they exist.")
scatterv_subparser.add_argument("--world-size", "-n", type=int, default=3, help="Number of players. Default: %(default)s")

# version
version_subparser = subparsers.add_parser("version", help="Print the Cicada version.")



def main():
    arguments = parser.parse_args()

    if arguments.command is None:
        parser.print_help()

    logging.basicConfig(level=logging.INFO)
    log = logging.getLogger()
    log.name = os.path.basename(sys.argv[0])

    # broadcast
    if arguments.command == "broadcast":

        def implementation(communicator, count, seed, size, src):
            generator = numpy.random.default_rng(seed=seed)
            timer = Timer()
            for index in range(count):
                value = generator.bytes(size) if communicator.rank == src else None
                value = communicator.broadcast(src=src, value=value)
            return timer.elapsed()

        case = f"{arguments.world_size} players broadcast {arguments.count} times using {arguments.size} byte messages"
        times = SocketCommunicator.run(world_size=arguments.world_size, fn=implementation, identities=identities(arguments), trusted=trusted(arguments), kwargs=dict(count=arguments.count, seed=arguments.seed, size=arguments.size, src=arguments.src))
        print_times(case, times)

    # floor
    if arguments.command == "floor":

        def implementation(communicator, count, seed):
            protocol = cicada.additive.AdditiveProtocol(communicator=communicator)
            generator = numpy.random.default_rng(seed=seed)
            timer = Timer()
            for index in range(count):
                value = generator.uniform(low=-5, high=5, size=()) if communicator.rank == 0 else None
                value_share = protocol.share(src=0, secret=protocol.encoder.encode(value), shape=())
                floor_share = protocol.floor(value_share)
            return timer.elapsed()

        case = f"{arguments.world_size} players compute floor() {arguments.count} times"
        times = SocketCommunicator.run(world_size=arguments.world_size, fn=implementation, identities=identities(arguments), trusted=trusted(arguments), kwargs=dict(count=arguments.count, seed=arguments.seed))
        print_times(case, times)

    # gather
    if arguments.command == "gather":

        def implementation(communicator, count, seed, size, dst):
            generator = numpy.random.default_rng(seed=seed)
            timer = Timer()
            for index in range(count):
                value = generator.bytes(size)
                value = communicator.gather(dst=dst, value=value)
            return timer.elapsed()

        case = f"{arguments.world_size} players gather {arguments.count} times using {arguments.size} byte messages"
        times = SocketCommunicator.run(world_size=arguments.world_size, fn=implementation, identities=identities(arguments), trusted=trusted(arguments), kwargs=dict(count=arguments.count, seed=arguments.seed, size=arguments.size, dst=arguments.dst))
        print_times(case, times)

    # scatterv
    if arguments.command == "scatterv":

        def implementation(communicator, count, seed, size, src, dst):
            generator = numpy.random.default_rng(seed=seed)
            timer = Timer()
            for index in range(count):
                values = [generator.bytes(size) for rank in dst] if communicator.rank == src else None
                value = communicator.scatterv(src=src, values=values, dst=dst)
            return timer.elapsed()

        case = f"{arguments.world_size} players scatterv {arguments.count} times using {arguments.size} byte messages"
        dst = [rank for rank in range(arguments.world_size) if rank != arguments.src]
        times = SocketCommunicator.run(world_size=arguments.world_size, fn=implementation, identities=identities(arguments), trusted=trusted(arguments), kwargs=dict(count=arguments.count, seed=arguments.seed, size=arguments.size, src=arguments.src, dst=dst))
        print_times(case, times)

    # version
    if arguments.command == "version":
        print(cicada.__version__)


