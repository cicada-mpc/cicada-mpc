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

import socket
import ssl

context = ssl.create_default_context(purpose=ssl.Purpose.CLIENT_AUTH)
context.load_cert_chain(certfile="cert.pem", keyfile="cert.pem")
context.check_hostname = False
context.verify_mode = ssl.CERT_NONE

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server = context.wrap_socket(server, server_side=True)

server.bind(("127.0.0.1", 10023))
server.listen(0)

while True:
    client, addr = server.accept()
    while True:
        data = client.recv(1024)
        if not data:
            break
        print(f"Received: {data}")
