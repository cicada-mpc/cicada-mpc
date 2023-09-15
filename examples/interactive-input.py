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

from cicada.additive import AdditiveProtocolSuite
from cicada.communicator import SocketCommunicator
from cicada.interactive import secret_input
from cicada.logging import Logger

logging.basicConfig(level=logging.INFO)

with SocketCommunicator.connect(startup_timeout=300) as communicator:
    log = Logger(logging.getLogger(), communicator)
    protocol = AdditiveProtocolSuite(communicator)

    secret = secret_input(communicator=communicator, src=0)
    log.info(f"Player {communicator.rank} secret: {secret}")

    secret_share = protocol.share(src=0, secret=secret, shape=())
    log.info(f"Player {communicator.rank} share: {secret_share}")

