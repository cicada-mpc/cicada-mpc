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

def secret_input(*, protocol, encoder, src, prompt=None, dtype=float):
    """Interactive prompt for a secret.

    Note
    ----
    Although this function only prompts one player for input, it is a
    collective operation that *must* be called by all players that are members
    of the communicator owned by `protocol`.

    Parameters
    ----------
    protocol: any protocol object, required
        Generates shares of the the secret value.
    src: int, required
        Rank of the player who will be prompted for a secret.
    prompt: str, optional
        Override the default interactive prompt.  See :func:`input`
        for usage.
    dtype: callable, optional
        Function for parsing user input into a secret-sharable value.  The
        function must take zero or one argument.  In the zero argument case, it
        should return a value which will be ignored.  In the one argument case,
        it must accept a string and return a scalar type that can be encoded
        and secret shared.  The builtin functions :func:`int` and :func:`float`
        are useful examples that provide this behavior.

    Returns
    -------
    share:
        A share of the secret input.  The type of the returned value will depend
        on the choice of protocol.
    """
    if protocol.communicator.rank == src:
        if prompt is None:
            prompt = f"Player {protocol.communicator.rank} secret: "
        secret = numpy.array(dtype(input(prompt)))
    else:
        secret = numpy.array(dtype())

    # Wait indefinitely for user input.
    with protocol.communicator.override(timeout=None):
        protocol.communicator.barrier()

    # Secret-share the input.
    return protocol.share(src=src, secret=encoder.encode(secret), shape=())
