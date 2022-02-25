import logging

import numpy

import cicada.additive
import cicada.communicator
import cicada.interactive

logging.basicConfig(level=logging.INFO)

with cicada.communicator.SocketCommunicator.connect(startup_timeout=300) as communicator:
    log = cicada.Logger(logging.getLogger(), communicator)
    protocol = cicada.additive.AdditiveProtocol(communicator)

    total = protocol.share(src=0, secret=protocol.encoder.encode(numpy.array(0)), shape=())
    for i in range(communicator.world_size):
        secret = cicada.interactive.secret_input(communicator=communicator, src=i)
        share = protocol.share(src=i, secret=protocol.encoder.encode(secret), shape=())
        total = protocol.add(total, share)

    total = protocol.encoder.decode(protocol.reveal(total))
    log.info(f"Player {communicator.rank} total: {total}")
