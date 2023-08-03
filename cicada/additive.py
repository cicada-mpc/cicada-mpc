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

"""Functionality for creating, manipulating, and revealing additive-shared secrets."""

import logging
import math
import warnings

import numpy

from cicada.communicator.interface import Communicator, Tag
from cicada.encoding import FixedPoint, Identity
import cicada.arithmetic


class AdditiveArrayShare(object):
    """Stores the local share of an additive-shared secret array.

    Instances of :class:`AdditiveArrayShare` should only be created
    using instances of :class:`AdditiveProtocolSuite`.

    Parameters
    ----------
    storage: :class:`numpy.ndarray`, required
        Local additive share of a secret array.
    """
    def __init__(self, storage):
        if not isinstance(storage, numpy.ndarray):
            raise ValueError(f"Expected numpy.ndarray, got {type(storage)}.")
        self.storage = storage


    def __repr__(self):
        return f"cicada.additive.AdditiveArrayShare(storage={self._storage})" # pragma: no cover


    def __getitem__(self, index):
        return AdditiveArrayShare(numpy.array(self._storage[index], dtype=self._storage.dtype))


    @property
    def storage(self):
        """Local share of an additive-shared secret array.

        Returns
        -------
        storage: :class:`object`
            Private storage for the local share of an additively-shared secret
            array.  Access is provided only for serialization and communication
            - callers must use :class:`AdditiveProtocolSuite` to manipulate
            secret shares.
        """
        return self._storage


    @storage.setter
    def storage(self, storage):
        self._storage = numpy.array(storage, dtype=object)


class AdditiveProtocolSuite(object):
    """Protocol suite implementing computation with additive-shared secrets.

    Multiplication is implemented using a generalization of "Protocols for
    secure remote database access with approximate matching" by Du and Atallah,
    which provides semi-honest security and does not require Beaver triples or
    other offline computation.

    Comparisons are based on "Multiparty computation for interval, equality,
    and comparison without bit-decomposition protocol" by Nishide and Ohta, and
    inherit the semi-honest security model from multiplication.

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
        less than :math:`2^{64}`.
    encoding: :class:`object`, optional
        Encoding to use by default for operations that require encoding/decoding.
        Defaults to an instance of :class:`FixedPoint` with 16 bits of floating-point
        precision.
    """
    def __init__(self, communicator, seed=None, seed_offset=None, order=None, encoding=None):
        if not isinstance(communicator, Communicator):
            raise ValueError("A Cicada communicator is required.") # pragma: no cover

        # Setup a pseudo-random sharing of zero, using code drawn from
        # https://github.com/facebookresearch/CrypTen/blob/master/crypten/__init__.py

        # Generate random seeds for Generators
        # NOTE: Chosen seed can be any number, but we choose a random 64-bit
        # integer here so other players cannot guess its value.

        # We typically get here from a forked process, which causes all players
        # to have the same RNG state. Reset the seed to make sure RNG streams
        # are different for all the players. We use numpy's random generator
        # here since initializing it without a seed will produce different
        # seeds even from forked processes.
        if seed is None:
            seed = numpy.random.default_rng(seed=None).integers(low=0, high=2**63-1, endpoint=True)
        else:
            if seed_offset is None:
                seed_offset = communicator.rank
            seed += seed_offset

        if encoding is None:
            encoding = FixedPoint()

        # Send random seed to next party, receive random seed from prev party
        if communicator.world_size >= 2:  # Otherwise sending seeds will segfault.
            next_rank = (communicator.rank + 1) % communicator.world_size
            prev_rank = (communicator.rank - 1) % communicator.world_size

            request = communicator.isend(value=seed, dst=next_rank, tag=Tag.PRSZ)
            result = communicator.irecv(src=prev_rank, tag=Tag.PRSZ)

            request.wait()
            result.wait()

            prev_seed = result.value
        else:
            prev_seed = seed

        # Setup random number generators
        self._g0 = numpy.random.default_rng(seed=seed)
        self._g1 = numpy.random.default_rng(seed=prev_seed)

        self._communicator = communicator
        self._field = cicada.arithmetic.Field(order=order)
        self._encoding = encoding


    def _assert_binary_compatible(self, lhs, rhs, lhslabel, rhslabel):
        self._assert_unary_compatible(lhs, lhslabel)
        self._assert_unary_compatible(rhs, rhslabel)
        if lhs.storage.shape != rhs.storage.shape:
            raise ValueError(f"{lhslabel} and {rhslabel} must be the same shape, got {lhs.storage.shape} and {rhs.storage.shape} instead.") # pragma: no cover


    def _assert_unary_compatible(self, share, label):
        if not isinstance(share, AdditiveArrayShare):
            raise ValueError(f"{label} must be an instance of AdditiveArrayShare, got {type(share)} instead.") # pragma: no cover


    def _require_encoding(self, encoding):
        if encoding is None:
            encoding = self._encoding
        return encoding


    def absolute(self, operand):
        """Return the elementwise absolute value of a secret shared array.

        Note
        ----
        This is a collective operation that *must* be called
        by all players that are members of :attr:`communicator`.

        Parameters
        ----------
        operand: :class:`AdditiveArrayShare`, required
            Secret shared value to which the absolute value function should be applied.

        Returns
        -------
        value: :class:`AdditiveArrayShare`
            Secret-shared elementwise absolute value of `operand`.
        """
        self._assert_unary_compatible(operand, "operand")
        ltz = self.less_zero(operand)
        nltz = self.logical_not(ltz)
        addinvop = self.negative(operand)
        ltz_parts = self.field_multiply(ltz, addinvop)
        nltz_parts = self.field_multiply(nltz, operand)
        return self.field_add(ltz_parts, nltz_parts)


    def add(self, lhs, rhs, *, encoding=None):
        """Return the elementwise sum of two secret shared arrays.

        The result is the secret shared elementwise sum of the operands.

        Note
        ----
        This is a collective operation that *must* be called
        by all players that are members of :attr:`communicator`.

        Parameters
        ----------
        lhs: :class:`AdditiveArrayShare`, required
            Secret shared value to be added.
        rhs: :class:`AdditiveArrayShare`, required
            Secret shared value to be added.

        Returns
        -------
        value: :class:`AdditiveArrayShare`
            Secret-shared sum of `lhs` and `rhs`.
        """
        encoding = self._require_encoding(encoding)

        # Private-private addition.
        if isinstance(lhs, AdditiveArrayShare) and isinstance(rhs, AdditiveArrayShare):
            return self.field_add(lhs, rhs)

        # Private-public addition.
        if isinstance(lhs, AdditiveArrayShare) and isinstance(rhs, numpy.ndarray):
            return self.field_add(lhs, encoding.encode(rhs, self.field))

        # Public-private addition.
        if isinstance(lhs, numpy.ndarray) and isinstance(rhs, AdditiveArrayShare):
            return self.field_add(encoding.encode(lhs, self.field), rhs)

        raise NotImplementedError(f"Privacy-preserving addition not implemented for the given types: {type(lhs)} and {type(rhs)}.")


    def bit_compose(self, operand):
        """given an operand in a bitwise decomposed representation, compose it into shares of its field element representation.

        Note
        ----
        The operand *must* be encoded with FixedFieldEncoder.  The result will
        have one more dimension than the operand, containing the returned bits
        in big-endian order.

        Parameters
        ----------
        operand: :class:`AdditiveArrayShare`, required
            Shared secret to be truncated.

        Returns
        -------
        array: :class:`AdditiveArrayShare`
            Share of the bit decomposed secret.
        """
        self._assert_unary_compatible(operand, "operand")

        result = numpy.empty(operand.storage.shape[:-1], dtype=object)
        shift = numpy.power(2, numpy.arange(operand.storage.shape[-1], dtype=self.field.dtype)[::-1])
        shifted = self.field.multiply(operand.storage, shift)
        result = numpy.sum(shifted, axis=-1, out=result)
        result %= self.field.order
        return AdditiveArrayShare(result)


    def bit_decompose(self, operand, *, bits=None):
        """Decompose operand into shares of its bitwise representation.

        Note
        ----
        The operand *must* be encoded with FixedFieldEncoder.  The result will
        have one more dimension than the operand, containing the returned bits
        in big-endian order.

        Parameters
        ----------
        operand: :class:`AdditiveArrayShare`, required
            Shared secret to be truncated.

        Returns
        -------
        array: :class:`AdditiveArrayShare`
            Share of the bit decomposed secret.
        """
        self._assert_unary_compatible(operand, "operand")

        if bits is None:
            bits = self.field.fieldbits
        list_o_bits = []
        two_inv = numpy.array(pow(2, self.field.order-2, self.field.order), dtype=self.field.dtype)
        for element in operand.storage.flat: # Iterates in "C" order.
            loopop = AdditiveArrayShare(numpy.array(element, dtype=self.field.dtype))
            elebits = []
            for i in range(bits):
                elebits.append(self._lsb(loopop))
                loopop = self.field_subtract(loopop, elebits[-1])
                loopop = AdditiveArrayShare(self.field.multiply(loopop.storage, two_inv))
            list_o_bits.append(elebits[::-1])
        return AdditiveArrayShare(numpy.array([x.storage for y in list_o_bits for x in y]).reshape(operand.storage.shape+(bits,)))


    @property
    def communicator(self):
        """Return the :class:`~cicada.communicator.interface.Communicator` used by this protocol."""
        return self._communicator


    def divide(self, lhs, rhs, *, encoding=None):
        """Elementwise division of two secret shared arrays.

        This is a collective operation that *must* be called
        by all players that are members of :attr:`communicator`.

        Parameters
        ----------
        lhs: :class:`AdditiveArrayShare`, required
            Secret shared array.
        rhs: :class:`AdditiveArrayShare`, required
            Secret shared array.

        Returns
        -------
        result: :class:`AdditiveArrayShare`
            Secret-shared elementwise division of `lhs` and `rhs`.
        """
        encoding = self._require_encoding(encoding)

        # Private-private division.
        if isinstance(lhs, AdditiveArrayShare) and isinstance(rhs, AdditiveArrayShare):
            pass

        # Private-public division.
        if isinstance(lhs, AdditiveArrayShare) and isinstance(rhs, numpy.ndarray):
            divisor = encoding.encode(numpy.array(1 / rhs), self.field)
            result = self.field_multiply(lhs, divisor)
            result = self.right_shift(result, bits=encoding.precision)
            return result

        # Public-private division.
        if isinstance(lhs, numpy.ndarray) and isinstance(rhs, AdditiveArrayShare):
            pass

        raise NotImplementedError(f"Privacy-preserving division not implemented for the given types: {type(lhs)} and {type(rhs)}.")


    def dot(self, lhs, rhs, *, encoding=None):
        """Return the dot product of two secret shared vectors.

        This is a collective operation that *must* be called
        by all players that are members of :attr:`communicator`.

        Parameters
        ----------
        lhs: :class:`AdditiveArrayShare`, required
            Secret shared vector.
        rhs: :class:`AdditiveArrayShare`, required
            Secret shared vector.

        Returns
        -------
        result: :class:`AdditiveArrayShare`
            Secret-shared dot product of `lhs` and `rhs`.
        """
        self._assert_binary_compatible(lhs, rhs, "lhs", "rhs")
        encoding = self._require_encoding(encoding)

        result = self.field_dot(lhs, rhs)
        result = self.right_shift(result, bits=encoding.precision)
        return result


    @property
    def encoding(self):
        return self._encoding


    def equal(self, lhs, rhs):
        """Return an elementwise probabilistic equality comparison between secret shared arrays.

        The result is the secret shared elementwise comparison `lhs` == `rhs`.
        This is a collective operation that *must* be called
        by all players that are members of :attr:`communicator`.

        Parameters
        ----------
        lhs: :class:`AdditiveArrayShare`, required
            Secret shared value to be compared.
        rhs: :class:`AdditiveArrayShare`, required
            Secret shared value to be compared.

        Returns
        -------
        result: :class:`AdditiveArrayShare`
            Secret-shared result of computing `lhs` == `rhs` elementwise.
        """
        self._assert_binary_compatible(lhs, rhs, "lhs", "rhs")
        diff = self.field_subtract(lhs, rhs)
        return self.logical_not(self.field_power(diff, self.field.order - 1))


    @property
    def field(self):
        return self._field


    def field_add(self, lhs, rhs):
        """Return the elementwise sum of two secret shared arrays.

        The result is the secret shared elementwise sum of the operands.

        Note
        ----
        This is a collective operation that *must* be called
        by all players that are members of :attr:`communicator`.

        Parameters
        ----------
        lhs: :class:`AdditiveArrayShare`, required
            Secret shared value to be added.
        rhs: :class:`AdditiveArrayShare`, required
            Secret shared value to be added.

        Returns
        -------
        value: :class:`AdditiveArrayShare`
            Secret-shared sum of `lhs` and `rhs`.
        """
        # Private-private addition.
        if isinstance(lhs, AdditiveArrayShare) and isinstance(rhs, AdditiveArrayShare):
            return AdditiveArrayShare(self.field.add(lhs.storage, rhs.storage))

        # Private-public addition.
        if isinstance(lhs, AdditiveArrayShare) and isinstance(rhs, numpy.ndarray):
            if self.communicator.rank == 0:
                return AdditiveArrayShare(self.field.add(lhs.storage, rhs))
            return lhs

        # Public-private addition.
        if isinstance(lhs, numpy.ndarray) and isinstance(rhs, AdditiveArrayShare):
            if self.communicator.rank == 0:
                return AdditiveArrayShare(self.field.add(lhs, rhs.storage))
            return rhs

        raise NotImplementedError(f"Privacy-preserving addition not implemented for the given types: {type(lhs)} and {type(rhs)}.")


    def field_divide(self, lhs, rhs):
        """Return the elementwise quotient of two secret shared arrays.

        The result is the secret shared elementwise sum of the operands.

        Note
        ----
        This is a collective operation that *must* be called
        by all players that are members of :attr:`communicator`.

        Parameters
        ----------
        lhs: :class:`AdditiveArrayShare`, required
            Secret shared value to be added.
        rhs: :class:`AdditiveArrayShare`, required
            Secret shared value to be added.

        Returns
        -------
        value: :class:`AdditiveArrayShare`
            Secret-shared sum of `lhs` and `rhs`.
        """
        # Private-private division.
        if isinstance(lhs, AdditiveArrayShare) and isinstance(rhs, AdditiveArrayShare):
            pass

        # Private-public division.
        if isinstance(lhs, AdditiveArrayShare) and isinstance(rhs, numpy.ndarray):
            pass

        # Public-private division.
        if isinstance(lhs, numpy.ndarray) and isinstance(rhs, AdditiveArrayShare):
            pass

        raise NotImplementedError(f"Privacy-preserving division not implemented for the given types: {type(lhs)} and {type(rhs)}.")


    def field_dot(self, lhs, rhs):
        """Return the dot product of two secret shared vectors.

        This is a collective operation that *must* be called
        by all players that are members of :attr:`communicator`.

        Parameters
        ----------
        lhs: :class:`AdditiveArrayShare`, required
            Secret shared vector.
        rhs: :class:`AdditiveArrayShare`, required
            Secret shared vector.

        Returns
        -------
        result: :class:`AdditiveArrayShare`
            Secret-shared dot product of `lhs` and `rhs`.
        """
        self._assert_binary_compatible(lhs, rhs, "lhs", "rhs")
        result = self.field_multiply(lhs, rhs)
        result = self.sum(result)
        return result


    def field_multiply(self, lhs, rhs):
        """Element-wise multiplication of two shared arrays.

        Note that this operation multiplies field values in the field -
        when using fixed-point encodings, the result must be shifted-right
        before it can be revealed.  See :meth:`multiply` instead.

        Note
        ----
        This is a collective operation that *must* be called
        by all players that are members of :attr:`communicator`.

        Parameters
        ----------
        lhs: :class:`AdditiveArrayShare`, required
            secret value to be multiplied.
        rhs: :class:`AdditiveArrayShare`, required
            secret value to be multiplied.

        Returns
        -------
        value: :class:`AdditiveArrayShare`
            The secret elementwise product of `lhs` and `rhs`.
        """
        # Private-private multiplication.
        if isinstance(lhs, AdditiveArrayShare) and isinstance(rhs, AdditiveArrayShare):
            # To multiply using additive shares X and Y, we need to compute the
            # following polynomial:
            #
            #    (X0 + X1 + ... Xn-1)(Y0 + Y1 + ... Yn-1)
            #
            # To do so, we carefully share the terms of the polynomial with the
            # other players while ensuring that no one player receives every share
            # of either secret.  Each player multiplies and sums the terms that
            # they have on hand, producing an additive share of the result.

            rank = self.communicator.rank
            world_size = self.communicator.world_size
            count = math.ceil((world_size - 1) / 2)
            x = lhs.storage
            y = rhs.storage
            X = [] # Storage for shares received from other players.
            Y = [] # Storage for shares received from other players.

            # Distribute terms to the other players.
            for src in self.communicator.ranks:
                # Identify which players will receive terms.
                if world_size % 2 == 0 and src >= count:
                    dst = numpy.arange(src + 1, src + 1 + count - 1) % world_size
                else:
                    dst = numpy.arange(src + 1, src + 1 + count) % world_size

                # Send terms to the other players.
                values = [x] * len(dst) if src == rank else None
                share = self.communicator.scatterv(src=src, dst=dst, values=values)
                if rank in dst:
                    X.append(share)
                values = [y] * len(dst) if src == rank else None
                share = self.communicator.scatterv(src=src, dst=dst, values=values)
                if rank in dst:
                    Y.append(share)

            # Multiply the polynomial terms that we have on-hand.
            result = x * y
            for other_x, other_y in zip(X, Y):
                result += x * other_y + other_x * y

            return AdditiveArrayShare(numpy.array(result % self.field.order, dtype=self.field.dtype))

        # Public-private multiplication.
        if isinstance(lhs, numpy.ndarray) and isinstance(rhs, AdditiveArrayShare):
            return AdditiveArrayShare(self.field.multiply(lhs, rhs.storage))

        # Private-public multiplication.
        if isinstance(lhs, AdditiveArrayShare) and isinstance(rhs, numpy.ndarray):
            return AdditiveArrayShare(self.field.multiply(lhs.storage, rhs))

        raise NotImplementedError(f"Privacy-preserving multiplication not implemented for the given types: {type(lhs)} and {type(rhs)}.")


    def field_power(self, lhs, rhs):
        """Raise the private array `lhs` to the public power `rhs` on an elementwise basis

        Parameters
        ----------
        lhs: :class:`AdditiveArrayShare`, required
            Shared secret to which floor should be applied.
        rhs: :class:`int`, required
            a publically known integer and the power to which each element in lhs should be raised

        Returns
        -------
        array: :class:`AdditiveArrayShare`
            Share of the array elements from lhs all raised to the power rhs.
        """
        if isinstance(lhs, AdditiveArrayShare) and isinstance(rhs, (numpy.ndarray, int)):
            if isinstance(rhs, int):
                rhs = self.field.full_like(lhs.storage, rhs)

            ans = []
            for lhse, rhse in numpy.nditer([lhs.storage, rhs], flags=(["refs_ok"])):
                rhsbits = [int(x) for x in bin(int(rhse))[2:]][::-1]
                tmp = AdditiveArrayShare(lhse)
                it_ans = self.share(src = 0, secret=self.field.full_like(lhse, 1), shape=lhse.shape, encoding=Identity())
                limit = len(rhsbits)-1
                for i, bit in enumerate(rhsbits):
                    if bit:
                        it_ans = self.field_multiply(it_ans, tmp)
                    if i < limit:
                        tmp = self.field_multiply(tmp,tmp)
                ans.append(it_ans)
            return AdditiveArrayShare(numpy.array([x.storage for x in ans], dtype=self.field.dtype).reshape(lhs.storage.shape))

        raise NotImplementedError(f"Privacy-preserving exponentiation not implemented for the given types: {type(lhs)} and {type(rhs)}.")


    def field_subtract(self, lhs, rhs):
        """Privacy-preserving subtraction of elements in the field.

        Two cases are currently supported - either `lhs` and `rhs` are secret shares,
        or `lhs` is a public value and `rhs` is a secret share.  In the latter case, *all*
        players *must* supply the same value for `lhs`.

        Note
        ----
        This is a collective operation that *must* be called
        by all players that are members of :attr:`communicator`.

        Parameters
        ----------
        lhs: :class:`AdditiveArrayShare`or :class:`numpy.ndarray`, required
            Shared value.
        rhs: :class:`AdditiveArrayShare`, required
            Shared value to be subtracted.

        Returns
        -------
        value: :class:`AdditiveArrayShare`
            The difference `lhs` - `rhs`.
        """
        # Private-private subtraction.
        if isinstance(lhs, AdditiveArrayShare) and isinstance(rhs, AdditiveArrayShare):
            return AdditiveArrayShare(self.field.subtract(lhs.storage, rhs.storage))

        # Public-private subtraction.
        if isinstance(lhs, numpy.ndarray) and isinstance(rhs, AdditiveArrayShare):
            if self.communicator.rank == 0:
                return AdditiveArrayShare(self.field.subtract(lhs, rhs.storage))
            return AdditiveArrayShare(self.field.negative(rhs.storage))

        # Private-public subtraction.
        if isinstance(lhs, AdditiveArrayShare) and isinstance(rhs, numpy.ndarray):
            if self.communicator.rank == 0:
                return AdditiveArrayShare(self.field.subtract(lhs.storage, rhs))
            return AdditiveArrayShare(lhs.storage)

        raise NotImplementedError(f"Privacy-preserving subtraction not implemented for the given types: {type(lhs)} and {type(rhs)}.")


    def field_uniform(self, *, shape=None, generator=None):
        """Return a AdditiveSharedArray with the specified shape and filled with random field elements

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
        secret: :class:`AdditiveArrayShare`
            A share of the random generated value.
        """

        if shape is None:
            shape=()

        if generator is None:
            generator = numpy.random.default_rng()

        return AdditiveArrayShare(self.field.uniform(size=shape, generator=generator))


    def floor(self, operand, *, encoding=None):
        """Remove the `bits` least significant bits from each element in a secret shared array
            then shift back left so that only the original integer part of 'operand' remains.


        Parameters
        ----------
        operand: :class:`AdditiveArrayShare`, required
            Shared secret to which floor should be applied.

        Returns
        -------
        array: :class:`AdditiveArrayShare`
            Share of the shared integer part of operand.
        """
        self._assert_unary_compatible(operand, "operand")
        encoding = self._require_encoding(encoding)

        one = self.share(src=0, secret=self.field.full_like(operand.storage, 2**encoding.precision), shape=operand.storage.shape, encoding=Identity())
        shift_op = self.field.full_like(operand.storage, 2**encoding.precision)
        pl2 = self.field.full_like(operand.storage, self.field.order-1)

        abs_op = self.absolute(operand)
        frac_bits = encoding.precision
        field_bits = self.field.fieldbits
        lsbs = self.bit_decompose(abs_op, bits=encoding.precision)
        lsbs_composed = self.bit_compose(lsbs)
        lsbs_inv = self.negative(lsbs_composed)
        two_lsbs = AdditiveArrayShare(self.field.multiply(lsbs_composed.storage, self.field.full_like(lsbs_composed.storage, 2)))
        ltz = self.less_zero(operand)
        ones2sub = AdditiveArrayShare(self.field.multiply(self.field_power(lsbs_composed, pl2).storage, shift_op))
        sel_2_lsbs = self.field_multiply(self.field_subtract(two_lsbs, ones2sub), ltz)
        return self.field_add(self.field_add(sel_2_lsbs, lsbs_inv), operand)


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
        lhs: :class:`AdditiveArrayShare`, required
            Secret shared value to be compared.
        rhs: :class:`AdditiveArrayShare`, required
            Secret shared value to be compared.

        Returns
        -------
        result: :class:`AdditiveArrayShare`
            Secret-shared result of computing `lhs` < `rhs` elementwise.
        """
        self._assert_binary_compatible(lhs, rhs, "lhs", "rhs")

        one = self.field.full_like(lhs.storage, 1)
        two = self.field.full_like(lhs.storage, 2)
        twolhs = self.field_multiply(two, lhs)
        tworhs = self.field_multiply(two, rhs)
        diff = self.field_subtract(lhs, rhs)
        twodiff = self.field_multiply(two, diff)
        w = self.field_subtract(one, self._lsb(twolhs))
        x = self.field_subtract(one, self._lsb(tworhs))
        y = self.field_subtract(one, self._lsb(twodiff))
        wxorx = self.logical_xor(w,x)
        notwxorx = self.field_subtract(one, wxorx)
        xwxorx = self.field_multiply(x, wxorx)
        noty = self.field_subtract(one, y)
        notwxorxnoty = self.field_multiply(notwxorx, noty)
        return self.field_add(xwxorx, notwxorxnoty)


    def less_zero(self, operand):
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
        operand: :class:`AdditiveArrayShare`, required
            Secret shared value to be compared.

        Returns
        -------
        result: :class:`AdditiveArrayShare`
            Secret-shared result of computing `operand` < `0` elementwise.
        """
        self._assert_unary_compatible(operand, "operand")
        two = self.field.full_like(operand.storage, 2)
        result = self.field_multiply(two, operand)
        return self._lsb(result)


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
        lhs: :class:`AdditiveArrayShare`, required
            Secret shared array to be AND'ed.
        rhs: :class:`AdditiveArrayShare`, required
            Secret shared array to be AND'ed.

        Returns
        -------
        value: :class:`AdditiveArrayShare`
            The secret elementwise logical AND of `lhs` and `rhs`.
        """
        self._assert_binary_compatible(lhs, rhs, "lhs", "rhs")
        return self.field_multiply(lhs, rhs)


    def logical_not(self, operand):
        """Return the elementwise logical NOT of a secret shared arrays.

        The operand *must* contain the *field* values `0` or `1`.  The result
        will be the secret shared elementwise logical negation of `operand`.
        When revealed, the result will contain the field values `0` or `1`, which do
        not require decoding.

        Note
        ----
        This is a collective operation that *must* be called
        by all players that are members of :attr:`communicator`.

        Parameters
        ----------
        operand: :class:`AdditiveArrayShare`, required
            Secret shared array to be negated.

        Returns
        -------
        value: :class:`AdditiveArrayShare`
            The secret elementwise logical NOT of `operand`.
        """
        self._assert_unary_compatible(operand, "operand")
        return self.field_subtract(self.field.ones_like(operand.storage), operand)


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
        lhs: :class:`AdditiveArrayShare`, required
            Secret shared array to be OR'd.
        rhs: :class:`AdditiveArrayShare`, required
            Secret shared array to be OR'd.

        Returns
        -------
        value: :class:`AdditiveArrayShare`
            The secret elementwise logical OR of `lhs` and `rhs`.
        """
        self._assert_binary_compatible(lhs, rhs, "lhs", "rhs")
        total = self.field_add(lhs, rhs)
        product = self.field_multiply(lhs, rhs)
        return self.field_subtract(total, product)


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
        lhs: :class:`AdditiveArrayShare`, required
            Secret shared array to be exclusive OR'd.
        rhs: :class:`AdditiveArrayShare`, required
            Secret shared array to be exclusive OR'd.

        Returns
        -------
        value: :class:`AdditiveArrayShare`
            The secret elementwise logical exclusive OR of `lhs` and `rhs`.
        """
        self._assert_binary_compatible(lhs, rhs, "lhs", "rhs")
        total = self.field_add(lhs, rhs)
        product = self.field_multiply(lhs, rhs)
        twice_product = self.field_multiply(self.field(2), product)
        return self.field_subtract(total, twice_product)


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
        operand: :class:`AdditiveArrayShare`, required
            Secret shared array from which the least significant bits will be extracted

        Returns
        -------
        lsb: :class:`AdditiveArrayShare`
            Additive shared array containing the elementwise least significant
            bits of `operand`.
        """
        one = numpy.array(1, dtype=self.field.dtype)
        lop = AdditiveArrayShare(operand.storage.flatten())
        tmpBW, tmp = self.random_bitwise_secret(bits=self.field._fieldbits, shape=lop.storage.shape)
        maskedlop = self.field_add(lop, tmp)
        c = self.reveal(maskedlop, encoding=Identity())
        comp_result = self._public_bitwise_less_than(lhspub=c, rhs=tmpBW)
        c = (c % 2)
        c0xr0 = numpy.empty(c.shape, dtype = self.field.dtype)
        for i, lc in enumerate(c):
            if lc:
                c0xr0[i] = self.field_subtract(lhs=one, rhs=AdditiveArrayShare(numpy.array(tmpBW.storage[i][-1], dtype=self.field.dtype))).storage
            else:
                c0xr0[i] = tmpBW.storage[i][-1]
        c0xr0 = AdditiveArrayShare(c0xr0)
        result = self.field_multiply(lhs=comp_result, rhs=c0xr0)
        result = AdditiveArrayShare(self.field.multiply(lhs=self.field.full_like(result.storage, 2), rhs=result.storage))
        result = self.field_subtract(lhs=c0xr0, rhs=result)
        result = self.field_add(lhs=comp_result, rhs=result)
        return AdditiveArrayShare(result.storage.reshape(operand.storage.shape))


    def maximum(self, lhs, rhs):
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
        lhs: :class:`AdditiveArrayShare`, required
            Secret shared operand.
        rhs: :class:`AdditiveArrayShare`, required
            Secret shared operand.

        Returns
        -------
        max: :class:`AdditiveArrayShare`
            Secret-shared elementwise maximum of `lhs` and `rhs`.
        """
        self._assert_binary_compatible(lhs, rhs, "lhs", "rhs")
        max_share = self.field_add(self.field_add(lhs, rhs), self.absolute(self.field_subtract(lhs, rhs)))
        shift_right = self.field.full_like(lhs.storage, pow(2, self.field.order-2, self.field.order))
        max_share = self.field_multiply(max_share, shift_right)
        return max_share


    def minimum(self, lhs, rhs):
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
        lhs: :class:`AdditiveArrayShare`, required
            Secret shared operand.
        rhs: :class:`AdditiveArrayShare`, required
            Secret shared operand.

        Returns
        -------
        min: :class:`AdditiveArrayShare`
            Secret-shared elementwise minimum of `lhs` and `rhs`.
        """
        self._assert_binary_compatible(lhs, rhs, "lhs", "rhs")
        diff = self.field_subtract(lhs, rhs)
        abs_diff = self.absolute(diff)
        min_share = self.field_subtract(self.field_add(lhs, rhs), abs_diff)
        shift_right = self.field.full_like(lhs.storage, pow(2, self.field.order-2, self.field.order))
        min_share = self.field_multiply(min_share, shift_right)

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
        operand: :class:`AdditiveArrayShare`, required
            Secret shared array to be multiplicatively inverted.

        Returns
        -------
        value: :class:`AdditiveArrayShare`
            The secret multiplicative inverse of operand on an elementwise basis.
        """
        self._assert_unary_compatible(operand, "operand")

        mask = self.field_uniform(shape=operand.storage.shape)
        masked_op = self.field_multiply(mask, operand)
        revealed_masked_op = self.reveal(masked_op, encoding=Identity())
        nppowmod = numpy.vectorize(lambda a, b, c: pow(int(a), int(b), int(c)), otypes=[self.field.dtype])
        inv = numpy.array(nppowmod(revealed_masked_op, self.field.order-2, self.field.order), dtype=self.field.dtype)
        op_inv_share = self.field.multiply(inv, mask.storage)
        return AdditiveArrayShare(op_inv_share)


    def multiply(self, lhs, rhs, *, encoding=None):
        """Return the elementwise product of two secret shared arrays.

        This is a collective operation that *must* be called
        by all players that are members of :attr:`communicator`.

        Parameters
        ----------
        lhs: :class:`AdditiveArrayShare`, required
            Secret shared array.
        rhs: :class:`AdditiveArrayShare`, required
            Secret shared array.
        encoding: :class:`object`, optional
            Encoding originally used to convert the secrets into field values.
            The protocol's default encoding will be used if `None`.

        Returns
        -------
        result: :class:`AdditiveArrayShare`
            Secret-shared elementwise product of `lhs` and `rhs`.
        """
        encoding = self._require_encoding(encoding)

        # Private-private multiplication.
        if isinstance(lhs, AdditiveArrayShare) and isinstance(rhs, AdditiveArrayShare):
            result = self.field_multiply(lhs, rhs)
            result = self.right_shift(result, bits=encoding.precision)
            return result

        # Private-public multiplication.
        if isinstance(lhs, AdditiveArrayShare) and isinstance(rhs, numpy.ndarray):
            result = self.field_multiply(lhs, encoding.encode(rhs, self.field))
            result = self.right_shift(result, bits=encoding.precision)
            return result

        # Public-private multiplication.
        if isinstance(lhs, numpy.ndarray) and isinstance(rhs, AdditiveArrayShare):
            result = self.field_multiply(encoding.encode(lhs, self.field), rhs)
            result = self.right_shift(result, bits=encoding.precision)
            return result

        raise NotImplementedError(f"Privacy-preserving multiplication not implemented for the given types: {type(lhs)} and {type(rhs)}.")


    def negative(self, operand):
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
        operand: :class:`AdditiveArrayShare`, required
            Secret shared array to be additively inverted.

        Returns
        -------
        value: :class:`AdditiveArrayShare`
            The secret additive inverse of operand on an elementwise basis.
        """
        self._assert_unary_compatible(operand, "operand")
        return self.field_subtract(self.field.full_like(operand.storage, self.field.order), operand)

    def pade_approx(self, func, endpoints, resolution, operand,*, encoding=None, degree=9):
        """Return the pade approximation of func evaluated at operand.

        This is a collective operation that *must* be called
        by all players that are members of :attr:`communicator`.

        Parameters
        ----------
        func: :class:`callable object`, required
            The function to be approximated via the pade method
        endpoints: :class:`tuple`, required
            The start and end of the range of interest for approximation/interpolation
        resolution: :class:`float`, required
            The resolution of the approximation to be done between the endpoints
        operand: :class:`AdditiveArrayShare`, required
            The secret share which represents the point at which the function func should be evaluated in a privacy preserving manner

        Returns
        -------
        result: :class:`AdditiveArrayShare`
            Secret shared result of evaluating the pade approximant of func(operand) with the given parameters
        """
        from scipy.interpolate import approximate_taylor_polynomial, pade
        axis = numy.linspace(endpoints[0], endpoints[1], resolution)
        num_deg = degree%2+degree//2
        den_deg = degree//2

        self._assert_unary_compatible(operand, "operand")
        encoding = self._require_encoding(encoding)

        func_taylor = approximate_taylor_polynomial(func, (endpoints[0]+endpoints[1])/2, degree, degree+1)
        func_pade_num, func_pade_den = pade(func_taylor, den_deg, n=num_deg)
        enc_func_pade_num = encoding.encode(numpy.array([x for x in func_pade_num]), self.field)
        enc_func_pade_den = encoding.encode(numpy.array([x for x in func_pade_den]), self.field)
        op_pows_num = [operand]
        for i in range(num_deg):
            op_pows_num.append(self.multiply(operand, op_pows_num[-1]))
        if degree%2:
            op_pows_den=[thing for thing in op_pows_num[:-1]]
        else:
            op_pows_den=[thing for thing in op_pows_num]
        
        result_num_prod = self.field_multiply(op_pows_num, enc_func_pade_num)
        result_num = self.sum(result_num_prod)

        result_den_prod = self.field_multiply(op_pows_den, enc_func_pade_den)
        result_den = self.sum(result_den_prod)
        
        result = self.divide(result_num, result_den)
        return result

    def power(self, lhs, rhs, *, encoding=None):
        """Raise the array contained in lhs to the power rhs on an elementwise basis

        Parameters
        ----------
        lhs: :class:`AdditiveArrayShare`, required
            Shared secret to which floor should be applied.
        rhs: :class:`int`, required
            a publically known integer and the power to which each element in lhs should be raised

        Returns
        -------
        array: :class:`AdditiveArrayShare`
            Share of the array elements from lhs all raised to the power rhs.
        """
        encoding = self._require_encoding(encoding)

        if isinstance(lhs, AdditiveArrayShare) and isinstance(rhs, (numpy.ndarray, int)):
            if isinstance(rhs, int):
                rhs = self.field.full_like(lhs.storage, rhs)

            ans=[]
            for lhse, rhse in numpy.nditer([lhs.storage, rhs], flags=(["refs_ok"])):
                rhsbits = [int(x) for x in bin(rhse)[2:]][::-1]
                tmp = AdditiveArrayShare(lhse)
                it_ans = self.share(src = 0, secret=self.field.full_like(tmp.storage, encoding.encode(numpy.array(1), self.field)),shape=tmp.storage.shape, encoding=Identity())
                limit = len(rhsbits)-1
                for i, bit in enumerate(rhsbits):
                    if bit:
                        it_ans = self.field_multiply(it_ans, tmp)
                        it_ans = self.right_shift(it_ans, bits=encoding.precision)
                    if i < limit:
                        tmp = self.field_multiply(tmp,tmp)
                        tmp = self.right_shift(tmp, bits=encoding.precision)
                ans.append(it_ans)
            return AdditiveArrayShare(numpy.array([x.storage for x in ans], dtype=self.field.dtype).reshape(lhs.storage.shape))

        raise NotImplementedError(f"Privacy-preserving exponentiation not implemented for the given types: {type(lhs)} and {type(rhs)}.")


    def _public_bitwise_less_than(self, *, lhspub, rhs):
        """Comparison Operator

        Parameters
        ----------
        lhs: :class:`ndarray`, required
            a publically known numpy array of integers and one of the two objects to be compared
        rhs: :class:`AdditiveArrayShare`, required
            bit decomposed shared secret(s) and the other of the two objects to be compared
            the bitwidth of each value in rhs (deduced from its shape) is taken to be the
            bitwidth of interest for the comparison if the values in lhspub require more bits
            for their representation, the computation will be incorrect

        note: this method is private as it does not consider the semantic mapping of meaning
        onto the field. The practical result of this is that every negative value will register as
        greater than every positive value due to the encoding.


        Returns
        -------
        an additive shared array containing the element wise result of the comparison: result[i] = 1 if lhspub[i] < rhs[i] and 0 otherwise
        """
        if lhspub.shape != rhs.storage.shape[:-1]:
            raise ValueError('rhs is not of the expected shape - it should be the same as lhs except the last dimension') # pragma: no cover
        bitwidth = rhs.storage.shape[-1]
        lhsbits = []
        for val in lhspub:
            tmplist = [int(x) for x in bin(val)[2:]]
            if len(tmplist) < bitwidth:
                tmplist = [0 for x in range(bitwidth-len(tmplist))] + tmplist
            lhsbits.append(tmplist)
        lhsbits = numpy.array(lhsbits, dtype=self.field.dtype)
        assert(lhsbits.shape == rhs.storage.shape)
        one = numpy.array(1, dtype=self.field.dtype)
        flatlhsbits = lhsbits.reshape((-1, lhsbits.shape[-1]))
        flatrhsbits = rhs.storage.reshape((-1, rhs.storage.shape[-1]))
        results=[]
        for j in range(len(flatlhsbits)):
            xord = []
            preord = []
            msbdiff=[]
            rhs_bit_at_msb_diff = []
            for i in range(bitwidth):
                rhsbit=AdditiveArrayShare(storage=numpy.array(flatrhsbits[j,i], dtype=self.field.dtype))
                if flatlhsbits[j][i] == 1:
                    xord.append(self.field_subtract(lhs=one, rhs=rhsbit))
                else:
                    xord.append(rhsbit)
            preord = [xord[0]]
            for i in range(1,bitwidth):
                preord.append(self.logical_or(lhs=preord[i-1], rhs=xord[i]))
            msbdiff = [preord[0]]
            for i in range(1,bitwidth):
                msbdiff.append(self.field_subtract(lhs=preord[i], rhs=preord[i-1]))
            for i in range(bitwidth):
                rhsbit=AdditiveArrayShare(storage=numpy.array(flatrhsbits[j,i], dtype=self.field.dtype))
                rhs_bit_at_msb_diff.append(self.field_multiply(rhsbit, msbdiff[i]))
            result = rhs_bit_at_msb_diff[0]
            for i in range(1,bitwidth):
                result = self.field_add(lhs=result, rhs=rhs_bit_at_msb_diff[i])
            results.append(result)
        return AdditiveArrayShare(storage = numpy.array([x.storage for x in results], dtype=self.field.dtype).reshape(rhs.storage.shape[:-1]))


    def random_bitwise_secret(self, *, bits, src=None, generator=None, shape=None):
        """Return a vector of randomly generated bits.

        This method is secure against non-colluding semi-honest adversaries.  A
        subset of players (by default: all) generate and secret share vectors
        of pseudo-random bits which are then xor-ed together elementwise.
        Communication and computation costs increase with the number of bits
        and the number of players, while security increases with the number of
        players.

        .. warning::

             If you supply your own generators, be careful to ensure that each
             has a unique seed value to preserve privacy (for example: a
             constant plus the player's rank).  If players receive generators
             with identical seed values, even numbers of players will produce
             all zero bits.

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
        bits: :class:`AdditiveArrayShare`
            A share of the randomly-generated bits that make-up the secret.
        secret: :class:`AdditiveArrayShare`
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
                local_bits = generator.choice(2, size=bits).astype(self.field.dtype)
            else:
                local_bits = None

            # Each participating player secret shares their bit vectors.
            player_bit_shares = []
            for rank in src:
                player_bit_shares.append(self.share(src=rank, secret=local_bits, shape=(bits,), encoding=Identity()))

            # Generate the final bit vector by xor-ing everything together elementwise.
            bit_share = player_bit_shares[0]
            for player_bit_share in player_bit_shares[1:]:
                bit_share = self.logical_xor(bit_share, player_bit_share)

            # Shift and combine the resulting bits in big-endian order to produce a random value.
            shift = numpy.power(2, numpy.arange(bits, dtype=self.field.dtype)[::-1])
            shifted = self.field.multiply(shift, bit_share.storage)
            secret_share = AdditiveArrayShare(numpy.array(numpy.sum(shifted), dtype=self.field.dtype))
            bit_res.append(bit_share)
            share_res.append(secret_share)
        if shape_was_none:
            bit_share = AdditiveArrayShare(numpy.array([x.storage for x in bit_res], dtype=self.field.dtype).reshape(bits))
            secret_share = AdditiveArrayShare(numpy.array([x.storage for x in share_res], dtype=self.field.dtype).reshape(shape))#, order="C"))
        else:
            bit_share = AdditiveArrayShare(numpy.array([x.storage for x in bit_res], dtype=self.field.dtype).reshape(shape+(bits,)))#, order="C"))
            secret_share = AdditiveArrayShare(numpy.array([x.storage for x in share_res], dtype=self.field.dtype).reshape(shape))#, order="C"))

        return bit_share, secret_share


    def relu(self, operand):
        """Return the elementwise ReLU of a secret shared array.

        Note
        ----
        This is a collective operation that *must* be called
        by all players that are members of :attr:`communicator`.

        Parameters
        ----------
        operand: :class:`AdditiveArrayShare`, required
            Secret shared value to which the ReLU function should be applied.

        Returns
        -------
        value: :class:`AdditiveArrayShare`
            Secret-shared elementwise ReLU of `operand`.
        """
        self._assert_unary_compatible(operand, "operand")
        ltz = self.less_zero(operand)
        nltz = self.logical_not(ltz)
        nltz_parts = self.field_multiply(nltz, operand)
        return nltz_parts


    def reshare(self, operand):
        """Rerandomize an additive secret share.

        Note
        ----
        This is a collective operation that *must* be called
        by all players that are members of :attr:`communicator`.

        Parameters
        ----------
        operand: :class:`AdditiveArrayShare`
            The local share of the secret shared array.

        Returns
        -------
        share: :class:`AdditiveArrayShare`
            The local share of the secret shared array, now rerandomized.
        """
        self._assert_unary_compatible(operand, "operand")
        recshares = []
        for i in range(self.communicator.world_size):
            recshares.append(self.share(src=i, secret=operand.storage, shape=operand.storage.shape, encoding=Identity()))
        acc = numpy.zeros(operand.storage.shape, dtype=self.field.dtype)
        for s in recshares:
            acc += s.storage
        acc %= self.field.order
        return AdditiveArrayShare(acc)


    def reveal(self, share, *, dst=None, encoding=None):
        """Reveals a secret shared value to a subset of players.

        Note
        ----
        This is a collective operation that *must* be called by all players
        that are members of :attr:`communicator`, whether they are receiving
        the revealed secret or not.

        Parameters
        ----------
        share: :class:`AdditiveArrayShare`, required
            The local share of the secret to be revealed.
        dst: sequence of :class:`int`, optional
            List of players who will receive the revealed secret.  If :any:`None`
            (the default), the secret will be revealed to all players.
        encoding: :class:`object`, optional
            Encoding used to extract the revealed secret from field values. The
            protocol's default encoding will be used if `None`.

        Returns
        -------
        value: :class:`numpy.ndarray` or :any:`None`
            The revealed secret, if this player is a member of `dst`, or :any:`None`.
        """
        if not isinstance(share, AdditiveArrayShare):
            raise ValueError("share must be an instance of AdditiveArrayShare.") # pragma: no cover

        # Identify who will be receiving shares.
        if dst is None:
            dst = self.communicator.ranks

        encoding = self._require_encoding(encoding)

        # Send data to the other players.
        secret = None
        for recipient in dst:
            received_shares = self.communicator.gather(value=share.storage, dst=recipient)

            # If we're a recipient, recover the secret.
            if self.communicator.rank == recipient:
                secret = received_shares[0].copy()
                for received_share in received_shares[1:]:
                    self.field.inplace_add(secret, received_share)

        return encoding.decode(secret, self.field)


    def right_shift(self, operand, *, bits, src=None, generator=None, trunc_mask=None, rem_mask=None):
        """Remove the `bits` least significant bits from each element in a secret shared array.

        Note
        ----
        The operand *must* be encoded with FixedFieldEncoder

        Parameters
        ----------
        operand: :class:`AdditiveArrayShare`, required
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
        array: :class:`AdditiveArrayShare`
            Share of the truncated secret.
        """
        if not isinstance(operand, AdditiveArrayShare):
            raise ValueError(f"Expected operand to be an instance of AdditiveArrayShare, got {type(operand)} instead.") # pragma: no cover

        fieldbits = self.field.fieldbits

        shift_left = self.field.full_like(operand.storage, 2**bits)
        # Multiplicative inverse of shift_left.
        shift_right = self.field.full_like(operand.storage, pow(2**bits, self.field.order-2, self.field.order))

        if trunc_mask:
            truncation_mask = trunc_mask
        else:
            # Generate random bits that will mask the region to be truncated.
            _, truncation_mask = self.random_bitwise_secret(bits=bits, src=src, generator=generator, shape=operand.storage.shape)
        if rem_mask:
            remaining_mask = rem_mask
        else:
            # Generate random bits that will mask everything outside the region to be truncated.
            _, remaining_mask = self.random_bitwise_secret(bits=fieldbits-bits, src=src, generator=generator, shape=operand.storage.shape)
        remaining_mask.storage = self.field.multiply(remaining_mask.storage, shift_left)

        # Combine the two masks.
        mask = self.field_add(remaining_mask, truncation_mask)

        # Mask the array element.
        masked_element = self.field_add(mask, operand)

        # Reveal the element to all players (because it's masked, no player learns the underlying secret).
        masked_element = self.reveal(masked_element, encoding=Identity())

        # Retain just the bits within the region to be truncated, which need to be removed.
        masked_truncation_bits = numpy.array(masked_element % shift_left, dtype=self.field.dtype)

        # Remove the mask, leaving just the bits to be removed from the
        # truncation region.  Because the result of the subtraction is
        # secret shared, the secret still isn't revealed.
        truncation_bits = self.field_subtract(masked_truncation_bits, truncation_mask)

        # Remove the bits in the truncation region from the element.  The result can be safely truncated.
        result = self.field_subtract(operand, truncation_bits)

        # Truncate the element by shifting right to get rid of the (now cleared) bits in the truncation region.
        result = self.field.multiply(result.storage, shift_right)

        return AdditiveArrayShare(result)


    def share(self, *, src, secret, shape, encoding=None):
        """Convert an array of scalars to an additive secret share.

        Note
        ----
        This is a collective operation that *must* be called
        by all players that are members of :attr:`communicator`.

        Parameters
        ----------
        src: :class:`int`, required
            The player providing the private array to be secret shared.
        secret: :class:`numpy.ndarray` or :any:`None`, required
            The secret array to be shared.  This value is ignored for all
            players except `src`.
        shape: :class:`tuple`, required
            The shape of the secret.  Note that all players must specify the
            same shape.
        encoding: :class:`object`, optional
            Encoding used to convert `secret` into field values. The protocol's
            default encoding will be used if `None`.

        Returns
        -------
        share: :class:`AdditiveArrayShare`
            The local share of the secret shared array.
        """
        if not isinstance(shape, tuple):
            shape = (shape,)

        if self.communicator.rank == src:
            if not isinstance(secret, numpy.ndarray):
                raise ValueError("secret must be an instance of numpy.ndarray.") # pragma: no cover
            if secret.shape != shape:
                raise ValueError(f"Expected secret.shape {shape}, got {secret.shape} instead.") # pragma: no cover

        encoding = self._require_encoding(encoding)

        # Generate a pseudo-random sharing of zero ...
        przs = self.field.uniform(size=shape, generator=self._g0)
        self.field.inplace_subtract(przs, self.field.uniform(size=shape, generator=self._g1))

        # Add the secret to the PRSZ
        if self.communicator.rank == src:
            secret = encoding.encode(secret, self.field)
            self.field.inplace_add(przs, secret)
        # Package the result.
        return AdditiveArrayShare(przs)


    def subtract(self, lhs, rhs, *, encoding=None):
        """Return the elementwise difference of two secret shared arrays.

        The result is the secret shared elementwise sum of the operands.

        Note
        ----
        This is a collective operation that *must* be called
        by all players that are members of :attr:`communicator`.

        Parameters
        ----------
        lhs: :class:`AdditiveArrayShare`, required
            Secret shared value to be added.
        rhs: :class:`AdditiveArrayShare`, required
            Secret shared value to be added.

        Returns
        -------
        value: :class:`AdditiveArrayShare`
            Secret-shared sum of `lhs` and `rhs`.
        """
        encoding = self._require_encoding(encoding)

        # Private-private subtraction.
        if isinstance(lhs, AdditiveArrayShare) and isinstance(rhs, AdditiveArrayShare):
            return self.field_subtract(lhs, rhs)

        # Private-public subtraction.
        if isinstance(lhs, AdditiveArrayShare) and isinstance(rhs, numpy.ndarray):
            return self.field_subtract(lhs, encoding.encode(rhs, self.field))

        # Public-private subtraction.
        if isinstance(lhs, numpy.ndarray) and isinstance(rhs, AdditiveArrayShare):
            return self.field_subtract(encoding.encode(lhs, self.field), rhs)

        raise NotImplementedError(f"Privacy-preserving subtraction not implemented for the given types: {type(lhs)} and {type(rhs)}.")


    def sum(self, operand):
        """Return the sum of a secret shared array's elements.

        The result is the secret shared sum of the array elements.  If
        revealed, the result will need to be decoded to obtain the actual sum.

        Note
        ----
        This is a collective operation that *must* be called
        by all players that are members of :attr:`communicator`.

        Parameters
        ----------
        operand: :class:`AdditiveArrayShare`, required
            Secret shared array to be summed.

        Returns
        -------
        value: :class:`AdditiveArrayShare`
            Secret-shared sum of `operand`'s elements.
        """
        self._assert_unary_compatible(operand, "operand")
        return AdditiveArrayShare(self.field.sum(operand.storage))


#    def untruncated_divide(self, lhs, rhs, *, rmask=None, mask1=None, rem1=None, mask2=None, rem2=None):
#        """Element-wise division of private values. Note: this may have a chance to leak info is the secret contained in rhs is 
#        close to or bigger than 2^precision
#
#        Note
#        ----
#        This is a collective operation that *must* be called
#        by all players that are members of :attr:`communicator`.
#
#        Parameters
#        ----------
#        lhs: :class:`AdditiveArrayShare`, required
#            Secret shared array dividend.
#        rhs: :class:`numpy.ndarray`, required
#            Public array divisor, which must *not* be encoded.
#
#        Returns
#        -------
#        value: :class:`AdditiveArrayShare`
#            The secret element-wise result of lhs / rhs.
#        """
#        self._assert_binary_compatible(lhs, rhs, "lhs", "rhs")
#        if rmask is None:
#            _, rmask = self.random_bitwise_secret(bits=self._encoding.precision, shape=rhs.storage.shape)
#        rhsmasked = self.untruncated_multiply(rmask, rhs)
#        if mask1 != None and rem1 != None:
#            rhsmasked = self.truncate(rhsmasked, trunc_mask=mask1, rem_mask=rem1)
#        else:
#            rhsmasked = self.truncate(rhsmasked)
#        revealrhsmasked = self._encoding.decode(self._reveal(rhsmasked), self.field)
#        if mask2 != None and rem2 != None:
#            almost_there = self.truncate(self.untruncated_multiply(lhs, rmask), trunc_mask=mask2, rem_mask=rem2)
#        else:
#            almost_there = self.truncate(self.untruncated_multiply(lhs, rmask))
#        maskquotient = self.untruncated_private_public_divide(almost_there, revealrhsmasked)
#        return maskquotient 
#
#
#    def untruncated_private_public_divide(self, lhs, rhs):
#        """Element-wise division of private and public values.
#
#        Note
#        ----
#        This is a collective operation that *must* be called
#        by all players that are members of :attr:`communicator`.
#
#        Parameters
#        ----------
#        lhs: :class:`AdditiveArrayShare`, required
#            Secret shared array dividend.
#        rhs: :class:`numpy.ndarray`, required
#            Public array divisor, which must *not* be encoded.
#
#        Returns
#        -------
#        value: :class:`AdditiveArrayShare`
#            The secret element-wise result of lhs / rhs.
#        """
#        self._assert_unary_compatible(lhs, "lhs")
#        divisor = self._encoding.encode(numpy.array(1 / rhs), self.field)
#        quotient = AdditiveArrayShare(self.field.untruncated_multiply(lhs.storage, divisor))
#        return quotient


    def zigmoid(self, operand, *, encoding=None):
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
        operand: :class:`AdditiveArrayShare`, required
            Secret shared value to which the zigmoid function should be applied.

        Returns
        -------
        value: :class:`AdditiveArrayShare`
            Secret-shared elementwise zigmoid of `operand`.
        """
        self._assert_unary_compatible(operand, "operand")
        encoding = self._require_encoding(encoding)

        ones = encoding.encode(numpy.full_like(operand.storage, 1.0), self.field)
        half = encoding.encode(numpy.full_like(operand.storage, 0.5), self.field)

        secret_plushalf = self.field_add(half, operand)
        secret_minushalf = self.field_subtract(operand, half)
        ltzsmh = self.less_zero(secret_minushalf)
        nltzsmh = self.logical_not(ltzsmh)
        ltzsph = self.less_zero(secret_plushalf)
        middlins = self.field_subtract(ltzsmh, ltzsph)
        extracted_middlins = self.field_multiply(middlins, operand)
        extracted_halfs = self.field_multiply(middlins, half)
        extracted_middlins = self.field_add(extracted_middlins, extracted_halfs)
        ones_part = self.field_multiply(nltzsmh, ones)
        return self.field_add(ones_part, extracted_middlins)

