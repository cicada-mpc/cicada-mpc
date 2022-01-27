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

import asyncio
import socket

class Server(object):
    def __init__(self):
        asyncio.run(self._start())

    async def _start(self):
        loop = asyncio.get_running_loop()

        sock = socket.create_server(("", 25000))
        sock.setblocking(False)
        sock.listen(5)

        for i in range(4):
            client, addr = await asyncio.wait_for(loop.sock_accept(sock), timeout=5)
            print(client, addr)
            msg = await loop.sock_recv(client, 100)
            print(msg)
            await loop.sock_sendall(client, b"whatever")

s = Server()
