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

"""Functionality for working with Shamir-shared secrets."""

import numbers

import numpy
import shamir

from cicada.communicator.interface import Communicator


class ShamirArrayShare(object):
    """Stores a local share of a Shamir-secret-shared array.

    Parameters
    ----------
    shape: :class:`tuple`, required
        The shape of the stored array.
    storage: :class:`object`, required
        Opaque storage for the secret-shared value.  This is created and
        manipulated by :class:`ShamirProtocol`, and is off-limits to all others!
    """
    def __init__(self, shape, storage):
        self._shape = shape
        self._storage = storage


    def __repr__(self):
        return f"cicada.shamir.ShamirArrayShare(shape={self._shape}, storage={self._storage})" # pragma: no cover


class ShamirProtocol(object):
    """Uses a communicator to create and manipulate Shamir-secret-shared values.

    Parameters
    ----------
    communicator: :class:`cicada.communicator.interface.Communicator`, required
        The communicator that this protocol will use for collective operations.
    """
    def __init__(self, communicator):
        if not isinstance(communicator, Communicator):
            raise ValueError("A Cicada communicator is required.") # pragma: no cover
        self._communicator = communicator


    def _require_rank(self, rank, label):
        if not isinstance(rank, numbers.Integral):
            raise ValueError(f"Expected an integer for {label}, received {rank} instead.") # pragma: no cover
        if rank < 0 or rank >= self.communicator.world_size:
            raise ValueError(f"Expected {label} would be in the range [0, {self.communicator.world_size}), received {rank} instead.") # pragma: no cover
        return int(rank)


    def _require_rank_list(self, ranks, label):
        ranks = [self._require_rank(rank, label) for rank in ranks]
        if len(ranks) != len(set(ranks)):
            raise ValueError(f"Expected unique values for {label}, received {ranks} instead.") # pragma: no cover
        return ranks


    @property
    def communicator(self):
        """Returns the :class:`cicada.communicator.interface.Communicator` used by this protocol."""
        return self._communicator


    def reveal(self, share, src=None, dst=None):
        """Reconstruct a secret from its shares.

        Note
        ----
        This is a collective operation that *must* be called
        by all players that are members of :attr:`communicator`.

        Parameters
        ----------
        share: :class:`ShamirArrayShare`, or :any:`None`, required
            A local share of the secret to be revealed.  This value is ignored
            if the local player isn't contributing a share.
        src: sequence of :class:`int`, optional
            List of players who will supply shares of the secret to be revealed.
            If :any:`None` (the default), all players will supply a share.
        dst: sequence of :class:`int`, optional
            List of players who will receive the revealed secret.  If :any:`None`
            (the default), the secret will be revealed to all players.

        Returns
        -------
        value: :class:`numpy.ndarray` or :any:`None`
            The revealed secret, if this player is a member of `dst`,
            or :any:`None`.
        """

        # Identify who will be providing shares.
        if src is None:
            src = self.communicator.ranks

        # Identify who will be receiving shares.
        if dst is None:
            dst = self.communicator.ranks

        # Enforce preconditions.
        src = self._require_rank_list(src, "src")
        dst = self._require_rank_list(dst, "dst")

        if self.communicator.rank in src:
            if not isinstance(share, ShamirArrayShare):
                raise ValueError(f"share must be an instance of ShamirArrayShare, received {share} instead.") # pragma: no cover

        # Unpack data to exchange with the other players.
        value = (share._shape, share._storage) if self.communicator.rank in src else None

        # Send data to the other players.
        secret = None
        for recipient in dst:
            data = self.communicator.gatherv(src=src, value=value, dst=recipient)

            # If we're a recipient, recover the secret.
            if self.communicator.rank == recipient:
                shapes, shares = zip(*data)
                element_shares = numpy.array(shares).swapaxes(0, 1)
                secrets = [shamir.recover_secret(shares) for shares in element_shares]
                secret = numpy.array(secrets, dtype=object).reshape(shapes[0], order="C")

        return secret


    def share(self, *, src, secret, k, dst=None):
        """Distribute Shamir shares of a secret array.

        Note
        ----
        The input array must contain integers, and those integers
        must all be >= 0.

        This is a collective operation that *must* be called
        by all players that are members of :attr:`communicator`.

        Parameters
        ----------
        src: integer, required
            The player providing the secret array to be shared.
        secret: :class:`numpy.ndarray` or :any:`None`, required
            The secret array to be shared, which must contain integers >= 0.
            This value is ignored for all players but `src`.
        k: integer, required
            Minimum number of shares required to reveal the secret.
            Must be <= the number of players that are members of
            :attr:`communicator`.
        dst: sequence of :class:`int`, optional.
            List of players who will receive shares of the secret.  If
            :any:`None` (the default), all players will receive a share.

        Returns
        -------
        share: :class:`ShamirArrayShare` or :any:`None`
            Local share of the shared secret, if this player is a member of
            `dst`, or :any:`None`.
        """
        # Identify who will be receiving shares.
        if dst is None:
            dst = self.communicator.ranks

        # Enforce preconditions.
        src = self._require_rank(src, "src")

        if self.communicator.rank == src:
            if not isinstance(secret, numpy.ndarray):
                raise ValueError(f"secret must be an instance of numpy.ndarray, received {secret} instead.") # pragma: no cover
            if not issubclass(secret.dtype.type, (numpy.integer, object)):
                raise ValueError(f"secret must contain integers, received {secret.dtype} instead.") # pragma: no cover
            if not numpy.all(secret >= 0):
                raise ValueError("secret must contain values >= 0.") # pragma: no cover

        k = int(k)
        if not (1 <= k and k <= len(dst)):
            raise ValueError(f"k must be an integer in the range [1, {len(dst)}], received {k} instead.") # pragma: no cover

        # Create a shamir share for each element in the secret.
        if self.communicator.rank == src:
            all_shares = []
            for element in secret.flat: # Returns elements in C-style (last index varies fastest) order.
                constant, shares = shamir.make_random_shares(k, len(dst))
                shares = numpy.array(shares)
                shares[:,1] -= constant
                shares[:,1] += element
                all_shares.append(shares)
            all_shares = numpy.array(all_shares)
            all_shares = all_shares.swapaxes(0, 1)
            values = [(secret.shape, shares) for shares in all_shares]
        else:
            values = None

        # Distribute shares to all players.
        shares = self.communicator.scatterv(src=src, values=values, dst=dst)

        # Package the shares.
        return shares if shares is None else ShamirArrayShare(shares[0], shares[1])

