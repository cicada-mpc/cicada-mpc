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
import time
import cicada.communicator
import cicada.active
from copy import deepcopy

logging.basicConfig(level=logging.INFO)

dumb_change = 0

smart_change = not dumb_change 

def main(communicator):
    log = cicada.Logger(logging.getLogger(), communicator)
    protocol = cicada.active.ActiveProtocolSuite(communicator, threshold=3)

    # Player 0 will provide a secret which is a scalar.
    secret = numpy.array([numpy.pi,1,-2,3]) if communicator.rank == 0 else None
    log.info(f"Player {communicator.rank} secret: {secret}")

    # Create shares for the secret.
    share = protocol.share(src=0, secret=secret, shape=(4,))
    #log.info(f"Player {communicator.rank} share: {share}")

    modulus = 2**64-59
    #log.info(f"Player {communicator.rank} share consistency check: {protocol.check_commit(share)}")
    log.info(f"Player {communicator.rank} share reveal check: {protocol.reveal(share)}")
    log.info(f"Player {communicator.rank} Entering Malicious activity, since we're messing with things in a {['dumb', 'smart'][smart_change]} way,\nthe consistency check should fail in the {['first', 'second'][smart_change]} step.", src=0)
    bad_share = deepcopy(share)
    if protocol.communicator.rank == 3 and dumb_change:
        bad_share[0].storage[0] += 1
    if protocol.communicator.rank == 0 and smart_change:
        bad_share[0].storage[1] += 1
        bad_share[1].storage[1] = (bad_share[1].storage[1] + pow(5, modulus-2, modulus)) % modulus
    try:
        log.info(f"Player {communicator.rank} share consistency check - should be True: {protocol.verify(bad_share)}")
    except cicada.active.ConsistencyError as e:
        print(f'Malicious alteration detected: {e}')
    try:
        log.info(f"Player {communicator.rank} share reveal check: {protocol.reveal(bad_share)}")
    except cicada.active.ConsistencyError as e:
        log.info(f'Malicious alteration detected: {e}')



    log.info("\n\nLet's try some operations...", src=0)
    double_share = protocol.add(share, share)
    try:
        log.info(f"Player {communicator.rank} share consistency check - should be True: {protocol.verify(double_share)}")
    except cicada.active.ConsistencyError as e:
        print(f'Malicious alteration detected: {e}')
    try:
        log.info(f"Player {communicator.rank} double share reveal check: {protocol.reveal(double_share)}")
    except cicada.active.ConsistencyError as e:
        log.info(f'Malicious alteration detected: {e}')



    square_share = protocol.untruncated_multiply(share, share)
    square_share = protocol.truncate(square_share)
    try:
        log.info(f"Player {communicator.rank} share consistency check - should be True: {protocol.verify(square_share)}")
    except cicada.active.ConsistencyError as e:
        print(f'Malicious alteration detected: {e}')
    try:
        log.info(f"Player {communicator.rank} share reveal check: {protocol.reveal(square_share)}")
    except cicada.active.ConsistencyError as e:
        log.info(f'Malicious alteration detected: {e}')




    log.info(f"\n\nFinally we'll mess with the results of the previous computation now, since we're messing with things in a {['dumb', 'smart'][smart_change]} way,\nthe consistency check should fail in the {['first', 'second'][smart_change]} step.", src=0)
    if protocol.communicator.rank == 3 and dumb_change:
        square_share[0].storage[0] += 1
    if protocol.communicator.rank == 0 and smart_change:
        square_share[0].storage[1] += 1
        square_share[1].storage[1] = (square_share[1].storage[1] + pow(5, modulus-2, modulus)) % modulus
    try:
        log.info(f"Player {communicator.rank} share consistency check - should be True: {protocol.verify(square_share)}")
    except cicada.active.ConsistencyError as e:
        print(f'Malicious alteration detected: {e}')
    try:
        log.info(f"Player {communicator.rank} share reveal check: {protocol.reveal(square_share)}")
    except cicada.active.ConsistencyError as e:
        log.info(f'Malicious alteration detected: {e}')

cicada.communicator.SocketCommunicator.run(world_size=5, fn=main)

