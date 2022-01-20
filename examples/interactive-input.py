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

import cicada.additive
import cicada.communicator
import cicada.interactive

logging.basicConfig(level=logging.INFO)

with cicada.communicator.SocketCommunicator(timeout=300) as communicator:
    log = cicada.Logger(logging.getLogger(), communicator, sync=False)
    protocol = cicada.additive.AdditiveProtocol(communicator)

    share = cicada.interactive.secret_input(protocol=protocol, encoder=protocol.encoder, src=0)
    log.info(f"Player {communicator.rank} share: {share}")

    secret = protocol.encoder.decode(protocol.reveal(share))
    log.info(f"Player {communicator.rank} secret: {secret}")
