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

import numpy

from cicada.additive import AdditiveArrayShare, AdditiveProtocolSuite
from cicada.arithmetic import Field
from cicada.communicator.interface import Communicator
from cicada.encoding import FixedPoint, Identity
from cicada.shamir import ShamirArrayShare, ShamirProtocolSuite


class ActiveArrayShare(object):
    """Stores the local share of a secret shared array for :class:`ActiveProtocolSuite`.

    Instances of :class:`ActiveArrayShare` should only be created
    using :class:`ActiveProtocolSuite`.
    """
    def __init__(self, storage):
        self.storage = storage


    def __repr__(self):
        return f"cicada.active.ActiveArrayShare(storage={self._storage})" # pragma: no cover


    def __getitem__(self, index):
        return ActiveArrayShare((
            AdditiveArrayShare(self.additive.storage[index]),
            ShamirArrayShare(self.shamir.storage[index])))


    @property
    def storage(self):
        """Private storage for the local share of a secret shared array.
        Access is provided only for serialization and communication -
        callers must use :class:`ActiveProtocolSuite` to manipulate secret
        shares.
        """
        return self._storage

    @property
    def additive(self):
        return self._storage[0]

    @property
    def shamir(self):
        return self._storage[1]

    @storage.setter
    def storage(self, storage):
        if not len(storage) == 2:
            raise ValueError(f"Expected instances of AdditiveArrayShare and ShamirArrayShare, got {storage} instead.") # pragma: no cover
        if not isinstance(storage[0], AdditiveArrayShare):
            raise ValueError(f"Expected instances of AdditiveArrayShare and ShamirArrayShare, got {storage} instead.") # pragma: no cover
        if not isinstance(storage[1], ShamirArrayShare):
            raise ValueError(f"Expected instances of AdditiveArrayShare and ShamirArrayShare, got {storage} instead.") # pragma: no cover
        self._storage = (storage[0], storage[1])


class ConsistencyError(Exception):
    pass


class ActiveProtocolSuite(object):
    """Protocol suite implementing computation with shared secrets that is secure against an active adversary.

    Implements "Combining Shamir & additive secret sharing to improve
    efficiency of SMC primitives against malicious adversaries" by Goss, which
    provides honest majority security with abort.

    Both :class:`~cicada.additive.AdditiveProtocolSuite` and
    :class:`~cicada.shamir.ShamirProtocolSuite` are used for the implementation.

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
    precision: :class:`int`, optional
        The number of bits for storing fractions in encoded values.  Defaults
        to 16.
    """
    def __init__(self, communicator, *, threshold, seed=None, seed_offset=None, order=None, encoding=None):
        if not isinstance(communicator, Communicator):
            raise ValueError("A Cicada communicator is required.") # pragma: no cover

        if encoding is None:
            encoding = FixedPoint()

        max_threshold = (communicator.world_size+1) // 2
        if threshold > max_threshold:
            min_world_size = (2 * threshold) - 1
            raise ValueError(f"threshold must be <= {max_threshold}, or world_size must be >= {min_world_size}")

        self._communicator = communicator
        self._field = Field(order=order)
        self.aprotocol = AdditiveProtocolSuite(communicator=communicator, seed=seed, seed_offset=seed_offset, order=order, encoding=encoding)
        self.sprotocol = ShamirProtocolSuite(communicator=communicator, threshold=threshold, seed=seed, seed_offset=seed_offset, order=order, encoding=encoding)


    def _assert_binary_compatible(self, lhs, rhs, lhslabel, rhslabel):
        self._assert_unary_compatible(lhs, lhslabel)
        self._assert_unary_compatible(rhs, rhslabel)
        if lhs.additive.storage.shape != rhs.additive.storage.shape :
            raise ValueError(f"{lhslabel} and {rhslabel} additive shares, the additive subshares must be the same shape, got {lhs.additive.storage.shape} and {rhs.additive.storage.shape} instead.") # pragma: no cover
        if lhs.shamir.storage.shape != rhs.shamir.storage.shape:
            raise ValueError(f"{lhslabel} and {rhslabel} shamir shares, the Shamir subshares must be the same shape, got {lhs.shamir.storage.shape} and {rhs.shamir.storage.shape} instead.") # pragma: no cover


    def _assert_unary_compatible(self, share, label):
        if not isinstance(share, ActiveArrayShare):
            raise ValueError(f"{label} must be an instance of ActiveArrayShare, got {type(share)} instead.") # pragma: no cover


    def _require_encoding(self, encoding):
        if encoding is None:
            encoding = self.aprotocol.encoding
        return encoding


    def absolute(self, operand):
        """Return the elementwise absolute value of a secret shared array.

        Note
        ----
        This is a collective operation that *must* be called
        by all players that are members of :attr:`communicator`.

        Parameters
        ----------
        operand: :class:`ActiveArrayShare`, required
            Secret shared value to which the absolute value function should be applied.

        Returns
        -------
        value: :class:`ActiveArrayShare`
            Secret-shared elementwise absolute value of `operand`.
        """
        self._assert_unary_compatible(operand, "operand")
        return ActiveArrayShare((
            self.aprotocol.absolute(operand.additive),
            self.sprotocol.absolute(operand.shamir)))


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
        if isinstance(lhs, ActiveArrayShare) and isinstance(rhs, ActiveArrayShare):
            return self.field_add(lhs, rhs)

        # Private-public addition.
        if isinstance(lhs, ActiveArrayShare) and isinstance(rhs, numpy.ndarray):
            return self.field_add(lhs, encoding.encode(rhs, self.field))

        # Public-private addition.
        if isinstance(lhs, numpy.ndarray) and isinstance(rhs, ActiveArrayShare):
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
        operand: :class:`ActiveArrayShare`, required
            Shared secret to be truncated.

        Returns
        -------
        array: :class:`ActiveArrayShare`
            Share of the bit decomposed secret.
        """
        self._assert_unary_compatible(operand, "operand")
        return ActiveArrayShare((
            self.aprotocol.bit_compose(operand.additive),
            self.sprotocol.bit_compose(operand.shamir)))


    def bit_decompose(self, operand, *, bits=None):
        """Decompose operand into shares of its bitwise representation.

        Note
        ----
        The operand *must* be encoded with FixedFieldEncoder.  The result will
        have one more dimension than the operand, containing the returned bits
        in big-endian order.

        Parameters
        ----------
        operand: :class:`ActiveArrayShare`, required
            Shared secret to be truncated.

        Returns
        -------
        array: :class:`ActiveArrayShare`
            Share of the bit decomposed secret.
        """
        self._assert_unary_compatible(operand, "operand")
        return ActiveArrayShare((
            self.aprotocol.bit_decompose(operand.additive, bits=bits),
            self.sprotocol.bit_decompose(operand.shamir, bits=bits)))


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
        lhs: :class:`ActiveArrayShare`, required
            Secret shared array.
        rhs: :class:`ActiveArrayShare`, required
            Secret shared array.

        Returns
        -------
        result: :class:`ActiveArrayShare`
            Secret-shared elementwise division of `lhs` and `rhs`.
        """
        encoding = self._require_encoding(encoding)

        # Private-private division.
        if isinstance(lhs, ActiveArrayShare) and isinstance(rhs, ActiveArrayShare):
            fieldbits = self.field.fieldbits
            truncbits = encoding.precision
            tbm, tshare = self.random_bitwise_secret(bits=truncbits, shape=rhs.additive.storage.shape)

            tbm, mask1 = self.random_bitwise_secret(bits=truncbits, shape=rhs.additive.storage.shape)
            tbm, rem1 = self.random_bitwise_secret(bits=fieldbits-truncbits, shape=rhs.additive.storage.shape)
            tbm, mask2 = self.random_bitwise_secret(bits=truncbits, shape=rhs.additive.storage.shape)
            tbm, rem2 = self.random_bitwise_secret(bits=fieldbits-truncbits, shape=rhs.additive.storage.shape)
            rev = self.reveal(tshare)
            resa = self.aprotocol.divide(
                lhs.additive,
                rhs.additive,
                encoding=encoding,
                rmask=tshare.additive,
                mask1=mask1.additive,
                rem1=rem1.additive,
                mask2=mask2.additive,
                rem2=rem2.additive,
                )
            ress = self.sprotocol.divide(
                lhs.shamir,
                rhs.shamir,
                encoding=encoding,
                rmask=tshare.shamir,
                mask1=mask1.shamir,
                rem1=rem1.shamir,
                mask2=mask2.shamir,
                rem2=rem2.shamir,
                )
            return ActiveArrayShare((resa, ress))

        # Private-public division.
        if isinstance(lhs, ActiveArrayShare) and isinstance(rhs, numpy.ndarray):
            divisor = encoding.encode(numpy.array(1 / rhs), self.field)
            result = self.field_multiply(lhs, divisor)
            result = self.right_shift(result, bits=encoding.precision)
            return result

        # Public-private division.
        if isinstance(lhs, numpy.ndarray) and isinstance(rhs, ActiveArrayShare):
            pass

        raise NotImplementedError(f"Privacy-preserving division not implemented for the given types: {type(lhs)} and {type(rhs)}.")


    def dot(self, lhs, rhs, *, encoding=None):
        """Return the dot product of two secret shared vectors.

        This is a collective operation that *must* be called
        by all players that are members of :attr:`communicator`.

        Parameters
        ----------
        lhs: :class:`ActiveArrayShare`, required
            Secret shared vector.
        rhs: :class:`ActiveArrayShare`, required
            Secret shared vector.

        Returns
        -------
        result: :class:`ActiveArrayShare`
            Secret-shared dot product of `lhs` and `rhs`.
        """
        self._assert_binary_compatible(lhs, rhs, "lhs", "rhs")
        return ActiveArrayShare((
            self.aprotocol.dot(lhs.additive, rhs.additive, encoding=encoding),
            self.sprotocol.dot(lhs.shamir, rhs.shamir, encoding=encoding)))


    def equal(self, lhs, rhs):
        """Return an elementwise probabilistic equality comparison between secret shared arrays.

        The result is the secret shared elementwise comparison `lhs` == `rhs`.
        This is a collective operation that *must* be called
        by all players that are members of :attr:`communicator`.

        Parameters
        ----------
        lhs: :class:`ActiveArrayShare`, required
            Secret shared value to be compared.
        rhs: :class:`ActiveArrayShare`, required
            Secret shared value to be compared.

        Returns
        -------
        result: :class:`ActiveArrayShare`
            Secret-shared result of computing `lhs` == `rhs` elementwise.
        """
        self._assert_binary_compatible(lhs, rhs, "lhs", "rhs")
        return ActiveArrayShare((
            self.aprotocol.equal(lhs.additive, rhs.additive),
            self.sprotocol.equal(lhs.shamir, rhs.shamir)))


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
        lhs: :class:`ActiveArrayShare`, required
            Secret shared value to be added.
        rhs: :class:`ActiveArrayShare`, required
            Secret shared value to be added.

        Returns
        -------
        value: :class:`ActiveArrayShare`
            Secret-shared sum of `lhs` and `rhs`.
        """
        # Private-private addition.
        if isinstance(lhs, ActiveArrayShare) and isinstance(rhs, ActiveArrayShare):
            return ActiveArrayShare((
                self.aprotocol.field_add(lhs.additive, rhs.additive),
                self.sprotocol.field_add(lhs.shamir, rhs.shamir)))

        # Private-public addition.
        if isinstance(lhs, ActiveArrayShare) and isinstance(rhs, numpy.ndarray):
            return ActiveArrayShare((
                self.aprotocol.field_add(lhs.additive, rhs),
                self.sprotocol.field_add(lhs.shamir, rhs)))

        # Public-private addition.
        if isinstance(lhs, numpy.ndarray) and isinstance(rhs, ActiveArrayShare):
            return ActiveArrayShare((
                self.aprotocol.field_add(lhs, rhs.additive),
                self.sprotocol.field_add(lhs, rhs.shamir)))

        raise NotImplementedError(f"Privacy-preserving addition not implemented for the given types: {type(lhs)} and {type(rhs)}.")


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
        if isinstance(lhs, ActiveArrayShare) and isinstance(rhs, ActiveArrayShare):
            return ActiveArrayShare((
                self.aprotocol.field_multiply(lhs.additive, rhs.additive),
                self.sprotocol.field_multiply(lhs.shamir, rhs.shamir)))

        # Public-private multiplication.
        if isinstance(lhs, numpy.ndarray) and isinstance(rhs, ActiveArrayShare):
            return ActiveArrayShare((
                self.aprotocol.field_multiply(lhs, rhs.additive),
                self.sprotocol.field_multiply(lhs, rhs.shamir)))

        # Private-public multiplication.
        if isinstance(lhs, ActiveArrayShare) and isinstance(rhs, numpy.ndarray):
            return ActiveArrayShare((
                self.aprotocol.field_multiply(lhs.additive, rhs),
                self.sprotocol.field_multiply(lhs.shamir, rhs)))

        raise NotImplementedError(f"Privacy-preserving multiplication not implemented for the given types: {type(lhs)} and {type(rhs)}.")


    def field_power(self, lhs, rhs):
        """Raise the array contained in lhs to the power rshpub on an elementwise basis

        Parameters
        ----------
        lhs: :class:`ActiveArrayShare`, required
            Shared secret to which floor should be applied.
        rhspub: :class:`int`, required
            a publically known integer and the power to which each element in lhs should be raised

        Returns
        -------
        array: :class:`ActiveArrayShare`
            Share of the array elements from lhs all raised to the power rhspub.
        """
        if isinstance(lhs, ActiveArrayShare) and isinstance(rhs, ActiveArrayShare):
            pass

        if isinstance(lhs, ActiveArrayShare) and isinstance(rhs, (numpy.ndarray, int)):
            if isinstance(rhs, int):
                rhs = self.field.full_like(lhs.additive.storage, rhs)
            return ActiveArrayShare((
                self.aprotocol.field_power(lhs.additive, rhs),
                self.sprotocol.field_power(lhs.shamir, rhs)))

        if isinstance(lhs, numpy.ndarray) and isinstance(rhs, ActiveArrayShare):
            pass

        raise NotImplementedError(f"Privacy-preserving exponentiation not implemented for the given types: {type(lhs)} and {type(rhs)}.")


    def field_subtract(self, lhs, rhs):
        """Return the elementwise sum of two secret shared arrays.

        The result is the secret shared elementwise sum of the operands.

        Note
        ----
        This is a collective operation that *must* be called
        by all players that are members of :attr:`communicator`.

        Parameters
        ----------
        lhs: :class:`ActiveArrayShare`, required
            Secret shared value to be added.
        rhs: :class:`ActiveArrayShare`, required
            Secret shared value to be added.

        Returns
        -------
        value: :class:`ActiveArrayShare`
            Secret-shared sum of `lhs` and `rhs`.
        """
        # Private-private subtraction.
        if isinstance(lhs, ActiveArrayShare) and isinstance(rhs, ActiveArrayShare):
            return ActiveArrayShare((
                self.aprotocol.field_subtract(lhs.additive, rhs.additive),
                self.sprotocol.field_subtract(lhs.shamir, rhs.shamir)))

        # Private-public subtraction.
        if isinstance(lhs, ActiveArrayShare) and isinstance(rhs, numpy.ndarray):
            return ActiveArrayShare((
                self.aprotocol.field_subtract(lhs.additive, rhs),
                self.sprotocol.field_subtract(lhs.shamir, rhs)))

        # Public-private subtraction.
        if isinstance(lhs, numpy.ndarray) and isinstance(rhs, ActiveArrayShare):
            return ActiveArrayShare((
                self.aprotocol.field_subtract(lhs, rhs.additive),
                self.sprotocol.field_subtract(lhs, rhs.shamir)))

        raise NotImplementedError(f"Privacy-preserving subtraction not implemented for the given types: {type(lhs)} and {type(rhs)}.")


    def field_uniform(self, *, shape=None, generator=None):
        """Return a ActiveSharedArray with the specified shape and filled with random field elements

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
        secret: :class:`ActiveArrayShare`
            A share of the random generated value.
        """
        uniadd = self.aprotocol.field_uniform(shape=shape, generator=generator)
        shamadd = []
        for i in self.communicator.ranks:
            shamadd.append(self.sprotocol.share(src=i, secret=uniadd.storage, shape=uniadd.storage.shape, encoding=Identity()))
        unisham = ShamirArrayShare(numpy.array(sum([x.storage for x in shamadd]), dtype=self.field.dtype))
        return ActiveArrayShare((uniadd, unisham))


    def floor(self, operand, *, encoding=None):
        """Return the largest integer less-than-or-equal-to `operand`.

        Parameters
        ----------
        operand: :class:`ActiveArrayShare`, required
            Shared secret to which floor should be applied.

        Returns
        -------
        array: :class:`ActiveArrayShare`
            Share of the floor value.
        """
        self._assert_unary_compatible(operand, "operand")
        return ActiveArrayShare((
            self.aprotocol.floor(operand.additive, encoding=encoding),
            self.sprotocol.floor(operand.shamir, encoding=encoding)))


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
        lhs: :class:`ActiveArrayShare`, required
            Secret shared value to be compared.
        rhs: :class:`ActiveArrayShare`, required
            Secret shared value to be compared.

        Returns
        -------
        result: :class:`ActiveArrayShare`
            Secret-shared result of computing `lhs` < `rhs` elementwise.
        """
        self._assert_binary_compatible(lhs, rhs, "lhs", "rhs")
        return ActiveArrayShare((
            self.aprotocol.less(lhs.additive, rhs.additive),
            self.sprotocol.less(lhs.shamir, rhs.shamir)))


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
        operand: :class:`ActiveArrayShare`, required
            Secret shared value to be compared.

        Returns
        -------
        result: :class:`ActiveArrayShare`
            Secret-shared result of computing `operand` < `0` elementwise.
        """
        self._assert_unary_compatible(operand, "operand")
        return ActiveArrayShare((
            self.aprotocol.less_zero(operand.additive),
            self.sprotocol.less_zero(operand.shamir)))


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
        lhs: :class:`ActiveArrayShare`, required
            Secret shared array to be AND'ed.
        rhs: :class:`ActiveArrayShare`, required
            Secret shared array to be AND'ed.

        Returns
        -------
        value: :class:`ActiveArrayShare`
            The secret elementwise logical AND of `lhs` and `rhs`.
        """
        self._assert_binary_compatible(lhs, rhs, "lhs", "rhs")
        return ActiveArrayShare((
            self.aprotocol.logical_and(lhs.additive, rhs.additive),
            self.sprotocol.logical_and(lhs.shamir, rhs.shamir)))


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
        operand: :class:`ActiveArrayShare`, required
            Secret shared array to be negated.

        Returns
        -------
        value: :class:`ActiveArrayShare`
            The secret elementwise logical NOT of `operand`.
        """
        self._assert_unary_compatible(operand, "operand")
        return ActiveArrayShare((
            self.aprotocol.logical_not(operand.additive),
            self.sprotocol.logical_not(operand.shamir)))


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
        lhs: :class:`ActiveArrayShare`, required
            Secret shared array to be OR'd.
        rhs: :class:`ActiveArrayShare`, required
            Secret shared array to be OR'd.

        Returns
        -------
        value: :class:`ActiveArrayShare`
            The secret elementwise logical OR of `lhs` and `rhs`.
        """
        self._assert_binary_compatible(lhs, rhs, "lhs", "rhs")
        return ActiveArrayShare((
            self.aprotocol.logical_or(lhs.additive, rhs.additive),
            self.sprotocol.logical_or(lhs.shamir, rhs.shamir)))


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
        lhs: :class:`ActiveArrayShare`, required
            Secret shared array to be exclusive OR'd.
        rhs: :class:`ActiveArrayShare`, required
            Secret shared array to be exclusive OR'd.

        Returns
        -------
        value: :class:`ActiveArrayShare`
            The secret elementwise logical exclusive OR of `lhs` and `rhs`.
        """
        self._assert_binary_compatible(lhs, rhs, "lhs", "rhs")
        return ActiveArrayShare((
            self.aprotocol.logical_xor(lhs.additive, rhs.additive),
            self.sprotocol.logical_xor(lhs.shamir, rhs.shamir)))


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
        lhs: :class:`ActiveArrayShare`, required
            Secret shared operand.
        rhs: :class:`ActiveArrayShare`, required
            Secret shared operand.

        Returns
        -------
        max: :class:`ActiveArrayShare`
            Secret-shared elementwise maximum of `lhs` and `rhs`.
        """
        self._assert_binary_compatible(lhs, rhs, "lhs", "rhs")
        return ActiveArrayShare((
            self.aprotocol.maximum(lhs.additive, rhs.additive),
            self.sprotocol.maximum(lhs.shamir, rhs.shamir)))


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
        lhs: :class:`ActiveArrayShare`, required
            Secret shared operand.
        rhs: :class:`ActiveArrayShare`, required
            Secret shared operand.

        Returns
        -------
        min: :class:`ActiveArrayShare`
            Secret-shared elementwise minimum of `lhs` and `rhs`.
        """
        self._assert_binary_compatible(lhs, rhs, "lhs", "rhs")
        return ActiveArrayShare((
            self.aprotocol.minimum(lhs.additive, rhs.additive),
            self.sprotocol.minimum(lhs.shamir, rhs.shamir)))


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
        operand: :class:`ActiveArrayShare`, required
            Secret shared array to be multiplicatively inverted.

        Returns
        -------
        value: :class:`ActiveArrayShare`
            The secret multiplicative inverse of operand on an elementwise basis.
        """
        self._assert_unary_compatible(operand, "operand")
        return ActiveArrayShare((
            self.aprotocol.multiplicative_inverse(operand.additive),
            self.sprotocol.multiplicative_inverse(operand.shamir)))


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
        # Private-private multiplication.
        if isinstance(lhs, ActiveArrayShare) and isinstance(rhs, ActiveArrayShare):
            return ActiveArrayShare((
                self.aprotocol.multiply(lhs.additive, rhs.additive, encoding=encoding),
                self.sprotocol.multiply(lhs.shamir, rhs.shamir, encoding=encoding)))

        # Private-public multiplication.
        if isinstance(lhs, ActiveArrayShare) and isinstance(rhs, numpy.ndarray):
            return ActiveArrayShare((
                self.aprotocol.multiply(lhs.additive, rhs, encoding=encoding),
                self.sprotocol.multiply(lhs.shamir, rhs, encoding=encoding)))

        # Public-private multiplication.
        if isinstance(lhs, numpy.ndarray) and isinstance(rhs, ActiveArrayShare):
            return ActiveArrayShare((
                self.aprotocol.multiply(lhs, rhs.additive, encoding=encoding),
                self.sprotocol.multiply(lhs, rhs.shamir, encoding=encoding)))

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
        operand: :class:`ActiveArrayShare`, required
            Secret shared array to be additively inverted.

        Returns
        -------
        value: :class:`ActiveArrayShare`
            The secret additive inverse of operand on an elementwise basis.
        """
        self._assert_unary_compatible(operand, "operand")
        return ActiveArrayShare((
            self.aprotocol.negative(operand.additive),
            self.sprotocol.negative(operand.shamir)))



    def pade_approx(self, func, operand,*, encoding=None, center=0, degree=12, scale=3):
        """Return the pade approximation of func evaluated at operand.

        This is a collective operation that *must* be called
        by all players that are members of :attr:`communicator`.

        Parameters
        ----------
        func: :class:`callable object`, required
            The function to be approximated via the pade method
        center: :class:`float`, required
            The value at which the approximation should be centered. The approximation gets worse the further from this point that the evaulation of the approximation actually occurs
        operand: :class:`AdditiveArrayShare`, required
            The secret share which represents the point at which the function func should be evaluated in a privacy preserving manner

        Returns
        -------
        result: :class:`AdditiveArrayShare`
            Secret shared result of evaluating the pade approximant of func(operand) with the given parameters
        """
        from scipy.interpolate import approximate_taylor_polynomial, pade
        num_deg = degree%2+degree//2
        den_deg = degree//2

        self._assert_unary_compatible(operand, "operand")
        encoding = self._require_encoding(encoding)

        func_taylor = approximate_taylor_polynomial(func, center, degree, scale)
        func_pade_num, func_pade_den = pade([x for x in func_taylor][::-1], den_deg, n=num_deg)
        enc_func_pade_num = encoding.encode(numpy.array([x for x in func_pade_num]), self.field)
        enc_func_pade_den = encoding.encode(numpy.array([x for x in func_pade_den]), self.field)
        op_pows_num_list = [self.share(src=1, secret=numpy.array(1), shape=())]
        for i in range(num_deg):
            op_pows_num_list.append(self.multiply(operand, op_pows_num_list[-1]))
        if degree%2:
            op_pows_den_list=[thing for thing in op_pows_num_list[:-1]]
        else:
            op_pows_den_list=[thing for thing in op_pows_num_list]
        op_pows_num = AdditiveArrayShare(numpy.array([x.storage for x in op_pows_num_list]))
        op_pows_den = AdditiveArrayShare(numpy.array([x.storage for x in op_pows_den_list]))

        result_num_prod = self.field_multiply(op_pows_num, enc_func_pade_num)
        result_num = self.right_shift(self.sum(result_num_prod), bits=encoding.precision)

        result_den_prod = self.field_multiply(op_pows_den, enc_func_pade_den)
        result_den = self.right_shift(self.sum(result_den_prod), bits=encoding.precision)
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
        if isinstance(lhs, ActiveArrayShare) and isinstance(rhs, ActiveArrayShare):
            pass

        if isinstance(lhs, ActiveArrayShare) and isinstance(rhs, (numpy.ndarray, int)):
            if isinstance(rhs, int):
                rhs = self.field.full_like(lhs.storage, rhs)
            return ActiveArrayShare((
                self.aprotocol.power(lhs.additive, rhs),
                self.sprotocol.power(lhs.shamir, rhs)))

        if isinstance(lhs, numpy.ndarray) and isinstance(rhs, ActiveArrayShare):
            pass

        raise NotImplementedError(f"Privacy-preserving exponentiation not implemented for the given types: {type(lhs)} and {type(rhs)}.")


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
        bits: :class:`ActiveArrayShare`
            A share of the randomly-generated bits that make-up the secret.
        secret: :class:`ActiveArrayShare`
            A share of the value defined by `bits` (in big-endian order).
        """
        bs_add, ss_add = self.aprotocol.random_bitwise_secret(bits=bits, src=src, generator=generator, shape=shape)
        shamadd = []
        for i in self.communicator.ranks:
            shamadd.append(self.sprotocol.share(src=i, secret=ss_add.storage, shape=ss_add.storage.shape, encoding=Identity()))
        ss_sham = ShamirArrayShare(numpy.array(sum([x.storage for x in shamadd]), dtype=self.field.dtype))
        shamadd = []
        for i in self.communicator.ranks:
            shamadd.append(self.sprotocol.share(src=i, secret=bs_add.storage, shape=bs_add.storage.shape, encoding=Identity()))
        bs_sham = ShamirArrayShare(numpy.array(sum([x.storage for x in shamadd]), dtype=self.field.dtype))
        return (ActiveArrayShare((bs_add, bs_sham)), ActiveArrayShare((ss_add, ss_sham)))


    def relu(self, operand):
        """Return the elementwise ReLU of a secret shared array.

        Note
        ----
        This is a collective operation that *must* be called
        by all players that are members of :attr:`communicator`.

        Parameters
        ----------
        operand: :class:`ActiveArrayShare`, required
            Secret shared value to which the ReLU function should be applied.

        Returns
        -------
        value: :class:`ActiveArrayShare`
            Secret-shared elementwise ReLU of `operand`.
        """
        self._assert_unary_compatible(operand, "operand")
        return ActiveArrayShare((
            self.aprotocol.relu(operand.additive),
            self.sprotocol.relu(operand.shamir)))


    def reshare(self, operand):
        """Convert a private array to an additive secret share.

        Note
        ----
        This is a collective operation that *must* be called
        by all players that are members of :attr:`communicator`.

        Parameters
        ----------
        operand: :class:`ActiveArrayShare`
            The local share of the secret shared array.

        Returns
        -------
        share: :class:`ActiveArrayShare`
            The local share of the secret shared array, now rerandomized.
        """
        self._assert_unary_compatible(operand, "operand")

        reshared = ActiveArrayShare((
            self.aprotocol.reshare(operand.additive),
            self.sprotocol.reshare(operand.shamir)))

        if not self.verify(reshared):
            raise ConsistencyError("Secret Shares being reshared are inconsistent")

        return reshared


    def reveal(self, share, *, dst=None, encoding=None):
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
        share: :class:`ActiveArrayShare`, required
            The local share of the secret to be revealed.
        dst: sequence of :class:`int`, optional
            List of players who will receive the revealed secret.  If :any:`None`
            (the default), the secret will be revealed to all players.

        Returns
        -------
        value: :class:`numpy.ndarray` or :any:`None`
            Encoded representation of the revealed secret, if this player is a
            member of `dst`, or :any:`None`
        """
        if not isinstance(share, ActiveArrayShare):
            raise ValueError(f"Expected operand to be an instance of ActiveArrayShare, got {type(share)} instead.") # pragma: no cover

        # Identify who will be receiving shares.
        if dst is None:
            dst = self.communicator.ranks

        encoding = self._require_encoding(encoding)

        zshare = ShamirArrayShare(self.sprotocol.field.subtract(share.shamir.storage, numpy.array((pow(self.sprotocol._revealing_coef[self.communicator.rank], self.field.order-2, self.field.order) * share.additive.storage) % self.field.order, dtype=self.field.dtype)))

        a_storage = numpy.array(self.communicator.allgather(share.additive.storage), dtype=self.field.dtype)
        z_storage = numpy.array(self.communicator.allgather(zshare.storage), dtype=self.field.dtype)
        secret = []
        revealing_coef = self.sprotocol._revealing_coef
        for index in numpy.ndindex(z_storage[0].shape):
            secret.append(sum([revealing_coef[i]*z_storage[i][index] for i in range(len(revealing_coef))]))
        rev = numpy.array([x%self.field.order for x in secret], dtype=self.field.dtype).reshape(share.additive.storage.shape)
        if len(rev.shape) == 0 and rev:
            raise ConsistencyError("Secret Shares are inconsistent in the first stage")
        if len(rev.shape) > 0 and numpy.any(rev):
            raise ConsistencyError("Secret Shares are inconsistent in the first stage")

        secret = []
        for index in numpy.ndindex(a_storage[0].shape):
            secret.append(sum([a_storage[i][index] for i in range(len(revealing_coef))]))
        reva = numpy.array([x%self.field.order for x in secret], dtype=self.field.dtype).reshape(share.additive.storage.shape)
        bs_storage=numpy.zeros(z_storage.shape, dtype=self.field.dtype)
        for i, c in enumerate(revealing_coef):
            bs_storage[i] =  self.sprotocol.field.add(z_storage[i], numpy.array((pow(self.sprotocol._revealing_coef[i], self.field.order-2, self.field.order) * a_storage[i]) % self.field.order, dtype=self.field.dtype))
        bs_storage %= self.field.order
        s1 = numpy.sort(numpy.random.choice(self.sprotocol.indices, self.sprotocol._d+1, replace=False))
        revealing_coef = self.sprotocol._lagrange_coef(s1)
        sub_secret = []
        if len(z_storage[0].shape) > 0:
            for index in numpy.ndindex(z_storage[0].shape):
                loop_acc = 0
                for i,v in enumerate(s1):
                    loop_acc += revealing_coef[i]*bs_storage[v-1][index]
                sub_secret.append(loop_acc % self.field.order)
        else:
            loop_acc = 0
            for i,v in enumerate(s1):
                loop_acc += revealing_coef[i]*bs_storage[v-1]
            sub_secret.append(loop_acc % self.field.order)

        revs = numpy.array(sub_secret, dtype=self.field.dtype).reshape(share.additive.storage.shape)
        while True:
            s2 = numpy.sort(numpy.random.choice(self.sprotocol.indices, self.sprotocol._d+1, replace=False))
            if not numpy.array_equal(s1, s2):
                break
        revealing_coef = self.sprotocol._lagrange_coef(s2)
        sub_secret2 = []
        if len(z_storage[0].shape) > 0:
            for index in numpy.ndindex(z_storage[0].shape):
                loop_acc = 0
                for i,v in enumerate(s2):
                    loop_acc += revealing_coef[i]*bs_storage[v-1][index]
                sub_secret2.append(loop_acc % self.field.order)
        else:
            loop_acc = 0
            for i,v in enumerate(s2):
                loop_acc += revealing_coef[i]*bs_storage[v-1]
            sub_secret2.append(loop_acc % self.field.order)

        revs2 = numpy.array(sub_secret2, dtype=self.field.dtype).reshape(share.additive.storage.shape)
        if len(revs.shape) > 0 or len(revs2.shape) > 0:
            if numpy.any(revs != reva) or numpy.any(revs2 != reva):
                raise ConsistencyError("Secret Shares are inconsistent in the second stage")
        else:
            if revs != reva or revs2 != reva:
                raise ConsistencyError("Secret Shares are inconsistent in the second stage")

        return encoding.decode(revs, self.field)


    def right_shift(self, operand, *, bits, src=None, generator=None):
        """Remove the `bits` least significant bits from each element in a secret shared array.

        Note
        ----
        The operand *must* be encoded with FixedFieldEncoder

        Parameters
        ----------
        operand: :class:`ActiveArrayShare`, required
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
        array: :class:`ActiveArrayShare`
            Share of the truncated secret.
        """
        if not isinstance(operand, ActiveArrayShare):
            raise ValueError(f"Expected operand to be an instance of ActiveArrayShare, got {type(operand)} instead.") # pragma: no cover

        tbm, tshare = self.random_bitwise_secret(bits=bits, src=src, generator=generator, shape=operand.additive.storage.shape)
        rbm, rshare = self.random_bitwise_secret(bits=self.field.fieldbits-bits, src=src, generator=generator, shape=operand.additive.storage.shape)
        return ActiveArrayShare((
            self.aprotocol.right_shift(operand.additive, bits=bits, src=src, generator=generator, trunc_mask=tshare.additive, rem_mask=rshare.additive),
            self.sprotocol.right_shift(operand.shamir, bits=bits, src=src, generator=generator, trunc_mask=tshare.shamir, rem_mask=rshare.shamir)))


    def share(self, *, src, secret, shape, encoding=None):
        """Convert a private array to an additive secret share.

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
            The shape of the secret.  Note that the shape must be consistently
            specified by all players.

        Returns
        -------
        share: :class:`ActiveArrayShare`
            The local share of the secret shared array.
        """
        return ActiveArrayShare((
            self.aprotocol.share(src=src, secret=secret, shape=shape, encoding=encoding),
            self.sprotocol.share(src=src, secret=secret, shape=shape, encoding=encoding)))


    def subtract(self, lhs, rhs, *, encoding=None):
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

        # Private-private subtraction.
        if isinstance(lhs, ActiveArrayShare) and isinstance(rhs, ActiveArrayShare):
            return self.field_subtract(lhs, rhs)

        # Private-public subtraction.
        if isinstance(lhs, ActiveArrayShare) and isinstance(rhs, numpy.ndarray):
            return self.field_subtract(lhs, encoding.encode(rhs, self.field))

        # Public-private subtraction.
        if isinstance(lhs, numpy.ndarray) and isinstance(rhs, ActiveArrayShare):
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
        operand: :class:`ActiveArrayShare`, required
            Secret shared array to be summed.

        Returns
        -------
        value: :class:`ActiveArrayShare`
            Secret-shared sum of `operand`'s elements.
        """
        self._assert_unary_compatible(operand, "operand")
        return ActiveArrayShare((
            self.aprotocol.sum(operand.additive),
            self.sprotocol.sum(operand.shamir)))


    def verify(self, operand):
        """Provides a means by which consistency of shares can be checked among all the parties by the use of a ZKP
        This method allows the parties to prove to one another (in zero knowledge) that a consistent set of shares is known by all parties.
        It can provide a 'safe' point at which calculations were known to be good that parties can 'rewind' to if consistency problems are 
        later discovered in the protocol.

        Parameters
        ----------
        operand: :class:`ActiveArrayShare`, required
            Shared secret to have its consistency verified.

        Returns
        -------
        consistency: :class:`bool`
            True if ZKP is successful i.e., everyone has demonstrated that they know consistent shares, and False otherwise.
        """
        self._assert_unary_compatible(operand, "operand")

        a_share = operand.additive
        s_share = operand.shamir
        zero = ShamirArrayShare(self.sprotocol.field.subtract(s_share.storage, numpy.array((pow(self.sprotocol._revealing_coef[self.communicator.rank], self.field.order-2, self.field.order) * a_share.storage) % self.field.order, dtype=object)))
        consistency = numpy.all(self.sprotocol.reveal(zero, encoding=Identity()) == numpy.zeros(zero.storage.shape))
        return consistency



    def taylor_approx(self, func, operand,*, encoding=None, center=0, degree=7, scale=3):

        """Return the taylor approximation of func evaluated at operand.

        This is a collective operation that *must* be called
        by all players that are members of :attr:`communicator`.

        Parameters
        ----------
        func: :class:`callable object`, required
            The function to be approximated via the taylor method
        center: :class:`float`, required
            The value at which the approximation should be centered. The approximation gets worse the further from this point that the evaulation of the approximation actually occurs
        operand: :class:`AdditiveArrayShare`, required
            The secret share which represents the point at which the function func should be evaluated in a privacy preserving manner

        Returns
        -------
        result: :class:`AdditiveArrayShare`
            Secret shared result of evaluating the taylor approximant of func(operand) with the given parameters
        """
        from scipy.interpolate import approximate_taylor_polynomial

        self._assert_unary_compatible(operand, "operand")
        encoding = self._require_encoding(encoding)

        taylor_poly = approximate_taylor_polynomial(func, center, degree, scale)

        enc_taylor_coef = encoding.encode(numpy.array([x for x in taylor_poly]), self.field)
        op_pow_list = [self.share(src=1, secret=numpy.array(1), shape=())]
        for i in range(degree):
            op_pow_list.append(self.multiply(operand, op_pow_list[-1]))

        op_pow_shares = AdditiveArrayShare(numpy.array([x.storage for x in op_pow_list]))

        result = self.field_multiply(op_pow_shares, enc_taylor_coef)
        result = self.sum(result)
        result = self.right_shift(result, bits=encoding.precision)
        return result



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
        operand: :class:`ActiveArrayShare`, required
            Secret shared value to which the zigmoid function should be applied.

        Returns
        -------
        value: :class:`ActiveArrayShare`
            Secret-shared elementwise zigmoid of `operand`.
        """
        self._assert_unary_compatible(operand, "operand")
        return ActiveArrayShare((
            self.aprotocol.zigmoid(operand.additive, encoding=encoding),
            self.sprotocol.zigmoid(operand.shamir, encoding=encoding)))

