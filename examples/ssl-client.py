import socket
import ssl
import time

context = ssl.create_default_context(purpose=ssl.Purpose.SERVER_AUTH)

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client = context.wrap_socket(client, server_side=False, server_hostname="127.0.0.1")

client.connect(("127.0.0.1", 10023))

while True:
    client.send(b"Hello!")
    time.sleep(1)
