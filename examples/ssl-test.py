import os
import ssl

from cicada.communicator import SocketCommunicator
from cicada.communicator.socket import connect

world_size = int(os.environ.get("CICADA_WORLD_SIZE"))
rank = int(os.environ.get("CICADA_RANK"))
address = os.environ.get("CICADA_ADDRESS")
root_address = os.environ.get("CICADA_ROOT_ADDRESS")

#server = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
server = ssl.SSLContext(protocol=ssl.PROTOCOL_TLS_SERVER)
#server.check_hostname = False

client = ssl.SSLContext(protocol=ssl.PROTOCOL_TLS_CLIENT)
#client = ssl.create_default_context()
client.check_hostname = False

timer = connect.Timer(threshold=5)
listen_socket = connect.listen(address=address, rank=rank, timer=timer, tls=server)
sockets = connect.rendezvous(listen_socket=listen_socket, root_address=root_address, world_size=world_size, rank=rank, timer=timer, tls=client)
with SocketCommunicator(sockets=sockets) as communicator:
    print(f"Hello from player {communicator.rank}!")
