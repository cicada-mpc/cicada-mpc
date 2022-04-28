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

"""Functionality for creating, manipulating, and revealing shamir-shared secrets."""

import logging
from math import ceil
from random import randrange

import numpy

from cicada.communicator.interface import Communicator
import cicada.encoder

class ShamirArrayShare(object):
    """Stores the local share of an shamir-shared secret array.

    Parameters
    ----------
    storage: :class:`numpy.ndarray`, required
        Local shamir share of a secret array, which *must* have been encoded
        using :class:`cicada.encoder.fixedfield.FixedFieldEncoder`.
    """
    def __init__(self, storage):
        self.storage = storage


    def __repr__(self):
        return f"cicada.shamir.ShamirArrayShare(storage={self._storage})" # pragma: no cover

    @property
    def storage(self):
        """Local share of an shamir-shared secret array.

        Returns
        -------
        storage: :class:`numpy.ndarray`
            The local shamir share of the secret array.  The share is encoded
            using an instance of
            :class:`cicada.encoder.fixedfield.FixedFieldEncoder` which is owned
            by an instance of :class:`ShamirProtocol`, and **must** be used
            for any modifications to the share value.
        """
        return self._storage


    @storage.setter
    def storage(self, storage):
        if not isinstance(storage, numpy.ndarray):
            raise ValueError(f"Expected storage to be an instance of numpy.ndarray, got {type(storage)} instead.") # pragma: no cover
        self._storage = storage

class ShamirBasicProtocol(object):
    """MPC protocol that uses a communicator to share and manipulate shamir-shared secrets.

    Note
    ----
    Creating the protocol is a collective operation that *must*
    be called by all players that are members of `communicator`.

    Parameters
    ----------
    communicator: :class:`cicada.communicator.interface.Communicator`, required
        The communicator that this protocol will use for communication.
    seed: :class:`int`, optional
        Seed used to initialize random number generators.  For privacy, this
        value should be different for each player.  By default, the seed will
        be chosen at random, and is guaranteed to be different even on forked
        processes.  If you specify `seed` yourself, the actual seed used will
        be the sum of this value and the value of `seed_offset`.
    seed_offset: :class:`int`, optional
        Value added to the value of `seed`.  This value defaults to the player's
        rank.
    modulus: :class:`int`, optional
        Field size for storing encoded values.  Defaults to the largest prime
        less than 2^64 (2**64-59).
    precision: :class:`int`, optional
        The number of bits for storing fractions in encoded values.  Defaults
        to 16.
    """
    def __init__(self, communicator,*, threshold, seed=None, seed_offset=None, modulus=18446744073709551557, precision=16,  indices=None):
        if not isinstance(communicator, Communicator):
            raise ValueError("A Cicada communicator is required.") # pragma: no cover

        if seed is None:
            seed = numpy.random.default_rng(seed=None).integers(low=0, high=2**63-1, endpoint=True)
        else:
            if seed_offset is None:
                seed_offset = communicator.rank
            seed += seed_offset

        self._prng = numpy.random.default_rng(seed=seed)
        if threshold < 2:
            raise ValueError('threshold is too small. Privacy is not tenable with threshold < 2.')
        self.d=threshold-1
        self.threshold = threshold
        if communicator.world_size < self.d+1:
            raise ValueError('threshold incompatible with worldsize, recovery impossible. Increase worldsize or decrease threshold.')
        #if communicator.world_size < self.d+1:
        #    raise ValueError('d incompatible with worldsize, even revealing secrets will not be feasible.')
        self._communicator = communicator
        self._encoder = cicada.encoder.FixedFieldEncoder(modulus=modulus, precision=precision)
        if indices is None:
            self.indices = [x+1 for x in communicator.ranks]
        else:
            self.indices = indices
        self.revealing_coef = self._lagrange_coef()


    def _assert_binary_compatible(self, lhs, rhs, lhslabel, rhslabel):
        self._assert_unary_compatible(lhs, lhslabel)
        self._assert_unary_compatible(rhs, rhslabel)
        if lhs.storage.shape != rhs.storage.shape:
            raise ValueError(f"{lhslabel} and {rhslabel} must be the same shape, got {lhs.storage.shape} and {rhs.storage.shape} instead.")

    def _assert_unary_compatible(self, share, label):
        if not isinstance(share, ShamirArrayShare):
            raise ValueError(f"{label} must be an instance of ShamirArrayShare, got {type(share)} instead.")

    def _lagrange_coef(self, src=None):
        # Given a set of indices, it returns an array containing the lagrange coefficients
        # with respect to each index given, keyed by those indices
        from math import prod
        if src is None:
            src = self.indices
        ls = len(src)
        coefs=numpy.zeros(ls, dtype=self.encoder.dtype)
        for i in range(ls):
            coefs[i]=prod([-src[j]*pow(src[i]-src[j], self.encoder.modulus-2, self.encoder.modulus) for j in range(ls) if src[j] != src[i]])%self.encoder.modulus
        return coefs 

    @property
    def communicator(self):
        """Return the :class:`~cicada.communicator.interface.Communicator` used by this protocol."""
        return self._communicator


    @property
    def encoder(self):
        """Return the :class:`cicada.encoder.fixedfield.FixedFieldEncoder` used by this protocol."""
        return self._encoder


    def add(self, lhs, rhs):
        """Return the elementwise sum of two secret shared arrays.

        The result is the secret shared elementwise sum of the operands.  If
        revealed, the result will need to be decoded to obtain the actual sum.

        Note
        ----
        This is a collective operation that *must* be called
        by all players that are members of :attr:`communicator`.

        Parameters
        ----------
        lhs: :class:`ShamirArrayShare`, required
            Secret shared value to be added.
        rhs: :class:`ShamirArrayShare`, required
            Secret shared value to be added.

        Returns
        -------
        value: :class:`ShamirArrayShare`
            Secret-shared sum of `lhs` and `rhs`.
        """
        self._assert_binary_compatible(lhs, rhs, "lhs", "rhs")
        return ShamirArrayShare(self.encoder.add(lhs.storage, rhs.storage))


    def additive_inverse(self, operand):
        """Return an elementwise additive inverse of a shared array 
        in the context of the underlying finite field. Explicitly, this 
        function returns a same shape array which, when added 
        elementwise with operand, will return a same shape array comprised
        entirely of zeros (the additive identity).

        Note
        ----
        This is a collective operation that *must* be called
        by all players that are members of :attr:`communicator`.
        This function does not take into account any field-external symantics.

        Parameters
        ----------
        operand: :class:`ShamirArrayShare`, required
            Secret shared array to be additively inverted.

        Returns
        -------
        value: :class:`ShamirArrayShare`
            The secret additive inverse of operand on an elementwise basis.
        """
        self._assert_unary_compatible(operand, "operand")

        return self.public_private_subtract(numpy.full(operand.storage.shape, self.encoder.modulus, dtype=self.encoder.dtype), operand)


    def bit_compose(self, operand):
        """given an operand in a bitwise decomposed representation, compose it into shares of its field element representation.

        Note
        ----
        The operand *must* be encoded with FixedFieldEncoder.  The result will
        have one more dimension than the operand, containing the returned bits
        in big-endian order.

        Parameters
        ----------
        operand: :class:`ShamirArrayShare`, required
            Shared secret to be truncated.

        Returns
        -------
        array: :class:`ShamirArrayShare`
            Share of the bit decomposed secret.
        """
        if not isinstance(operand, ShamirArrayShare):
            raise ValueError(f"Expected operand to be an instance of ShamirArrayShare, got {type(operand)} instead.") # pragma: no cover
        outer_shape = operand.storage.shape[:-1]
        last_dimension = operand.storage.shape[-1]
        idx = numpy.ndindex(outer_shape)
        composed = []
        shift = numpy.power(2, numpy.arange(last_dimension, dtype=self.encoder.dtype)[::-1])
        for x in idx:
            shifted = self.encoder.untruncated_multiply(operand.storage[x], shift)
            val_share = numpy.sum(shifted) % self.encoder.modulus
            composed.append(val_share)
        return ShamirArrayShare(numpy.array([x for x in composed], dtype=self.encoder.dtype).reshape(outer_shape))

    def private_public_subtract(self, lhs, rhs):
        """Return the elementwise difference between public and secret shared arrays.

        All players *must* supply the same value of `lhs` when calling this
        method.  The result will be the secret shared elementwise difference
        between the public (known to all players) `lhs` array and the private
        (secret shared) `rhs` array.  If revealed, the result will need to be
        decoded to obtain the actual difference.

        Note
        ----
        This is a collective operation that *must* be called
        by all players that are members of :attr:`communicator`.

        Parameters
        ----------
        lhs: :class:`ShamirArrayShare`, required
            Secret shared value from which rhs should be subtracted.
        rhs: :class:`numpy.ndarray`, required
            Public value, which must have been encoded with this protocol's
            :attr:`encoder`.

        Returns
        -------
        value: :class:`ShamirArrayShare`
            The secret shared difference `lhs` - `rhs`.
        """
        self._assert_unary_compatible(lhs, "lhs")

        return ShamirArrayShare(self.encoder.subtract(lhs.storage, rhs))


    def public_private_add(self, lhs, rhs):
        """Return the elementwise sum of public and secret shared arrays.

        All players *must* supply the same value of `lhs` when calling this
        method.  The result will be the secret shared elementwise sum of the
        public (known to all players) `lhs` array and the private (secret
        shared) `rhs` array.  If revealed, the result will need to be decoded
        to obtain the actual sum.

        Note
        ----
        This is a collective operation that *must* be called
        by all players that are members of :attr:`communicator`.

        Parameters
        ----------
        lhs: :class:`numpy.ndarray`, required
            Public value to be added, which must have been encoded
            with this protocol's :attr:`encoder`.
        rhs: :class:`ShamirArrayShare`, required
            Secret shared value to be added.

        Returns
        -------
        value: :class:`ShamirArrayShare`
            The secret shared sum of `lhs` and `rhs`.
        """
        self._assert_unary_compatible(rhs, "rhs")

        return ShamirArrayShare(self.encoder.add(lhs, rhs.storage))


    def public_private_subtract(self, lhs, rhs):
        """Return the elementwise difference between public and secret shared arrays.

        All players *must* supply the same value of `lhs` when calling this
        method.  The result will be the secret shared elementwise difference
        between the public (known to all players) `lhs` array and the private
        (secret shared) `rhs` array.  If revealed, the result will need to be
        decoded to obtain the actual difference.

        Note
        ----
        This is a collective operation that *must* be called
        by all players that are members of :attr:`communicator`.

        Parameters
        ----------
        lhs: :class:`numpy.ndarray`, required
            Public value, which must have been encoded with this protocol's
            :attr:`encoder`.
        rhs: :class:`ShamirArrayShare`, required
            Secret shared value to be subtracted.

        Returns
        -------
        value: :class:`ShamirArrayShare`
            The secret shared difference `lhs` - `rhs`.
        """
        self._assert_unary_compatible(rhs, "rhs")

        return ShamirArrayShare(self.encoder.subtract(lhs, rhs.storage))


    def reveal(self, share,*, dst=None):
        """Reveals a secret shared value to a subset of players.

        Note
        ----
        In most cases the revealed secret needs to be decoded with this
        protocol's :attr:`encoder` to reveal the actual value.

        This is a collective operation that *must* be called by all players
        that are members of :attr:`communicator`, whether they are receiving
        the revealed secret or not.

        Parameters
        ----------
        share: :class:`ShamirArrayShare`, required
            The local share of the secret to be revealed.
        dst: sequence of :class:`int`, optional
            List of players who will receive the revealed secret.  If :any:`None`
            (the default), the secret will be revealed to all players.

        Returns
        -------
        value: :class:`numpy.ndarray` or :any:`None`
            Encoded representation of the revealed secret, if this player is a
            member of `dst`, or :any:`None`.
        """

        if not isinstance(share, ShamirArrayShare):
            raise ValueError("share must be an instance of ShamirArrayShare.") # pragma: no cover

        # Identify who will be receiving shares.
        if dst is None:
            dst = self.communicator.ranks

        src = self.communicator.ranks
        n=len(src)
        if n == len(self.indices):
            revealing_coef = self.revealing_coef
        else:
            revealing_coef = None
        # Send data to the other players.
        secret = None
        for recipient in dst:
            received_shares = self.communicator.gatherv(src=src, value=share, dst=recipient)
            if received_shares: 
                received_storage = numpy.array([x.storage for x in received_shares], dtype=self.encoder.dtype)
                if self.communicator.rank == recipient:
                    if revealing_coef is None:
                        revealing_coef = self._lagrange_coef([self.indices[x] for x in src])
                    secret = []
                    for index in numpy.ndindex(received_storage[0].shape):
                        secret.append(sum([revealing_coef[i]*received_storage[i][index] for i in range(len(revealing_coef))]))
        if secret is None:
            return secret
        else:
            ret = numpy.array([x%self.encoder.modulus for x in secret], dtype=self.encoder.dtype).reshape(share.storage.shape)
            return ret


    def share(self, *, src, secret, shape):
        """Convert a private array to an shamir secret share.

        Note
        ----
        This is a collective operation that *must* be called
        by all players that are members of :attr:`communicator`.

        Parameters
        ----------
        src: :class:`int`, required
            The player providing the private array to be secret shared.
        secret: :class:`numpy.ndarray` or :any:`None`, required
            The secret array to be shared, which must be encoded with this
            object's :attr:`encoder`.  This value is ignored for all players
            except `src`.
        shape: :class:`tuple`, required
            The shape of the secret.  Note that the shape must be consistently
            specified by all players.

        Returns
        -------
        share: :class:`ShamirArrayShare`
            The local share of the secret shared array.
        """
        if not isinstance(shape, tuple):
            shape = (shape,)

        dst=self.communicator.ranks
        ldst=len(dst)

        shares = []
        sharesn = numpy.zeros(shape+(ldst,))
        if self.communicator.rank == src:
            if not isinstance(secret, numpy.ndarray):
                raise ValueError("secret must be an instance of numpy.ndarray.") # pragma: no cover
            if secret.dtype != self.encoder.dtype:
                raise ValueError("secret must be encoded by this protocol's encoder.") # pragma: no cover
            if secret.shape != shape:
                raise ValueError(f"secret.shape must match shape parameter.  Expected {secret.shape}, got {shape} instead.") # pragma: no cover
            coef = self.encoder.uniform(size=shape+(self.d,), generator=self._prng)
            for index in numpy.ndindex(shape):
                for x in self.indices:
                    shares.append(numpy.dot(numpy.power(numpy.full((self.d,), x),numpy.arange(1, self.d+1)), coef[index])+secret[index])
            sharesn = numpy.array(shares, dtype=self.encoder.dtype).reshape(shape+(ldst,)).T
        share = numpy.array(self.communicator.scatter(src=src, values=sharesn), dtype=self.encoder.dtype).T
        return ShamirArrayShare(share)


    def subtract(self, lhs, rhs):
        """Subtract a secret shared value from a secret shared value.

        Note
        ----
        This is a collective operation that *must* be called
        by all players that are members of :attr:`communicator`.

        Parameters
        ----------
        lhs: :class:`ShamirArrayShare`, required
            Shared value.
        rhs: :class:`ShamirArrayShare`, required
            Shared value to be subtracted.

        Returns
        -------
        value: :class:`ShamirArrayShare`
            The difference `lhs` - `rhs`.
        """
        self._assert_binary_compatible(lhs, rhs, "lhs", "rhs")
        return ShamirArrayShare(self.encoder.subtract(lhs.storage, rhs.storage))


    def uniform(self, *, shape=None, generator=None):
        """Return a ShamirSharedArray with the specified shape and filled with random field elements

        This method is secure against non-colluding semi-honest adversaries.  A
        subset of players (by default: all) generate and secret share vectors
        of pseudo-random field elements which are then added together
        elementwise.  Computation costs increase with the number of elements to
        generate and the number of players, while security increases with the
        number of players.

        Parameters
        ----------
        shape: :class:`tuple`, optional
            Shape of the array to populate. By default, 
            a shapeless array of one random element will be generated.
        src: sequence of :class:`int`, optional
            Players that will contribute to random array generation.  By default,
            all players contribute.
        generator: :class:`numpy.random.Generator`, optional
            A psuedorandom number generator for sampling.  By default,
            `numpy.random.default_rng()` will be used.

        Returns
        -------
        secret: :class:`ShamirArrayShare`
            A share of the random generated value.
        """

        if shape==None:
            shape=()
        if generator is None:
            generator = self._prng

        rand_ints = self.encoder.uniform(size=shape, generator=generator)
        share = ShamirArrayShare(numpy.zeros(shape, dtype=self.encoder.dtype))
        for i in self.communicator.ranks:
            share = self.add(self.share(src=i, secret=rand_ints, shape=rand_ints.shape), share)
        return share


class ShamirProtocol(ShamirBasicProtocol):
    """MPC protocol that uses a communicator to share and manipulate shamir-shared secrets.

    Note
    ----
    Creating the protocol is a collective operation that *must*
    be called by all players that are members of `communicator`.

    Parameters
    ----------
    communicator: :class:`cicada.communicator.interface.Communicator`, required
        The communicator that this protocol will use for communication.
    seed: :class:`int`, optional
        Seed used to initialize random number generators.  For privacy, this
        value should be different for each player.  By default, the seed will
        be chosen at random, and is guaranteed to be different even on forked
        processes.  If you specify `seed` yourself, the actual seed used will
        be the sum of this value and the value of `seed_offset`.
    seed_offset: :class:`int`, optional
        Value added to the value of `seed`.  This value defaults to the player's
        rank.
    modulus: :class:`int`, optional
        Field size for storing encoded values.  Defaults to the largest prime
        less than 2^64 (2**64-59).
    precision: :class:`int`, optional
        The number of bits for storing fractions in encoded values.  Defaults
        to 16.
    """
    def __init__(self, communicator,*, threshold, seed=None, seed_offset=None, modulus=18446744073709551557, precision=16,  indices=None):
        if not isinstance(communicator, Communicator):
            raise ValueError("A Cicada communicator is required.") # pragma: no cover

        if seed is None:
            seed = numpy.random.default_rng(seed=None).integers(low=0, high=2**63-1, endpoint=True)
        else:
            if seed_offset is None:
                seed_offset = communicator.rank
            seed += seed_offset

        self._prng = numpy.random.default_rng(seed=seed)
        if threshold < 2:
            raise ValueError('threshold is too small. Privacy is not tenable with threshold < 2.')
        self.d=threshold-1
        self.threshold = threshold
        if communicator.world_size < 2*self.d+1:
            raise ValueError('threshold incompatible with worldsize, multiplications will not be feasible. Multiplications with this threshold would require worldsize at least {2*self.d+1}. Increase worldsize or decrease threshold.')
        #if communicator.world_size < self.d+1:
        #    raise ValueError('d incompatible with worldsize, even revealing secrets will not be feasible.')
        self._communicator = communicator
        self._encoder = cicada.encoder.FixedFieldEncoder(modulus=modulus, precision=precision)
        if indices is None:
            self.indices = [x+1 for x in communicator.ranks]
        else:
            self.indices = indices
        self.revealing_coef = self._lagrange_coef()


    def _assert_binary_compatible(self, lhs, rhs, lhslabel, rhslabel):
        self._assert_unary_compatible(lhs, lhslabel)
        self._assert_unary_compatible(rhs, rhslabel)
        if lhs.storage.shape != rhs.storage.shape:
            raise ValueError(f"{lhslabel} and {rhslabel} must be the same shape, got {lhs.storage.shape} and {rhs.storage.shape} instead.")

    def _assert_unary_compatible(self, share, label):
        if not isinstance(share, ShamirArrayShare):
            raise ValueError(f"{label} must be an instance of ShamirArrayShare, got {type(share)} instead.")


    def absolute(self, operand):
        """Return the elementwise absolute value of a secret shared array.

        Note
        ----
        This is a collective operation that *must* be called
        by all players that are members of :attr:`communicator`.

        Parameters
        ----------
        operand: :class:`ShamirArrayShare`, required
            Secret shared value to which the absolute value function should be applied.

        Returns
        -------
        value: :class:`ShamirArrayShare`
            Secret-shared elementwise absolute value of `operand`.
        """
        self._assert_unary_compatible(operand, "operand")
        ltz = self.less_than_zero(operand)
        nltz = self.logical_not(ltz)
        addinvop = ShamirArrayShare(self.encoder.negative(operand.storage))
        ltz_parts = self.untruncated_multiply(ltz, addinvop)
        nltz_parts = self.untruncated_multiply(nltz, operand)
        return self.add(ltz_parts, nltz_parts)

    def bit_decompose(self, operand, num_bits=None):
        """Decompose operand into shares of its bitwise representation.

        Note
        ----
        The operand *must* be encoded with FixedFieldEncoder.  The result will
        have one more dimension than the operand, containing the returned bits
        in big-endian order.

        Parameters
        ----------
        operand: :class:`ShamirArrayShare`, required
            Shared secret to be truncated.

        Returns
        -------
        array: :class:`ShamirArrayShare`
            Share of the bit decomposed secret.
        """
        if not isinstance(operand, ShamirArrayShare):
            raise ValueError(f"Expected operand to be an instance of ShamirArrayShare, got {type(operand)} instead.") # pragma: no cover
        if num_bits is None:
            num_bits = self.encoder.fieldbits
        list_o_bits = []
        two_inv = numpy.array(pow(2, self.encoder.modulus-2, self.encoder.modulus), dtype=self.encoder.dtype)
        for element in operand.storage.flat: # Iterates in "C" order.
            loopop = ShamirArrayShare(numpy.array(element, dtype=self.encoder.dtype))
            elebits = []
            for i in range(num_bits):
                elebits.append(self._lsb(loopop))
                loopop = self.subtract(loopop, elebits[-1])
                loopop = ShamirArrayShare(self.encoder.untruncated_multiply(loopop.storage, two_inv))
            list_o_bits.append(elebits[::-1])
        return ShamirArrayShare(numpy.array([x.storage for y in list_o_bits for x in y]).reshape(operand.storage.shape+(num_bits,)))


    def equal(self, lhs, rhs):
        """Return an elementwise probabilistic equality comparison between secret shared arrays.

        The result is the secret shared elementwise comparison `lhs` == `rhs`.
        This is a collective operation that *must* be called
        by all players that are members of :attr:`communicator`.

        Parameters
        ----------
        lhs: :class:`ShamirArrayShare`, required
            Secret shared value to be compared.
        rhs: :class:`ShamirArrayShare`, required
            Secret shared value to be compared.

        Returns
        -------
        result: :class:`ShamirArrayShare`
            Secret-shared result of computing `lhs` == `rhs` elementwise.
        """
        self._assert_binary_compatible(lhs, rhs, "lhs", "rhs")
        diff = self.subtract(lhs, rhs)
        return self.logical_not(self.private_public_power_field(diff, self.encoder.modulus-1))


    def floor(self, operand):
        """Remove the `bits` least significant bits from each element in a secret shared array 
            then shift back left so that only the original integer part of 'operand' remains.


        Parameters
        ----------
        operand: :class:`ShamirArrayShare`, required
            Shared secret to which floor should be applied.

        Returns
        -------
        array: :class:`ShamirArrayShare`
            Share of the shared integer part of operand.
        """
        if not isinstance(operand, ShamirArrayShare):
            raise ValueError(f"Expected operand to be an instance of ShamirArrayShare, got {type(operand)} instead.") # pragma: no cover
        one = self.share(src=0, secret=numpy.full(operand.storage.shape, 2**self.encoder.precision, dtype=self.encoder.dtype), shape=operand.storage.shape)
        shift_op = numpy.full(operand.storage.shape, 2**self.encoder.precision, dtype=self.encoder.dtype)
        pl2 = numpy.full(operand.storage.shape, self.encoder.modulus-1, dtype=self.encoder.dtype)

        abs_op = self.absolute(operand)
        frac_bits = self.encoder.precision
        field_bits = self.encoder.fieldbits
        lsbs = self.bit_decompose(abs_op, self.encoder.precision)
        lsbs_composed = self.bit_compose(lsbs)
        lsbs_inv = self.additive_inverse(lsbs_composed)
        two_lsbs = ShamirArrayShare(self.encoder.untruncated_multiply(lsbs_composed.storage, numpy.full(lsbs_composed.storage.shape, 2, dtype=self.encoder.dtype)))
        ltz = self.less_than_zero(operand)  
        ones2sub = ShamirArrayShare(self.encoder.untruncated_multiply(self.private_public_power_field(lsbs_composed, pl2).storage, shift_op))
        sel_2_lsbs = self.untruncated_multiply(self.subtract(two_lsbs, ones2sub), ltz) 
        return self.add(self.add(sel_2_lsbs, lsbs_inv), operand) 


    def less(self, lhs, rhs):
        """Return an elementwise less-than comparison between secret shared arrays.

        The result is the secret shared elementwise comparison `lhs` < `rhs`.
        When revealed, the result will contain the values `0` or `1`, which do
        not need to be decoded.

        Note
        ----
        This is a collective operation that *must* be called
        by all players that are members of :attr:`communicator`.

        Parameters
        ----------
        lhs: :class:`ShamirArrayShare`, required
            Secret shared value to be compared.
        rhs: :class:`ShamirArrayShare`, required
            Secret shared value to be compared.

        Returns
        -------
        result: :class:`ShamirArrayShare`
            Secret-shared result of computing `lhs` < `rhs` elementwise.
        """
        self._assert_binary_compatible(lhs, rhs, "lhs", "rhs")
        one = numpy.full(lhs.storage.shape, 1, dtype=self.encoder.dtype)
        two = numpy.full(lhs.storage.shape, 2, dtype=self.encoder.dtype)
        twolhs = ShamirArrayShare(self.encoder.untruncated_multiply(two, lhs.storage))
        tworhs = ShamirArrayShare(self.encoder.untruncated_multiply(two, rhs.storage))
        diff = self.subtract(lhs, rhs)
        twodiff = ShamirArrayShare(self.encoder.untruncated_multiply(two, diff.storage))
        w = self.public_private_subtract(one, self._lsb(operand=twolhs))
        x = self.public_private_subtract(one, self._lsb(operand=tworhs))
        y = self.public_private_subtract(one, self._lsb(operand=twodiff))
        wxorx = self.logical_xor(w,x)
        notwxorx = self.public_private_subtract(one, wxorx)
        xwxorx = self.untruncated_multiply(x, wxorx)
        noty = self.public_private_subtract(one, y)
        notwxorxnoty = self.untruncated_multiply(notwxorx, noty)
        return self.add(xwxorx, notwxorxnoty)


    def less_than_zero(self, operand):
        """Return an elementwise less-than comparison between operand elements and zero.

        The result is the secret shared elementwise comparison `operand` < `0`.
        When revealed, the result will contain the values `0` or `1`, which do
        not need to be decoded.

        Note
        ----
        This is a collective operation that *must* be called
        by all players that are members of :attr:`communicator`.

        Parameters
        ----------
        operand: :class:`ShamirArrayShare`, required
            Secret shared value to be compared.

        Returns
        -------
        result: :class:`ShamirArrayShare`
            Secret-shared result of computing `operand` < `0` elementwise.
        """
        self._assert_unary_compatible(operand, "operand")
        two = numpy.array(2, dtype=self.encoder.dtype)
        twoop = ShamirArrayShare(self.encoder.untruncated_multiply(two, operand.storage))
        return self._lsb(operand=twoop)


    def logical_and(self, lhs, rhs):
        """Return an elementwise logical AND of two secret shared arrays.

        The operands *must* contain the *field* values `0` or `1`.  The result
        will be the secret shared elementwise logical AND of `lhs` and `rhs`.
        When revealed, the result will contain the values `0` or `1`, which do
        not need to be decoded.

        Note
        ----
        This is a collective operation that *must* be called
        by all players that are members of :attr:`communicator`.

        Parameters
        ----------
        lhs: :class:`ShamirArrayShare`, required
            Secret shared array to be AND'ed.
        rhs: :class:`ShamirArrayShare`, required
            Secret shared array to be AND'ed.

        Returns
        -------
        value: :class:`ShamirArrayShare`
            The secret elementwise logical AND of `lhs` and `rhs`.
        """
        self._assert_binary_compatible(lhs, rhs, "lhs", "rhs")

        product = self.untruncated_multiply(lhs, rhs)
        return product


    def logical_not(self, operand):
        """Return an elementwise logical NOT of two secret shared array.

        The operand *must* contain the *field* values `0` or `1`.  The result
        will be the secret shared elementwise logical negation of `operand`.
        When revealed, the result will contain the values `0` or `1`, which do
        not need to be decoded.

        Note
        ----
        This is a collective operation that *must* be called
        by all players that are members of :attr:`communicator`.

        Parameters
        ----------
        operand: :class:`ShamirArrayShare`, required
            Secret shared array to be negated.

        Returns
        -------
        value: :class:`ShamirArrayShare`
            The secret elementwise logical NOT of `operand`.
        """
        self._assert_unary_compatible(operand, "operand")

        ones = numpy.full(operand.storage.shape, 1, dtype=self.encoder.dtype)
        return self.public_private_subtract(lhs=ones, rhs=operand)


    def logical_or(self, lhs, rhs):
        """Return an elementwise logical OR of two secret shared arrays.

        The operands *must* contain the *field* values `0` or `1`.  The result
        will be the secret shared elementwise logical OR of `lhs` and `rhs`.
        When revealed, the result will contain the values `0` or `1`, which do
        not need to be decoded.

        Note
        ----
        This is a collective operation that *must* be called
        by all players that are members of :attr:`communicator`.

        Parameters
        ----------
        lhs: :class:`ShamirArrayShare`, required
            Secret shared array to be OR'd.
        rhs: :class:`ShamirArrayShare`, required
            Secret shared array to be OR'd.

        Returns
        -------
        value: :class:`ShamirArrayShare`
            The secret elementwise logical OR of `lhs` and `rhs`.
        """
        self._assert_binary_compatible(lhs, rhs, "lhs", "rhs")

        total = self.encoder.add(lhs.storage, rhs.storage)
        product = self.untruncated_multiply(lhs, rhs)
        return ShamirArrayShare(self.encoder.subtract(total, product.storage))


    def logical_xor(self, lhs, rhs):
        """Return an elementwise logical exclusive OR of two secret shared arrays.

        The operands *must* contain the *field* values `0` or `1`.  The result
        will be the secret shared elementwise logical XOR of `lhs` and `rhs`.
        When revealed, the result will contain the values `0` or `1`, which do
        not need to be decoded.

        Note
        ----
        This is a collective operation that *must* be called
        by all players that are members of :attr:`communicator`.

        Parameters
        ----------
        lhs: :class:`ShamirArrayShare`, required
            Secret shared array to be exclusive OR'd.
        rhs: :class:`ShamirArrayShare`, required
            Secret shared array to be exclusive OR'd.

        Returns
        -------
        value: :class:`ShamirArrayShare`
            The secret elementwise logical exclusive OR of `lhs` and `rhs`.
        """
        self._assert_binary_compatible(lhs, rhs, "lhs", "rhs")

        total = self.encoder.add(lhs.storage, rhs.storage)
        product = self.untruncated_multiply(lhs, rhs)
        twice_product = self.encoder.untruncated_multiply(numpy.array(2, dtype=self.encoder.dtype), product.storage)
        return ShamirArrayShare(self.encoder.subtract(total, twice_product))


    def _lsb(self, operand):
        """Return the elementwise least significant bit of a secret shared array.

        When revealed, the result will contain the values `0` or `1`, which do
        not need to be decoded.

        Note
        ----
        This is a collective operation that *must* be called
        by all players that are members of :attr:`communicator`.

        Parameters
        ----------
        operand: :class:`ShamirArrayShare`, required
            Secret shared array from which the least significant bits will be extracted

        Returns
        -------
        lsb: :class:`ShamirArrayShare`
            Additive shared array containing the elementwise least significant
            bits of `operand`.
        """
        one = numpy.array(1, dtype=self.encoder.dtype)
        lop = ShamirArrayShare(storage = operand.storage.flatten())
        tmpBW, tmp = self.random_bitwise_secret(bits=self.encoder._fieldbits, shape=lop.storage.shape)
        maskedlop = self.add(lhs=lop, rhs=tmp)
        c = self.reveal(maskedlop)
        # gotta sort the next function call first
        comp_result = self._public_bitwise_less_than(lhspub=c, rhs=tmpBW)
        c = (c % 2)
        c0xr0 = numpy.empty(c.shape, dtype = self.encoder.dtype) 
        for i, lc in enumerate(c):
            if lc:
                c0xr0[i] = self.public_private_subtract(lhs=one, rhs=ShamirArrayShare(storage=numpy.array(tmpBW.storage[i][-1], dtype=self.encoder.dtype))).storage
            else:
                c0xr0[i] = tmpBW.storage[i][-1]
        c0xr0 = ShamirArrayShare(storage = c0xr0)
        result = self.untruncated_multiply(lhs=comp_result, rhs=c0xr0)
        result = ShamirArrayShare(storage=self.encoder.untruncated_multiply(lhs=numpy.full(result.storage.shape, 2, dtype=object), rhs=result.storage))
        result = self.subtract(lhs=c0xr0, rhs=result)
        result = self.add(lhs=comp_result, rhs=result)
        return ShamirArrayShare(storage = result.storage.reshape(operand.storage.shape))

    def max(self, lhs, rhs):
        """Return the elementwise maximum of two secret shared arrays.

        The result is the secret shared elementwise maximum of the operands.
        If revealed, the result will need to be decoded to obtain the actual
        maximum values. Note: the field element ( if in the 'negative' range 
        of the field consider only its magnitude ) should be less than
        a quarter of the modulus for this method to be accurate in general.

        Note
        ----
        This is a collective operation that *must* be called
        by all players that are members of :attr:`communicator`.

        Parameters
        ----------
        lhs: :class:`ShamirArrayShare`, required
            Secret shared operand.
        rhs: :class:`ShamirArrayShare`, required
            Secret shared operand.

        Returns
        -------
        max: :class:`ShamirArrayShare`
            Secret-shared elementwise maximum of `lhs` and `rhs`.
        """
        self._assert_binary_compatible(lhs, rhs, "lhs", "rhs")
        max_share = self.add(self.add(lhs, rhs), self.absolute(self.subtract(lhs, rhs)))
        shift_right = numpy.full(lhs.storage.shape, pow(2, self.encoder.modulus-2, self.encoder.modulus), dtype=self.encoder.dtype)
        max_share.storage = self.encoder.untruncated_multiply(max_share.storage, shift_right)
        return max_share


    def min(self, lhs, rhs):
        """Return the elementwise minimum of two secret shared arrays.

        The result is the secret shared elementwise minimum of the operands.
        If revealed, the result will need to be decoded to obtain the actual
        minimum values. Note: the field element ( if in the 'negative' range 
        of the field consider only its magnitude ) should be less than
        a quarter of the modulus for this method to be accurate in general.

        Note
        ----
        This is a collective operation that *must* be called
        by all players that are members of :attr:`communicator`.

        Parameters
        ----------
        lhs: :class:`ShamirArrayShare`, required
            Secret shared operand.
        rhs: :class:`ShamirArrayShare`, required
            Secret shared operand.

        Returns
        -------
        min: :class:`ShamirArrayShare`
            Secret-shared elementwise minimum of `lhs` and `rhs`.
        """
        self._assert_binary_compatible(lhs, rhs, "lhs", "rhs")
        diff = self.subtract(lhs, rhs)
        abs_diff = self.absolute(diff)
        min_share = self.subtract(self.add(lhs, rhs), abs_diff)
        shift_right = numpy.full(lhs.storage.shape, pow(2, self.encoder.modulus-2, self.encoder.modulus), dtype=self.encoder.dtype)
        min_share.storage = self.encoder.untruncated_multiply(min_share.storage, shift_right)

        return min_share


    def multiplicative_inverse(self, operand):
        """Return an elementwise multiplicative inverse of a shared array 
        in the context of the underlying finite field. Explicitly, this 
        function returns a same shape array which, when multiplied 
        elementwise with operand, will return a same shape array comprised
        entirely of ones assuming operand is entirely non-trivial elements.

        Note
        ----
        This is a collective operation that *must* be called
        by all players that are members of :attr:`communicator`.
        This function does not take into account any field-external symantics.
        There is a potential for information leak here if operand contains any
        zero elements, that will be revealed. There is a small probability, 
        2^-operand.storage.size, for this approach to fail by zero being randomly
        generated by the parties as the mask.

        Parameters
        ----------
        operand: :class:`ShamirArrayShare`, required
            Secret shared array to be multiplicatively inverted.

        Returns
        -------
        value: :class:`ShamirArrayShare`
            The secret multiplicative inverse of operand on an elementwise basis.
        """
        self._assert_unary_compatible(operand, "operand")

        mask = self.uniform(shape=operand.storage.shape)
        masked_op = self.untruncated_multiply(mask, operand)
        revealed_masked_op = self.reveal(masked_op)
        nppowmod = numpy.vectorize(lambda a, b, c: pow(int(a), int(b), int(c)), otypes=[self.encoder.dtype])
        inv = numpy.array(nppowmod(revealed_masked_op, self.encoder.modulus-2, self.encoder.modulus), dtype=self.encoder.dtype)
        op_inv_share = self.encoder.untruncated_multiply(inv, mask.storage)
        return ShamirArrayShare(op_inv_share)


    def _private_public_mod(self, lhs, rhspub, *, enc=False):
        """Return an elementwise result of applying moduli contained in rhspub to lhs 
        in the context of the underlying finite field. Explicitly, this 
        function returns a same shape array which contains an approximation
        of the division in which lhs is the secret shared dividend and 
        rhspub is a publicly known divisor. 

        Note
        ----
        This is a collective operation that *must* be called
        by all players that are members of :attr:`communicator`.

        Parameters
        ----------
        lhs: :class:`ShamirArrayShare`, required
            Secret shared array to act as the dend.
        rhspub: :class:`numpy.ndarray`, required
            Public value to act as divisor, it is assumed to not
            be encoded, but we optionally provide an argument to 
            handle the case in which it is

        Returns
        -------
        value: :class:`ShamirArrayShare`
            The secret approximate result of lhs/rhspub on an elementwise basis.
        """
        self._assert_unary_compatible(lhs, "lhs")
        if not enc:
            divisor = self.encoder.encode(numpy.array(1/rhspub))
            rhs_enc = self.encoder.encode(rhspub)
        else:
            divisor = self.encoder.encode(numpy.array(1/self.encoder.decode(rhspub)))
            rhs_enc = rhspub
        quotient = ShamirArrayShare(self.encoder.untruncated_multiply(lhs.storage, divisor))
        quotient = self.truncate(quotient)
        quotient = self.floor(quotient)
        val2subtract = self.truncate(ShamirArrayShare(self.encoder.untruncated_multiply(rhs_enc, quotient.storage)))
        remainder = self.subtract(lhs, val2subtract) 
        return remainder 


    def private_public_power(self, lhs, rhspub):
        """Raise the array contained in lhs to the power rshpub on an elementwise basis

        Parameters
        ----------
        lhs: :class:`ShamirArrayShare`, required
            Shared secret to which floor should be applied.
        rhspub: :class:`int`, required
            a publically known integer and the power to which each element in lhs should be raised 

        Returns
        -------
        array: :class:`ShamirArrayShare`
            Share of the array elements from lhs all raised to the power rhspub.
        """
        if not isinstance(lhs, ShamirArrayShare):
            raise ValueError(f"Expected operand to be an instance of ShamirArrayShare, got {type(operand)} instead.") # pragma: no cover

        if isinstance(rhspub, int):
            rhspub = numpy.full(lhs.storage.shape, rhspub, dtype=self.encoder.dtype)
        ans=[]
        for lhse, rhse in numpy.nditer([lhs.storage, rhspub], flags=(["refs_ok"])):  
            rhsbits = [int(x) for x in bin(int(rhse))[2:]][::-1]
            tmp = ShamirArrayShare(lhse)
            it_ans = self.share(src = 0, secret=numpy.full(lhse.shape, self.encoder.encode(numpy.array(1)), dtype=self.encoder.dtype),shape=lhse.shape)
            limit = len(rhsbits)-1
            for i, bit in enumerate(rhsbits):
                if bit:
                    it_ans = self.untruncated_multiply(it_ans, tmp)
                    it_ans = self.truncate(it_ans)
                if i < limit:
                    tmp = self.untruncated_multiply(tmp,tmp)
                    tmp = self.truncate(tmp)
            ans.append(it_ans)
        return ShamirArrayShare(numpy.array([x.storage for x in ans], dtype=self.encoder.dtype).reshape(lhs.storage.shape)) 


    def private_public_power_field(self, lhs, rhspub):
        """Raise the array contained in lhs to the power rshpub on an elementwise basis

        Parameters
        ----------
        lhs: :class:`ShamirArrayShare`, required
            Shared secret to which floor should be applied.
        rhspub: :class:`int`, required 
            a publically known integer and the power to which each element in lhs should be raised 

        Returns
        -------
        array: :class:`ShamirArrayShare`
            Share of the array elements from lhs all raised to the power rhspub.
        """
        if not isinstance(lhs, ShamirArrayShare):
            raise ValueError(f"Expected operand to be an instance of ShamirArrayShare, got {type(operand)} instead.") # pragma: no cover
        if isinstance(rhspub, int):
            rhspub = numpy.full(lhs.storage.shape, rhspub, dtype=self.encoder.dtype)
        ans = []
        for lhse, rhse in numpy.nditer([lhs.storage, rhspub], flags=(["refs_ok"])):  
            rhsbits = [int(x) for x in bin(int(rhse))[2:]][::-1]
            tmp = ShamirArrayShare(lhse)
            it_ans = self.share(src = 0, secret=numpy.full(lhse.shape, numpy.array(1), dtype=self.encoder.dtype),shape=lhse.shape)
            limit = len(rhsbits)-1
            for i, bit in enumerate(rhsbits):
                if bit:
                    it_ans = self.untruncated_multiply(it_ans, tmp)
                if i < limit:
                    tmp = self.untruncated_multiply(tmp,tmp)
            ans.append(it_ans)
        return ShamirArrayShare(numpy.array([x.storage for x in ans], dtype=self.encoder.dtype).reshape(lhs.storage.shape)) 

    def _public_bitwise_less_than(self,*, lhspub, rhs):
        """Comparison Operator

        Parameters
        ----------
        lhs: :class:`ndarray`, required 
            a publically known numpy array of integers and one of the two objects to be compared 
        rhs: :class:`ShamirArrayShare`, required 
            bit decomposed shared secret(s) and the other of the two objects to be compared 
            the bitwidth of each value in rhs (deduced from its shape) is taken to be the 
            bitwidth of interest for the comparison if the values in lhspub require more bits 
            for their representation, the computation will be incorrect

        note: this method is private as it does not consider the semantic mapping of meaning 
        onto the field. The practical result of this is that every negative value will register as 
        greater than every positive value due to the encoding.


        Returns
        -------
        a shamir shared array containing the element wise result of the comparison: result[i] = 1 if lhspub[i] < rhs[i] and 0 otherwise
        """
        if lhspub.shape != rhs.storage.shape[:-1]:
            raise ValueError('rhs is not of the expected shape - it should be the same as lhs except the last dimension')
        bitwidth = rhs.storage.shape[-1]
        lhsbits = []
        for val in lhspub:
            tmplist = [int(x) for x in bin(val)[2:]]
            if len(tmplist) < bitwidth:
                tmplist = [0 for x in range(bitwidth-len(tmplist))] + tmplist
            lhsbits.append(tmplist)
        lhsbits = numpy.array(lhsbits, dtype=self.encoder.dtype)
        assert(lhsbits.shape == rhs.storage.shape)
        one = numpy.array(1, dtype=self.encoder.dtype)
        flatlhsbits = lhsbits.reshape((-1, lhsbits.shape[-1]))
        flatrhsbits = rhs.storage.reshape((-1, rhs.storage.shape[-1]))
        results=[]
        for j in range(len(flatlhsbits)):
            xord = []
            preord = []
            msbdiff=[]
            rhs_bit_at_msb_diff = []
            for i in range(bitwidth):
                rhsbit=ShamirArrayShare(storage=numpy.array(flatrhsbits[j,i], dtype=self.encoder.dtype))
                if flatlhsbits[j][i] == 1:
                    xord.append(self.public_private_subtract(lhs=one, rhs=rhsbit))
                else:
                    xord.append(rhsbit)
            preord = [xord[0]] 
            for i in range(1,bitwidth):
                preord.append(self.logical_or(lhs=preord[i-1], rhs=xord[i]))
            msbdiff = [preord[0]]
            for i in range(1,bitwidth):
                msbdiff.append(self.subtract(lhs=preord[i], rhs=preord[i-1]))
            for i in range(bitwidth):
                rhsbit=ShamirArrayShare(storage=numpy.array(flatrhsbits[j,i], dtype=self.encoder.dtype))
                rhs_bit_at_msb_diff.append(self.untruncated_multiply(rhsbit, msbdiff[i]))
            result = rhs_bit_at_msb_diff[0]
            for i in range(1,bitwidth):
                result = self.add(lhs=result, rhs=rhs_bit_at_msb_diff[i])
            results.append(result)
        return ShamirArrayShare(storage = numpy.array([x.storage for x in results], dtype=self.encoder.dtype).reshape(rhs.storage.shape[:-1]))

    def random_bitwise_secret(self, *, bits, src=None, generator=None, shape=None):
        """Return a vector of randomly generated bits.

        This method is secure against non-colluding semi-honest adversaries.  A
        subset of players (by default: all) generate and secret share vectors
        of pseudo-random bits which are then xored together elementwise.
        Communication and computation costs increase with the number of bits
        and the number of players, while security increases with the number of
        players.

        Parameters
        ----------
        bits: :class:`int`, required
            Number of bits to generate.
        src: sequence of :class:`int`, optional
            Players that will contribute to random bit generation.  By default,
            all players contribute.
        generator: :class:`numpy.random.Generator`, optional
            A psuedorandom number generator for sampling.  By default,
            `numpy.random.default_rng()` will be used.

        Returns
        -------
        bits: :class:`ShamirArrayShare`
            A share of the randomly-generated bits that make-up the secret.
        secret: :class:`ShamirArrayShare`
            A share of the value defined by `bits` (in big-endian order).
        """
        bits = int(bits)
        shape_was_none = False
        if bits < 1:
            raise ValueError(f"bits must be a positive integer, got {bits} instead.") # pragma: no cover

        if src is None:
            src = self.communicator.ranks
        if not src:
            raise ValueError(f"src must include at least one player, got {src} instead.") # pragma: no cover

        if generator is None:
            generator = numpy.random.default_rng()
        if shape is None:
            shape = ()
            shape_was_none = True
        bit_res = []
        share_res = []
        numzeros = numpy.zeros(shape)
        for loopop in numzeros.flat:
            # Each participating player generates a vector of random bits.
            if self.communicator.rank in src:
                local_bits = generator.choice(2, size=bits).astype(self.encoder.dtype)
            else:
                local_bits = None

            # Each participating player secret shares their bit vectors.
            player_bit_shares = []
            for rank in src:
                player_bit_shares.append(self.share(src=rank, secret=local_bits, shape=(bits,)))

            # Generate the final bit vector by xor-ing everything together elementwise.
            bit_share = player_bit_shares[0]
            for player_bit_share in player_bit_shares[1:]:
                bit_share = self.logical_xor(bit_share, player_bit_share)

            # Shift and combine the resulting bits in big-endian order to produce a random value.
            shift = numpy.power(2, numpy.arange(bits, dtype=self.encoder.dtype)[::-1])
            shifted = self.encoder.untruncated_multiply(shift, bit_share.storage)
            secret_share = ShamirArrayShare(numpy.array(numpy.sum(shifted), dtype=self.encoder.dtype))
            bit_res.append(bit_share)
            share_res.append(secret_share)
        if shape_was_none:
            bit_share = ShamirArrayShare(numpy.array([x.storage for x in bit_res], dtype=self.encoder.dtype).reshape(bits))
            secret_share = ShamirArrayShare(numpy.array([x.storage for x in share_res], dtype=self.encoder.dtype).reshape(shape))#, order="C"))
        else:
            bit_share = ShamirArrayShare(numpy.array([x.storage for x in bit_res], dtype=self.encoder.dtype).reshape(shape+(bits,)))#, order="C"))
            secret_share = ShamirArrayShare(numpy.array([x.storage for x in share_res], dtype=self.encoder.dtype).reshape(shape))#, order="C"))

        return bit_share, secret_share


    def relu(self, operand):
        """Return the elementwise ReLU of a secret shared array.

        Note
        ----
        This is a collective operation that *must* be called
        by all players that are members of :attr:`communicator`.

        Parameters
        ----------
        operand: :class:`ShamirArrayShare`, required
            Secret shared value to which the ReLU function should be applied.

        Returns
        -------
        value: :class:`ShamirArrayShare`
            Secret-shared elementwise ReLU of `operand`.
        """
        self._assert_unary_compatible(operand, "operand")
        ltz = self.less_than_zero(operand)
        nltz = self.logical_not(ltz)
        nltz_parts = self.untruncated_multiply(nltz, operand)
        return nltz_parts


    def truncate(self, operand, *, bits=None, src=None, generator=None):
        """Remove the `bits` least significant bits from each element in a secret shared array.

        Note
        ----
        The operand *must* be encoded with FixedFieldEncoder

        Parameters
        ----------
        operand: :class:`ShamirArrayShare`, required
            Shared secret to be truncated.
        bits: :class:`int`, optional
            Number of bits to truncate - defaults to the precision of the encoder.
        src: sequence of :class:`int`, optional
            Players who will participate in generating random bits as part of
            the truncation process.  More players increases security but
            decreases performance.  Defaults to all players.
        generator: :class:`numpy.random.Generator`, optional
            A psuedorandom number generator for sampling.  By default,
            `numpy.random.default_rng()` will be used.

        Returns
        -------
        array: :class:`ShamirArrayShare`
            Share of the truncated secret.
        """
        if not isinstance(operand, ShamirArrayShare):
            raise ValueError(f"Expected operand to be an instance of ShamirArrayShare, got {type(operand)} instead.") # pragma: no cover

        if bits is None:
            bits = self.encoder.precision

        fieldbits = self.encoder.fieldbits

        shift_left = numpy.full(operand.storage.shape, 2 ** bits, dtype=self.encoder.dtype)
        # Multiplicative inverse of shift_left.
        shift_right = numpy.full(operand.storage.shape, pow(2 ** bits, self.encoder.modulus-2, self.encoder.modulus), dtype=self.encoder.dtype)


        # Generate random bits that will mask the region to be truncated.
        _, truncation_mask = self.random_bitwise_secret(bits=bits, src=src, generator=generator, shape=operand.storage.shape)

        # Generate random bits that will mask everything outside the region to be truncated.
        _, remaining_mask = self.random_bitwise_secret(bits=fieldbits-bits, src=src, generator=generator, shape=operand.storage.shape)
        remaining_mask.storage = self.encoder.untruncated_multiply(remaining_mask.storage, shift_left)

        # Combine the two masks.
        mask = self.add(remaining_mask, truncation_mask)

        # Mask the array element.
        masked_element = self.add(mask, operand)

        # Reveal the element to all players (because it's masked, no player learns the underlying secret).
        masked_element = self.reveal(masked_element)

        # Retain just the bits within the region to be truncated, which need to be removed.
        masked_truncation_bits = numpy.array(masked_element % shift_left, dtype=self.encoder.dtype)

        # Remove the mask, leaving just the bits to be removed from the
        # truncation region.  Because the result of the subtraction is
        # secret shared, the secret still isn't revealed.
        truncation_bits = self.public_private_subtract(masked_truncation_bits, truncation_mask)

        # Remove the bits in the truncation region from the element.  The result can be safely truncated.
        result = self.subtract(operand, truncation_bits)

        # Truncate the element by shifting right to get rid of the (now cleared) bits in the truncation region.
        result = self.encoder.untruncated_multiply(result.storage, shift_right)

        return ShamirArrayShare(result)



    def untruncated_multiply(self, lhs, rhs):
        """Element-wise multiplication of two shared arrays.

        The operands are assumed to be vectors or matrices and their product is
        computed on an elementwise basis. Multiplication with shared secrets and
        public scalars is implemented in the encoder.

        Note
        ----
        This is a collective operation that *must* be called
        by all players that are members of :attr:`communicator`.

        Parameters
        ----------
        lhs: :class:`ShamirArrayShare`, required
            secret value to be multiplied.
        rhs: :class:`ShamirArrayShare`, required
            secret value to be multiplied.

        Returns
        -------
        value: :class:`ShamirArrayShare`
            The secret elementwise product of `lhs` and `rhs`.
        """
        self._assert_binary_compatible(lhs, rhs, "lhs", "rhs")

        world_size = self.communicator.world_size
        count = ceil((world_size - 1) / 2)
        x = lhs.storage
        y = rhs.storage
        xy=numpy.array((x*y)%self.encoder.modulus, dtype=self.encoder.dtype)
        lc = self._lagrange_coef()
        dubdeg = numpy.zeros((len(lc),)+lhs.storage.shape, dtype=self.encoder.dtype) 
        for i, src in enumerate(self.communicator.ranks):
            dubdeg[i]=self.share(src=src, secret=xy, shape=xy.shape).storage #transpose
        sharray = numpy.zeros(lhs.storage.shape, dtype=self.encoder.dtype)
        for i in range(len(self.communicator.ranks)):
            sharray = numpy.array((sharray + dubdeg[i]*lc[i]) % self.encoder.modulus, dtype=self.encoder.dtype)
        return ShamirArrayShare(sharray)


    def untruncated_private_divide(self, lhs, rhs):
        """Element-wise division of private values. Note: this may have a chance to leak info is the secret contained in rhs is 
        close to or bigger than 2^precision

        Note
        ----
        This is a collective operation that *must* be called
        by all players that are members of :attr:`communicator`.

        Parameters
        ----------
        lhs: :class:`ShamirArrayShare`, required
            Secret shared array dividend.
        rhs: :class:`numpy.ndarray`, required
            Public array divisor, which must *not* be encoded.

        Returns
        -------
        value: :class:`ShamirArrayShare`
            The secret element-wise result of lhs / rhs.
        """
        self._assert_binary_compatible(lhs, rhs, "lhs", "rhs")
        _, rmask = self.random_bitwise_secret(bits=self.encoder.precision, shape=rhs.storage.shape)
        rhsmasked = self.untruncated_multiply(rmask, rhs)
        rhsmasked = self.truncate(rhsmasked)
        revealrhsmasked = self.encoder.decode(self.reveal(rhsmasked))
        maskquotient = self.untruncated_private_public_divide(self.truncate(self.untruncated_multiply(lhs, rmask)), revealrhsmasked)
        return maskquotient 


    def untruncated_private_public_divide(self, lhs, rhs):
        """Element-wise division of private and public values.

        Note
        ----
        This is a collective operation that *must* be called
        by all players that are members of :attr:`communicator`.

        Parameters
        ----------
        lhs: :class:`ShamirArrayShare`, required
            Secret shared array dividend.
        rhs: :class:`numpy.ndarray`, required
            Public array divisor, which must *not* be encoded.

        Returns
        -------
        value: :class:`ShamirArrayShare`
            The secret element-wise result of lhs / rhs.
        """
        self._assert_unary_compatible(lhs, "lhs")
        divisor = self.encoder.encode(numpy.array(1 / rhs))
        quotient = ShamirArrayShare(self.encoder.untruncated_multiply(lhs.storage, divisor))
        return quotient

    def zigmoid(self, operand):
        r"""Compute the elementwise zigmoid function of a secret value.

        Zigmoid is an approximation of sigmoid which is more angular and is a piecewise function much
        more efficient to compute in an MPC context:

        .. math::

            zigmoid(x) = \left\{
            \begin{array}\\
                0 & if\ x<-0.5 \\
                x+0.5 & if\ -0.5\leq x \leq 0.5 \\
                1 & if x>0.5
            \end{array}
            \right.

        Note
        ----
        This is a collective operation that *must* be called
        by all players that are members of :attr:`communicator`.

        Parameters
        ----------
        operand: :class:`ShamirArrayShare`, required
            Secret shared value to which the zigmoid function should be applied.

        Returns
        -------
        value: :class:`ShamirArrayShare`
            Secret-shared elementwise zigmoid of `operand`.
        """
        ones=self.encoder.encode(numpy.full(operand.storage.shape, 1))
        half = self.encoder.encode(numpy.full(operand.storage.shape, .5))
        
        secret_plushalf = self.public_private_add(half, operand)
        secret_minushalf = self.private_public_subtract(operand, half)
        ltzsmh = self.less_than_zero(secret_minushalf)
        nltzsmh = self.logical_not(ltzsmh)
        ltzsph = self.less_than_zero(secret_plushalf)
        middlins = self.subtract(ltzsmh, ltzsph)
        extracted_middlins = self.untruncated_multiply(middlins, operand)
        extracted_halfs = ShamirArrayShare(self.encoder.untruncated_multiply(middlins.storage, half))
        extracted_middlins = self.add(extracted_middlins, extracted_halfs)
        ones_part = ShamirArrayShare(self.encoder.untruncated_multiply(nltzsmh.storage, ones))
        return self.add(ones_part, extracted_middlins)
