import logging

import cicada.additive
import cicada.communicator
import cicada.interactive

logging.basicConfig(level=logging.INFO)

with cicada.communicator.SocketCommunicator.connect(startup_timeout=300) as communicator:
    log = cicada.Logger(logging.getLogger(), communicator, sync=False)
    protocol = cicada.additive.AdditiveProtocol(communicator)

    secret = cicada.interactive.secret_input(communicator=communicator, src=0)
    log.info(f"Player {communicator.rank} secret: {secret}")

    secret_share = protocol.share(src=0, secret=protocol.encoder.encode(secret), shape=())
    log.info(f"Player {communicator.rank} share: {secret_share}")

