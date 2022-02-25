import logging

import cicada.additive
import cicada.communicator
import cicada.interactive

logging.basicConfig(level=logging.INFO)

with cicada.communicator.SocketCommunicator.connect(startup_timeout=300) as communicator:
    log = cicada.Logger(logging.getLogger(), communicator)
    protocol = cicada.additive.AdditiveProtocol(communicator)

    winner = None
    winning_share = protocol.share(src=0, secret=protocol.encoder.zeros(shape=()), shape=())

    for rank in communicator.ranks:
        fortune = cicada.interactive.secret_input(communicator=communicator, src=rank, prompt="Fortune: ")
        fortune_share = protocol.share(src=rank, secret=protocol.encoder.encode(fortune), shape=())
        less_share = protocol.less(fortune_share, winning_share)
        less = protocol.reveal(less_share)
        if not less:
            winner = rank
            winning_share = fortune_share

    log.info(f"Player {communicator.rank} winner: {winner}")
