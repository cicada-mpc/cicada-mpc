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
import itertools
import logging
import os
import signal

import numpy

from cicada.communicator import SocketCommunicator
from cicada.logging import Logger
from cicada.shamir import ShamirBasicProtocolSuite

parser = argparse.ArgumentParser(description="Failure recovery tester.")
parser.add_argument("--pfail", type=float, default="0.01", help="Probability that a process will fail during the current iteration. Default: %(default)s")
parser.add_argument("--seed", type=int, default=1234, help="Random seed. Default: %(default)s")
parser.add_argument("--world-size", "-n", type=int, default=32, help="Number of players. Default: %(default)s")
arguments = parser.parse_args()

logging.basicConfig(level=logging.INFO)
logging.getLogger("cicada.communicator").setLevel(logging.CRITICAL)


def random_failures(pfail, seed):
    generator = numpy.random.default_rng(seed=seed)

    while True:
        if generator.uniform() <= pfail:
            os.kill(os.getpid(), signal.SIGKILL)
        yield


def main(communicator):
    # One-time initialization.
    communicator_index = itertools.count(1)
    failure = random_failures(pfail=arguments.pfail, seed=arguments.seed + communicator.rank)

    log = Logger(logging.getLogger(), communicator)
    protocol = ShamirBasicProtocolSuite(communicator, threshold=2)

    total_share = protocol.share(src=0, secret=numpy.array(0), shape=())

    # Main iteration loop.
    for iteration in itertools.count():
        # Allow players to fail at random.
        next(failure)

        # Do computation in this block.
        try:
            # Increment the total.
            contributor = iteration % communicator.world_size
            increment = numpy.array(1) if communicator.rank == contributor else None
            increment_share = protocol.share(src=contributor, secret=increment, shape=())
            total_share = protocol.add(total_share, increment_share)

            # Print the current total.
            total = protocol.reveal(total_share)
            log.info(f"Iteration {iteration} comm {communicator.name} total: {total}", src=0)

        # Implement failure recovery in this block. Be careful here! Many
        # operations can't be used when there are unresponsive players.
        except Exception as e:
            # Something went wrong.  Revoke the current communicator to
            # ensure that all players are aware of it.
            communicator.revoke()

            # If we don't have enough players to continue, it's time to shutdown cleanly.
            if communicator.world_size == protocol.threshold:
                log.info(f"Iteration {iteration} not enough players to continue.", src=0)
                break

            # Obtain a new communicator that contains the remaining players.
            name = f"world-{next(communicator_index)}"
            newcommunicator, oldranks = communicator.shrink(name=name)

            # Recreate the logger since objects that depend on the old,
            # revoked communicator must be rebuilt from scratch using the
            # new communicator.
            log = Logger(logging.getLogger(), newcommunicator)
            log.info(f"Iteration {iteration} shrank comm {communicator.name} with {communicator.world_size} players to comm {newcommunicator.name} with {newcommunicator.world_size} players.", src=0)

            # Recreate the protocol since objects that depend on the old,
            # revoked communicator must be rebuilt from scratch using the
            # new communicator.
            protocol = ShamirBasicProtocolSuite(newcommunicator, threshold=2, indices=protocol.indices[oldranks])

            # Cleanup the old communicator.
            communicator.free()
            communicator = newcommunicator


SocketCommunicator.run(world_size=arguments.world_size, fn=main, name="world-0")
