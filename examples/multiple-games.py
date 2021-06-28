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

import collections
import logging

import numpy

import cicada.communicator
import cicada.additive

logging.basicConfig(level=logging.INFO)

Game = collections.namedtuple("Game", ["communicator", "log", "generator"])

@cicada.communicator.NNGCommunicator.run(world_size=4)
def main(communicator):
    # Setup multiple games with separate communicators.
    games = []
    partitions = [[0, 1, 2], [1, 2, 3], [2, 3, 0]]
    for index, partition in enumerate(partitions):
        game_communicator = communicator.split(group=f"game-{index}" if communicator.rank in partition else None)
        if game_communicator is not None:
            game = Game(
                communicator=game_communicator,
                log=cicada.Logger(logging.getLogger(), game_communicator),
                generator=numpy.random.default_rng(),
                )
            games.append(game)

    # Run games in round-robin fashion.
    for i in range(2):
        for game in games:
            if game.communicator.rank == 0:
                value = game.generator.uniform()
            else:
                value = None
            value = game.communicator.broadcast(src=0, value=value)
            game.log.info(f"{game.communicator.name} player {game.communicator.rank} received broadcast value: {value}")

    # Cleanup games.
    for game in games:
        game.communicator.free()

main()

