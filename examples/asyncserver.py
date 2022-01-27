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
