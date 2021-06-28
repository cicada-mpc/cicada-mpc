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

import logging

import cicada.communicator
import numpy

logging.basicConfig(level=logging.INFO)

@cicada.communicator.NNGCommunicator.run(world_size=3)
def main(communicator):
    if communicator.rank == 0:
        logging.info(f"Player {communicator.rank} did nothing.")

    if communicator.rank == 1:
        value = communicator.recv(src=2)
        logging.info(f"Player {communicator.rank} received {value}.")

    if communicator.rank == 2:
        value = numpy.array(42, dtype=numpy.float32)
        communicator.send(value=value, dst=1)
        logging.info(f"Player {communicator.rank} sent {value}.")

main()

