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

import numpy

from cicada.communicator import SocketCommunicator
from cicada.shamir import ShamirProtocolSuite

def main(communicator):
    protocol = ShamirProtocolSuite(communicator, threshold=2)
    a = numpy.arange(25).reshape((5,5))
    identity = numpy.identity(5)

    ashare = protocol.share(src=0, secret=a, shape=a.shape)
    idshare = protocol.share(src=0, secret=identity, shape=identity.shape)


    print("revealed:", protocol.reveal(ashare))
    fdpshare = protocol.folklore_dot(ashare, idshare)
    print("revealed folklore dot product share:", protocol.reveal(fdpshare))
    print(f'should communicate {communicator.world_size*25*64} bits')
    dpshare = protocol.dot(ashare, idshare)
    print("revealed dot product share:", protocol.reveal(dpshare))
    #print(f'should communicate {communicator.worldsize*25*64} bits')


SocketCommunicator.run(world_size=3, fn=main)
