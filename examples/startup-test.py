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
import logging

from cicada.communicator import SocketCommunicator

logging.basicConfig(level=logging.INFO)


parser = argparse.ArgumentParser(description="Startup timeout testing.")
parser.add_argument("--startup-timeout", "-t", type=float, default=5, help="Startup timeout. Default: %(default)s s")
parser.add_argument("--world-size", "-n", type=int, default=32, help="Number of players. Default: %(default)s")
arguments = parser.parse_args()

def main(communicator):
    return

SocketCommunicator.run(world_size=arguments.world_size, fn=main, startup_timeout=arguments.startup_timeout)

