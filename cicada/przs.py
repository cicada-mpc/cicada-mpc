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

"""Pseudorandom Zero-Sharing functionality."""

import numpy

from cicada.arithmetic import Field
from cicada.communicator.interface import Communicator, Tag


class PRZSProtocol(object):
    """Implements the Pseudorandom Zero-Sharing protocol of Cramer, Damgard, and Ishai.

    Note
    ----
    Creating the protocol is a collective operation that *must*
    be implemented by all players that are members of `communicator`.

    Parameters
    ----------
    communicator: :class:`cicada.communicator.interface.Communicator`, required
        The communicator that this protocol will use for communication.
    field: :class:`cicada.arithmetic.Field`, required
        The field from which generated values will be drawn.
    seed: :class:`int`, optional
        Seed used to initialize random number generators.  For privacy, this
        value should be different for each player.
    """
    def __init__(self, *, communicator, field, seed):
        if not isinstance(communicator, Communicator):
            raise ValueError("A Cicada communicator is required.") # pragma: no cover
        self._communicator = communicator

        if not isinstance(field, Field):
            raise ValueError("A Cicada field is required.") # pragma: no cover
        self._field = field

        # Send random seed to next party, receive random seed from prev party
        if communicator.world_size >= 2:  # Otherwise sending seeds will segfault.
            next_rank = (communicator.rank + 1) % communicator.world_size
            prev_rank = (communicator.rank - 1) % communicator.world_size

            request = communicator.isend(value=seed, dst=next_rank, tag=Tag.PRZS)
            result = communicator.irecv(src=prev_rank, tag=Tag.PRZS)

            request.wait()
            result.wait()

            prev_seed = result.value
        else:
            prev_seed = seed

        # Setup random number generators
        self._g0 = numpy.random.default_rng(seed=seed)
        self._g1 = numpy.random.default_rng(seed=prev_seed)


    def __call__(self, *, shape):
        """Generate an array of field values that sum to zero, using pseudorandom zero-sharing.

        Note
        ----
        This is a collective operation that *must* be called
        by all players that are members of :attr:`communicator`.

        Parameters
        ----------
        shape: :class:`tuple`, required
            The shape of the result.  Note that all players must specify the
            same shape.

        Returns
        -------
        przs: :class:`numpy.ndarray`
            The local share of zeros.
        """
        if not isinstance(shape, tuple):
            shape = (shape,)

        przs = self.field.uniform(size=shape, generator=self._g0)
        self.field.inplace_subtract(przs, self.field.uniform(size=shape, generator=self._g1))

        return przs


    @property
    def communicator(self):
        """The :class:`~cicada.communicator.interface.Communicator` used by this protocol."""
        return self._communicator # pragma: no cover


    @property
    def field(self):
        """The :class:`~cicada.arithmetic.Field` used by this protocol."""
        return self._field

