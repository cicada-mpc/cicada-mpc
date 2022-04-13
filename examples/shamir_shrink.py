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
import logging
import os
import signal

import numpy

from cicada.communicator import SocketCommunicator
import cicada.encoder
import cicada.shamir

logging.basicConfig(level=logging.INFO)

def main(communicator):
    with contextlib.ExitStack() as resources:
        log = cicada.Logger(logging.getLogger(), communicator)
        shamir = cicada.shamir.ShamirProtocol(communicator)
        encoder = cicada.encoder.FixedFieldEncoder()

        # Player 0 will provide a secret.
        secret = numpy.array(numpy.pi) if communicator.rank == 0 else None
        log.info(f"Player {communicator.rank} secret: {secret}")

        # Generate shares for all players.
        share = shamir.share(src=0, secret=encoder.encode(secret), shape=())
        log.info(f"Player {communicator.rank} share: {share}")

        # Nice player ya got there.  It'd be a real shame
        # if they had a most unfortunate and unexpected accident.
        if communicator.rank == 3:
            os.kill(os.getpid(), signal.SIGKILL)

        try:
            # This is a placeholder that represents whatever
            # computation we happened to be performing at the
            # time of the failure.
            revealed = encoder.decode(shamir.reveal(share))
            logging.info("-" * 60, src=0)
            logging.info(f"Player {communicator.rank} revealed: {revealed}")
            logging.info(f"Player {communicator.rank} made it!")
        except Exception as e:
            logging.info(f"Player {communicator.rank} in the exception: {e}")
            # Something went wrong.  Revoke our communicator to
            # ensure that all players are aware of it.
            communicator.revoke()
            # Obtain a new communicator that contains the remaining players.
            newcommunicator, old_ranks = communicator.shrink(name="smallworld")
            logging.info('#'*10+'\nold_ranks: '+str(old_ranks)+'\nold indicies: '+str(shamir.indicies)+'\nnew indicies: '+str([shamir.indicies[x] for x in old_ranks]))
            # run() automatically cleans-up the old communicator, this
            # will ensure that we properly cleanup the new one.
            resources.enter_context(newcommunicator)
            # These objects must be recreated from scratch since they use
            # the communicator that was revoked.
            log = cicada.Logger(logging.getLogger(), newcommunicator)
            shamir = cicada.shamir.ShamirProtocol(newcommunicator, indicies=[shamir.indicies[x] for x in old_ranks])
            logging.info('#'*10+'current indicies: '+str(shamir.indicies)+' current ranks: '+str(newcommunicator.ranks))
        finally:
            logging.info(f"Player {communicator.rank} in final block")



        # Now we can continue on with our work ...

        # Reveal the secret to all players.
        revealed = encoder.decode(shamir.reveal(share))
        log.info(f"Player {newcommunicator.rank} (formerly {old_ranks[newcommunicator.rank]}) revealed: {revealed}")


SocketCommunicator.run(world_size=5, fn=main)
