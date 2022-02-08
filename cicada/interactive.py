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

"""Functionality for user interaction."""

import numpy

from cicada.communicator.interface import Communicator

def secret_input(*, communicator, src, prompt=None, dtype=float, timeout=300):
    """Prompt one user for a secret.

    Note
    ----
    Although this function only prompts one player for input, it is a
    collective operation that *must* be called by all players that are members
    of `communicator`.

    Parameters
    ----------
    communicator: :class:`~cicada.communicator.interface.Communicator`, required
        Used to coordinate among players.
    src: :class:`int`, required
        Rank of the player who will be prompted for a secret.
    prompt: :class:`str`, optional
        Override the default interactive prompt.  See :func:`input`
        for usage.
    dtype: :func:`callable`, optional
        Function for parsing user input into a final value.  The function must
        take one :class:`str` argument and return a result.  The builtin
        functions :class:`int`, :class:`float`, and :class:`str` are useful
        examples.
    timeout: :class:`numbers.Number`, optional
        Maximum time to wait for user input, in seconds. Defaults to 300 seconds.

    Returns
    -------
    value: :class:`object` or :any:`None`
        For player `src`: the secret input.  For all other players: :any:`None`.
    """
    if communicator.rank == src:
        if prompt is None:
            prompt = f"Enter a secret: "
        secret = numpy.array(dtype(input(prompt)))
    else:
        secret = None

    # Wait for user input.
    with communicator.override(timeout=timeout):
        communicator.barrier()

    return secret
