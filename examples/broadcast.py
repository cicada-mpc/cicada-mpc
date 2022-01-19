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

import numpy

import cicada.communicator

logging.basicConfig(level=logging.INFO)

@cicada.communicator.SocketCommunicator.run(world_size=4)
def main(communicator):
    log = cicada.Logger(logging.getLogger(), communicator)

    value = numpy.array(3.14) if communicator.rank == 0 else None
    result = communicator.broadcast(src=0, value=value)
    log.info(f"Player {communicator.rank} received broadcast value: {result}")

    communicator.free()
    communicator.log_stats()

main()

