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


parser = argparse.ArgumentParser(description="Cicada TLS tester.")
parser.add_argument("--debug", action="store_true", help="Enable verbose output.")
parser.add_argument("--iterations", "-n", type=int, default=10000, help="Iterations. Default: %(default)s")
parser.add_argument("--send-hack", action="store_true", help="Enable the send hack.")

arguments = parser.parse_args()

logging.basicConfig(level=logging.INFO)
if arguments.debug:
    logging.getLogger("cicada.communicator").setLevel(logging.INFO)

def main(communicator):
    if arguments.send_hack:
        for rank in communicator.ranks:
            result = communicator.broadcast(src=rank, value="bar")

    for index in range(arguments.iterations):
        try:
            for rank in [0]:
                result = communicator.broadcast(src=rank, value="foo")
        except Exception as e:
            print(f"Player {communicator.rank} exception: {e}")
            break
    print(f"Player {communicator.rank} stats: {communicator.stats}")

world_size = 3
identities = [f"player-{rank}.pem" for rank in range(world_size)]
peers = [f"player-{rank}.cert" for rank in range(world_size)]
SocketCommunicator.run(world_size=world_size, fn=main, identities=identities, peers=peers)


