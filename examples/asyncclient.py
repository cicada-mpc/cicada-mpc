import asyncio
import socket

class Client(object):
    def __init__(self):
        asyncio.run(self._start())

    async def _start(self):
        loop = asyncio.get_running_loop()

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setblocking(False)

        await loop.sock_connect(sock, ("", 25000))
        print("connected")
        await loop.sock_sendall(sock, b"hello!")
        print(await loop.sock_recv(sock, 100))

c = Client()

