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
import time

import numpy

import cicada.communicator

logging.basicConfig(level=logging.INFO)

parser = argparse.ArgumentParser()
parser.add_argument("--mtbf", type=float, default=10, help="Mean time between failure in seconds. Default: %(default)s")
parser.add_argument("--players", "-n", type=int, default=3, help="Number of players. Default: %(default)s")
arguments = parser.parse_args()

lam = 1.0 / arguments.mtbf

def main(communicator):
    log = cicada.Logger(logging.getLogger(), communicator)
    generator = numpy.random.default_rng()

    # Broadcasts happen once per second, so our timeout needs to be longer
    communicator.timeout = 2

    log.info("-" * 20, src=0)
    for i in itertools.count():
        failures = generator.poisson(lam)
        if failures:
            logging.warning(f"Player {communicator.rank} failing.")
            return

        try:
            tensor = numpy.array(i) if communicator.rank == 0 else None
            tensor = communicator.broadcast(src=0, value=tensor)
            log.info(f"Player {communicator.rank} received: {tensor}")
            log.info("-" * 20, src=0)
        except Exception as e:
            logging.error(f"Player {communicator.rank} exception: {e}.")
            return

        if communicator.rank == 0:
            time.sleep(1)

cicada.communicator.SocketCommunicator.run(world_size=arguments.players, fn=main)

