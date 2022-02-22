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

import os
import ssl

from cicada.communicator import SocketCommunicator
from cicada.communicator.socket import connect

world_size = int(os.environ.get("CICADA_WORLD_SIZE"))
rank = int(os.environ.get("CICADA_RANK"))
address = os.environ.get("CICADA_ADDRESS")
root_address = os.environ.get("CICADA_ROOT_ADDRESS")

server = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
server.load_cert_chain(certfile=f"player-{rank}.pem")
for index in range(world_size):
    if index != rank:
        server.load_verify_locations(f"player-{index}.cert")
server.check_hostname=False
server.verify_mode = ssl.CERT_REQUIRED

client = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
client.load_cert_chain(certfile=f"player-{rank}.pem")
for index in range(world_size):
    if index != rank:
        client.load_verify_locations(f"player-{index}.cert")
client.check_hostname = False
client.verify_mode = ssl.CERT_REQUIRED

timer = connect.Timer(threshold=5)
listen_socket = connect.listen(address=address, rank=rank, timer=timer, tls=server)
sockets = connect.rendezvous(listen_socket=listen_socket, root_address=root_address, world_size=world_size, rank=rank, timer=timer, tls=client)
with SocketCommunicator(sockets=sockets) as communicator:
    value = communicator.broadcast(src=0, value="Hello!")
    print(f"Player {communicator.rank} received: {value}")


