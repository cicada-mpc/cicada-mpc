import socket
import ssl

context = ssl.create_default_context(purpose=ssl.Purpose.CLIENT_AUTH)
#context.load_cert_chain(certfile="cert.pem", keyfile="cert.pem")
#context.check_hostname = False

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
