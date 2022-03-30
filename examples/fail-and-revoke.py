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
import os
import logging
import signal
import time

import numpy

from cicada.communicator import SocketCommunicator


parser = argparse.ArgumentParser(description="Demonstrate recovering from a failure.")
parser.add_argument("--debug", action="store_true", help="Enable debugging output.")
parser.add_argument("-n", "--players", type=int, default=5, help="Number of players. Default: %(default)s")
parser.add_argument("-p", "--pfail", type=float, default=0.01, help="Probability of player failure. Default: %(default)s")
arguments = parser.parse_args()

logging.basicConfig(level=logging.DEBUG if arguments.debug else logging.INFO)
#logging.getLogger("cicada.communicator").setLevel(logging.DEBUG if arguments.debug else logging.INFO)

def main(communicator):
    numpy.random.seed()

    value = communicator.rank
    next_rank = (communicator.rank + 1) % communicator.world_size
    prev_rank = (communicator.rank - 1) % communicator.world_size

    # Do "computation"
    for index in itertools.count():
        try:
            # Players blow-up at random.
            if numpy.random.uniform() < arguments.pfail:
                logging.error(f"Player {communicator.rank} ************************************* BOOM!")
                os.kill(os.getpid(), signal.SIGKILL)

            communicator.send(value=value, dst=next_rank)
            value = communicator.recv(src=prev_rank)
            logging.info(f"Player {communicator.rank} received value: {value}")
            time.sleep(0.5)
        except Exception as e:
            logging.error(f"Player {communicator.rank} exception: {type(e)} {e}")
            break

    # Something went wrong, so revoke the communicator and try to recover.
    try:
        communicator.revoke()
        newcommunicator, old_ranks = communicator.shrink(name="world")
        print(newcommunicator.world_size)
    except Exception as e:
        logging.error(f"Player {communicator.rank} exception during shrink: {type(e)} {e}")
        #traceback.print_exc()

SocketCommunicator.run(world_size=arguments.players, fn=main)

