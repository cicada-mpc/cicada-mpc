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
import traceback

import numpy

import cicada.communicator

logging.basicConfig(level=logging.DEBUG)


rank=int(os.environ["RANK"])

try:
    if numpy.random.uniform() < 0.1:
        logging.error(f"Player {rank} bailing out!!!")
        exit(-1)

    receiver, players = cicada.communicator.nng.setup_sockets(
        link_addr=os.environ["LINK_ADDR"],
        host_addr=os.environ["HOST_ADDR"],
        world_size=int(os.environ["WORLD_SIZE"]),
        rank=rank,
        token=numpy.random.uniform() < 0.1,
#        token=42,
        )
except Exception as e:
    logging.error(f"Player {rank} exception: {e}")
