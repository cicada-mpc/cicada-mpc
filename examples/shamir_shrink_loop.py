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
import contextlib
import itertools
import logging
import os
import signal
import time

import numpy

from cicada.communicator import SocketCommunicator
import cicada.encoder
import cicada.shamir

logging.basicConfig(level=logging.INFO, format='%(asctime)s.%(msecs)03d %(message)s', datefmt="%H:%M:%S")


parser = argparse.ArgumentParser(description="Failure recovery tester.")
parser.add_argument("--debug", action="store_true", help="Enable verbose output.")
parser.add_argument("--mtbf", "-m", type=float, default="10", help="Mean time between failure in iterations. Default: %(default)s")
parser.add_argument("--seed", type=int, default=1234, help="Random seed. Default: %(default)s")
parser.add_argument("--world-size", "-n", type=int, default=32, help="Number of players. Default: %(default)s")
arguments = parser.parse_args()

lam = 1.0 / arguments.mtbf

def main(communicator):
    import manhole
    manhole.install()

    log = cicada.Logger(logging.getLogger(), communicator)
    shamir = cicada.shamir.ShamirProtocol(communicator, threshold=2)
    encoder = cicada.encoder.FixedFieldEncoder()
    generator = numpy.random.default_rng(seed=arguments.seed)

    communicator_index = itertools.count(1)

    # Player 0 will provide a secret.
    secret = numpy.array(0) if communicator.rank == 0 else None
    one = numpy.array(1) if communicator.rank == 0 else None

    # Generate shares for all players.
    share = shamir.share(src=0, secret=encoder.encode(secret), shape=())
    one_share = shamir.share(src=0, secret=encoder.encode(one), shape=())
    while True:
        try: # Do computation in this block.
            revealed = encoder.decode(shamir.reveal(share))
            share = shamir.add(one_share, share)
            log.info("-" * 60, src=0)
            log.info(f"Comm {communicator.name} player {communicator.rank} original rank {shamir.indices[communicator.rank]-1} revealed: {revealed}")
        except Exception as e: # Implement failure recovery in this block.
            try:
                log.sync = False
                log.error(f"Comm {communicator.name} player {communicator.rank} exception: {e}")
                # Something went wrong.  Revoke the current communicator to
                # ensure that all players are aware of it.
                communicator.revoke()
                # Obtain a new communicator that contains the remaining players.
                name = f"world-{next(communicator_index)}"
                newcommunicator, oldranks = communicator.shrink(name=name)
                # These objects must be recreated from scratch since they use
                # the communicator that was revoked.
                log = cicada.Logger(logging.getLogger(), newcommunicator)
                shamir = cicada.shamir.ShamirProtocol(newcommunicator, threshold=2, indices=shamir.indices[oldranks])
                log.info("-" * 60, src=0)
                log.info(f"Shrank {communicator.name} player {communicator.rank} to {newcommunicator.name} player {newcommunicator.rank}.")
                communicator.free()
                communicator = newcommunicator
            except ValueError as e:
                print('World has shrunk too small to continue, cleaning up experiment')
                break
        finally:
            time.sleep(0.1)

        # Figure-out how many processes will fail on this round.
        failures = generator.poisson(lam)

        # Decide which processes will fail.
        failures = generator.choice(communicator.world_size, size=failures, replace=False)

        # If we're one of the lambs, bail-out.
        if communicator.rank in failures:
            logging.info("-" * 60)
            logging.error(f"Comm {communicator.name} player {communicator.rank} dying!")
            os.kill(os.getpid(), signal.SIGKILL)


SocketCommunicator.run(world_size=arguments.world_size, fn=main, name="world-0")
