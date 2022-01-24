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
import os
import signal

import cicada.communicator.nng

logging.basicConfig(level=logging.INFO)


def main(communicator):
    # Example of a normal return value.
    if communicator.rank == 0:
        return 42
    # Example of a failure that raises an exception.
    if communicator.rank == 1:
        raise RuntimeError("Ahhhh! YOU GOT ME!")
    # Example of a process that dies unexpectedly.
    if communicator.rank == 2:
        os.kill(os.getpid(), signal.SIGKILL)

cicada.communicator.SocketCommunicator.run(world_size=3, fn=main)

