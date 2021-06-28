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

import contextlib
import itertools
import logging
import os
import signal
import time

import numpy

import cicada.communicator
import cicada.encoder
import cicada.shamir

logging.basicConfig(level=logging.INFO)

@cicada.communicator.NNGCommunicator.run(world_size=8)
def main(communicator):
    with contextlib.ExitStack() as resources:
        log = cicada.Logger(logging.getLogger(), communicator)
        shamir = cicada.shamir.ShamirProtocol(communicator)
        encoder = cicada.encoder.FixedFieldEncoder()
        generator = numpy.random.default_rng(seed=communicator.rank)

        communicator_index = itertools.count(2)

        # Player 0 will provide a secret.
        secret = numpy.array(numpy.pi) if communicator.rank == 0 else None
        log.info(f"Comm {communicator.name} player {communicator.rank} secret: {secret}")

        # Generate shares for all players.
        share = shamir.share(src=0, k=3, secret=encoder.encode(secret))
        log.info(f"Comm {communicator.name} player {communicator.rank} share: {share}")

        while True:
            try: # Do computation in this block.
                revealed = encoder.decode(shamir.reveal(share))
                log.info("-" * 60, src=0)
                log.info(f"Comm {communicator.name} player {communicator.rank} revealed: {revealed}")
            except Exception as e: # Implement failure recovery in this block.
                logging.error(f"Comm {communicator.name} player {communicator.rank} exception: {e}")
                # Something went wrong.  Revoke the current communicator to
                # ensure that all players are aware of it.
                communicator.revoke()
                # Obtain a new communicator that contains the remaining players.
                name = f"world-{next(communicator_index)}"
                communicator, old_ranks = communicator.shrink(name=name)
                # Ensure that the newly created communicator gets cleaned-up.
                resources.enter_context(communicator)
                # These objects must be recreated from scratch since they use
                # the communicator that was revoked.
                log = cicada.Logger(logging.getLogger(), communicator)
                shamir = cicada.shamir.ShamirProtocol(communicator)
            finally:
                time.sleep(1.0)

            # Our processes are remarkably failure-prone.
            if generator.uniform() < 0.05:
                logging.error(f"Comm {communicator.name} player {communicator.rank} dying!")
                os.kill(os.getpid(), signal.SIGKILL)

main()

