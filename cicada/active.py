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
from math import ceil

import numpy

from cicada.communicator.interface import Communicator
import cicada.encoder
import cicada.additive
import cicada.shamir
import random

class ActiveArrayShare(object):
    """Stores the local share of an additive-shared secret array.

    Parameters
    ----------
    storage: :class:`numpy.ndarray`, required
        Local additive share of a secret array, which *must* have been encoded
        using :class:`cicada.encoder.fixedfield.FixedFieldEncoder`.
    """
    def __init__(self, storage):
        self.storage = storage


    def __repr__(self):
        return f"cicada.additive.ActiveArrayShare(storage={self._storage})" # pragma: no cover


    def __getitem__(self, index):
        return self.storage[index]


    @property
    def storage(self):
        """Local share of an shared secret array.

        Returns
        -------
        storage: :class:`numpy.ndarray`
            The local additive share of the secret array.  The share is encoded
            using an instance of
            :class:`cicada.encoder.fixedfield.FixedFieldEncoder` which is owned
            by an instance of :class:`ActiveProtocol`, and **must** be used
            for any modifications to the share value.
        """
        return self._storage


    @storage.setter
    def storage(self, storage):
        if not isinstance(storage, tuple) or not isinstance(storage[0].storage, numpy.ndarray) or not isinstance(storage[1].storage, numpy.ndarray):#should this check that the elements are additive and shamir array shares todo?
            raise ValueError(f"Expected storage to be a tuple containing two instances of numpy.ndarray, got {type(storage)} of {type(storage[0])} and {type(storage[1])} instead.") # pragma: no cover
        self._storage = storage


class ConsistencyError(Exception):
    pass

class ActiveProtocol(object):
    """MPC protocol that uses a communicator to share and manipulate shared secrets
        such that active adversaries actions are detected.

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
    def __init__(self, communicator,*, threshold, seed=None, seed_offset=None, modulus=18446744073709551557, precision=16):
        if not isinstance(communicator, Communicator):
            raise ValueError("A Cicada communicator is required.") # pragma: no cover

        # Setup a pseudo-random sharing of zero, using code drawn from
        # https://github.com/facebookresearch/CrypTen/blob/master/crypten/__init__.py

        # Generate random seeds for Generators
        # NOTE: Chosen seed can be any number, but we choose a random 64-bit
        # integer here so other players cannot guess its value.

        # We sometimes get here from a forked process, which causes all players
        # to have the same RNG state. Reset the seed to make sure RNG streams
        # are different for all the players. We use numpy's random generator
        # here since initializing it without a seed will produce different
        # seeds even from forked processes.

        max_threshold = (communicator.world_size+1) // 2
        if threshold > max_threshold:
            min_world_size = (2 * threshold) - 1
            raise ValueError(f"threshold must be <= {max_threshold}, or world_size must be >= {min_world_size}")
        self._communicator = communicator
        self._encoder = cicada.encoder.FixedFieldEncoder(modulus=modulus, precision=precision)
        self.aprotocol = cicada.additive.AdditiveProtocol(communicator=communicator, seed=seed, seed_offset=seed_offset, modulus=modulus, precision=precision)
        self.sprotocol = cicada.shamir.ShamirProtocol(communicator=communicator, seed=seed, seed_offset=seed_offset, modulus=modulus, precision=precision, threshold=threshold)


    def _assert_binary_compatible(self, lhs, rhs, lhslabel, rhslabel):
        self._assert_unary_compatible(lhs, lhslabel)
        self._assert_unary_compatible(rhs, rhslabel)
        if lhs[0].storage.shape != rhs[0].storage.shape :
            raise ValueError(f"{lhslabel} and {rhslabel} additive shares, ActiveShare[0], must be the same shape, got {lhs.storage.shape} and {rhs.storage.shape} instead.") # pragma: no cover
        if lhs[1].storage.shape != rhs[1].storage.shape:
            raise ValueError(f"{lhslabel} and {rhslabel} shamir shares, ActiveShare[1], must be the same shape, got {lhs.storage.shape} and {rhs.storage.shape} instead.") # pragma: no cover


    def _assert_unary_compatible(self, share, label):
        if not isinstance(share, ActiveArrayShare):
            raise ValueError(f"{label} must be an instance of ActiveArrayShare, got {type(share)} instead.") # pragma: no cover


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
        return ActiveArrayShare((self.aprotocol.absolute(operand[0]), self.sprotocol.absolute(operand[1])))


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
        lhs: :class:`ActiveArrayShare`, required
            Secret shared value to be added.
        rhs: :class:`ActiveArrayShare`, required
            Secret shared value to be added.

        Returns
        -------
        value: :class:`ActiveArrayShare`
            Secret-shared sum of `lhs` and `rhs`.
        """
        self._assert_binary_compatible(lhs, rhs, "lhs", "rhs")
        return ActiveArrayShare((self.aprotocol.add(lhs[0], rhs[0]), self.sprotocol.add(lhs[1], rhs[1])))


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
        operand: :class:`ActiveArrayShare`, required
            Secret shared array to be additively inverted.

        Returns
        -------
        value: :class:`ActiveArrayShare`
            The secret additive inverse of operand on an elementwise basis.
        """
        self._assert_unary_compatible(operand, "operand")

        return ActiveArrayShare((self.aprotocol.additive_inverse(operand[0]), self.sprotocol.additive_inverse(operand[1])))

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
        if not isinstance(operand, ActiveArrayShare):
            raise ValueError(f"Expected operand to be an instance of ActiveArrayShare, got {type(operand)} instead.") # pragma: no cover
        return ActiveArrayShare((self.aprotocol.bit_compose(operand[0]), self.sprotocol.bit_compose(operand[1])))

    def bit_decompose(self, operand, num_bits=None):
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
        if not isinstance(operand, ActiveArrayShare):
            raise ValueError(f"Expected operand to be an instance of ActiveArrayShare, got {type(operand)} instead.") # pragma: no cover
        return ActiveArrayShare((self.aprotocol.bit_decompose(operand[0], num_bits), self.sprotocol.bit_decompose(operand[1], num_bits)))

    def check_commit(self, operand):
        if not isinstance(operand, ActiveArrayShare):
            raise ValueError(f"Expected operand to be an instance of ActiveArrayShare, got {type(operand)} instead.") # pragma: no cover
        a_share = operand[0]
        s_share = operand[1]
        zero = cicada.shamir.ShamirArrayShare(self.sprotocol.encoder.subtract(s_share.storage, numpy.array((pow(self.sprotocol._revealing_coef[self.communicator.rank], self.encoder.modulus-2, self.encoder.modulus) * a_share.storage) % self.encoder.modulus, dtype=object)))
        if all(self.sprotocol.reveal(zero) == numpy.zeros(zero.storage.shape)):
            return zero
        else:
            raise ConsistencyError("Secret Shares are inconsistent in the first stage")

    @property
    def communicator(self):
        """Return the :class:`~cicada.communicator.interface.Communicator` used by this protocol."""
        return self._communicator


    def dot(self, lhs, rhs):
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
        result = self.untruncated_multiply(lhs, rhs)
        result = self.sum(result)
        result = self.truncate(result)
        return result


    @property
    def encoder(self):
        """Return the :class:`cicada.encoder.fixedfield.FixedFieldEncoder` used by this protocol."""
        return self._encoder


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
        return ActiveArrayShare((self.aprotocol.equal(lhs[0], rhs[0]), self.sprotocol.equal(lhs[1], rhs[1])))


    def floor(self, operand):
        """Remove the `bits` least significant bits from each element in a secret shared array
            then shift back left so that only the original integer part of 'operand' remains.
k

        Parameters
        ----------
        operand: :class:`ActiveArrayShare`, required
            Shared secret to which floor should be applied.

        Returns
        -------
        array: :class:`ActiveArrayShare`
            Share of the shared integer part of operand.
        """
        if not isinstance(operand, ActiveArrayShare):
            raise ValueError(f"Expected operand to be an instance of ActiveArrayShare, got {type(operand)} instead.") # pragma: no cover
        return ActiveArrayShare((self.aprotocol.floor(operand[0]), self.sprotocol.floor(operand[1])))

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
        return ActiveArrayShare((self.aprotocol.less(lhs[0], rhs[0]), self.sprotocol.less(lhs[1], rhs[1])))


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
        operand: :class:`ActiveArrayShare`, required
            Secret shared value to be compared.

        Returns
        -------
        result: :class:`ActiveArrayShare`
            Secret-shared result of computing `operand` < `0` elementwise.
        """
        if not isinstance(operand, ActiveArrayShare):
            raise ValueError(f"Expected operand to be an instance of ActiveArrayShare, got {type(operand)} instead.") # pragma: no cover
        return ActiveArrayShare((self.aprotocol.less_than_zero(operand[0]), self.sprotocol.less_than_zero(operand[1])))


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
        return ActiveArrayShare((self.aprotocol.logical_and(lhs[0], rhs[0]), self.sprotocol.logical_and(lhs[1], rhs[1])))


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
        if not isinstance(operand, ActiveArrayShare):
            raise ValueError(f"Expected operand to be an instance of ActiveArrayShare, got {type(operand)} instead.") # pragma: no cover
        return ActiveArrayShare((self.aprotocol.logical_not(operand[0]), self.sprotocol.logical_not(operand[1])))


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
        return ActiveArrayShare((self.aprotocol.logical_or(lhs[0], rhs[0]), self.sprotocol.logical_or(lhs[1], rhs[1])))


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
        return ActiveArrayShare((self.aprotocol.logical_xor(lhs[0], rhs[0]), self.sprotocol.logical_xor(lhs[1], rhs[1])))


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
        operand: :class:`ActiveArrayShare`, required
            Secret shared array from which the least significant bits will be extracted

        Returns
        -------
        lsb: :class:`ActiveArrayShare`
            Active shared array containing the elementwise least significant
            bits of `operand`.
        """
        if not isinstance(operand, ActiveArrayShare):
            raise ValueError(f"Expected operand to be an instance of ActiveArrayShare, got {type(operand)} instead.") # pragma: no cover
        return ActiveArrayShare((self.aprotocol._lsb(operand[0]), self.sprotocol._lsb(operand[1])))

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
        return ActiveArrayShare((self.aprotocol.max(lhs[0], rhs[0]), self.sprotocol.max(lhs[1], rhs[1])))


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
        return ActiveArrayShare((self.aprotocol.min(lhs[0], rhs[0]), self.sprotocol.min(lhs[1], rhs[1])))


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
        if not isinstance(operand, ActiveArrayShare):
            raise ValueError(f"Expected operand to be an instance of ActiveArrayShare, got {type(operand)} instead.") # pragma: no cover
        return ActiveArrayShare((self.aprotocol.multiplicative_inverse(operand[0]), self.sprotocol.multiplicative_inverse(operand[1])))


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
        lhs: :class:`ActiveArrayShare`, required
            Secret shared array to act as the dend.
        rhspub: :class:`numpy.ndarray`, required
            Public value to act as divisor, it is assumed to not
            be encoded, but we optionally provide an argument to
            handle the case in which it is

        Returns
        -------
        value: :class:`ActiveArrayShare`
            The secret approximate result of lhs/rhspub on an elementwise basis.
        """
        self._assert_unary_compatible(lhs, "lhs")
        if not enc:
            divisor = self.encoder.encode(numpy.array(1/rhspub))
            rhs_enc = self.encoder.encode(rhspub)
        else:
            divisor = self.encoder.encode(numpy.array(1/self.encoder.decode(rhspub)))
            rhs_enc = rhspub
        quotient = ActiveArrayShare(self.encoder.untruncated_multiply(lhs.storage, divisor))
        quotient = self.truncate(quotient)
        quotient = self.floor(quotient)
        val2subtract = self.truncate(ActiveArrayShare(self.encoder.untruncated_multiply(rhs_enc, quotient.storage)))
        remainder = self.subtract(lhs, val2subtract)
        print(f'div: {divisor} rhs_enc: {rhs_enc}, q: {self.encoder.decode(self.reveal(quotient))}')
        return remainder


    def private_public_power(self, lhs, rhspub):
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
        if not isinstance(lhs, ActiveArrayShare):
            raise ValueError(f"Expected operand to be an instance of ActiveArrayShare, got {type(operand)} instead.") # pragma: no cover
        return ActiveArrayShare((self.aprotocol.private_public_power(lhs[0], rhspub), self.sprotocol.private_public_power(lhs[1], rhspub)))


    def private_public_power_field(self, lhs, rhspub):
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
        if not isinstance(lhs, ActiveArrayShare):
            raise ValueError(f"Expected operand to be an instance of ActiveArrayShare, got {type(operand)} instead.") # pragma: no cover
        return ActiveArrayShare((self.aprotocol.private_public_power_field(lhs[0], rhspub), self.sprotocol.private_public_power_field(lhs[1], rhspub)))

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
        lhs: :class:`ActiveArrayShare`, required
            Secret shared value from which rhs should be subtracted.
        rhs: :class:`numpy.ndarray`, required
            Public value, which must have been encoded with this protocol's
            :attr:`encoder`.

        Returns
        -------
        value: :class:`ActiveArrayShare`
            The secret shared difference `lhs` - `rhs`.
        """
        self._assert_unary_compatible(lhs, "lhs")

        return ActiveArrayShare((self.aprotocol.private_public_subtract(lhs[0], rhs), self.sprotocol.private_public_subtract(lhs[1], rhs)))


    def _public_bitwise_less_than(self,*, lhspub, rhs):
        """Comparison Operator

        Parameters
        ----------
        lhs: :class:`ndarray`, required
            a publically known numpy array of integers and one of the two objects to be compared
        rhs: :class:`ActiveArrayShare`, required 
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
        self._assert_unary_compatible(rhs, "rhs")
        return ActiveArrayShare((self.aprotocol._public_bitwise_less_than(lhspub, rhs[0]), self.sprotocol._public_bitwise_less_than(lhspub, rhs[1])))


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
        rhs: :class:`ActiveArrayShare`, required
            Secret shared value to be added.

        Returns
        -------
        value: :class:`ActiveArrayShare`
            The secret shared sum of `lhs` and `rhs`.
        """
        self._assert_unary_compatible(rhs, "rhs")
        return ActiveArrayShare((self.aprotocol.public_private_add(lhs, rhs[0]), self.sprotocol.public_private_add(lhs, rhs[1])))


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
        rhs: :class:`ActiveArrayShare`, required
            Secret shared value to be subtracted.

        Returns
        -------
        value: :class:`ActiveArrayShare`
            The secret shared difference `lhs` - `rhs`.
        """
        self._assert_unary_compatible(lhs, "lhs")
        return ActiveArrayShare((self.aprotocol.public_private_subtract(lhs, rhs[0]), self.sprotocol.public_private_subtract(lhs, rhs[1])))


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
            shamadd.append(self.sprotocol.share(src=i, secret=ss_add.storage, shape=ss_add.storage.shape))
        ss_sham = cicada.shamir.ShamirArrayShare(numpy.array(sum([x.storage for x in shamadd]), dtype=self.encoder.dtype))
        shamadd = []
        for i in self.communicator.ranks:
            shamadd.append(self.sprotocol.share(src=i, secret=bs_add.storage, shape=bs_add.storage.shape))
        bs_sham = cicada.shamir.ShamirArrayShare(numpy.array(sum([x.storage for x in shamadd]), dtype=self.encoder.dtype))
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
        if not isinstance(operand, ActiveArrayShare):
            raise ValueError(f"Expected operand to be an instance of ActiveArrayShare, got {type(operand)} instead.") # pragma: no cover
        return ActiveArrayShare((self.aprotocol.relu(operand[0]), self.sprotocol.relu(operand[1])))

    def reshare(self, *, operand):
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

        if not isinstance(operand, ActiveArrayShare):
            raise ValueError(f"Expected operand to be an instance of ActiveArrayShare, got {type(operand)} instead.") # pragma: no cover
        return ActiveArrayShare((self.aprotocol.reshare(operand=operand[0]), self.sprotocol.reshare(operand=operand[1])))

    def reveal(self, share, dst=None):
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
        zshare =  cicada.shamir.ShamirArrayShare(self.sprotocol.encoder.subtract(share[1].storage, numpy.array((pow(self.sprotocol._revealing_coef[self.communicator.rank], self.encoder.modulus-2, self.encoder.modulus) * share[0].storage) % self.encoder.modulus, dtype=self.encoder.dtype)))
        
        a_storage = numpy.array(self.communicator.allgather(share[0].storage), dtype=self.encoder.dtype)
        z_storage = numpy.array(self.communicator.allgather(zshare.storage), dtype=self.encoder.dtype)
        secret = []
        revealing_coef = self.sprotocol._revealing_coef 
        for index in numpy.ndindex(z_storage[0].shape):
            secret.append(sum([revealing_coef[i]*z_storage[i][index] for i in range(len(revealing_coef))]))
        rev = numpy.array([x%self.encoder.modulus for x in secret], dtype=self.encoder.dtype).reshape(share[0].storage.shape)
        if len(rev.shape) == 0 and rev:
            #print(f's: {self.sprotocol.reveal(share[1])}\na: {self.aprotocol.reveal(share[0])}')
            raise ConsistencyError("Secret Shares are inconsistent in the first stage")
        if len(rev.shape) > 0 and numpy.any(rev):
            #print(f's: {self.sprotocol.reveal(share[1])}\na: {self.aprotocol.reveal(share[0])}')
            raise ConsistencyError("Secret Shares are inconsistent in the first stage")

        secret = []
        for index in numpy.ndindex(a_storage[0].shape):
            secret.append(sum([a_storage[i][index] for i in range(len(revealing_coef))]))
        reva = numpy.array([x%self.encoder.modulus for x in secret], dtype=self.encoder.dtype).reshape(share[0].storage.shape)
        bs_storage=numpy.zeros(z_storage.shape, dtype=self.encoder.dtype)
        for i, c in enumerate(revealing_coef):
            bs_storage[i] =  self.sprotocol.encoder.add(z_storage[i], numpy.array((pow(self.sprotocol._revealing_coef[i], self.encoder.modulus-2, self.encoder.modulus) * a_storage[i]) % self.encoder.modulus, dtype=self.encoder.dtype))
        bs_storage %= self.encoder.modulus
        s1 = random.sample(list(self.sprotocol._indices), self.sprotocol._d+1)
        s1.sort()
        revealing_coef = self.sprotocol._lagrange_coef(s1)
        sub_secret = []
        if len(z_storage[0].shape) > 0:
            for index in numpy.ndindex(z_storage[0].shape):
                loop_acc = 0
                for i,v in enumerate(s1):
                    loop_acc += revealing_coef[i]*bs_storage[v-1][index] # TODO Problem arises in 0d shared array
                sub_secret.append(loop_acc % self.encoder.modulus)
                #sub_secret.append(sum([(revealing_coef[i]*bs_storage[v-1][index]) % self.encoder.modulus for i,v in enumerate(s1)]))
        else:
            loop_acc = 0
            for i,v in enumerate(s1):
                loop_acc += revealing_coef[i]*bs_storage[v-1]
            sub_secret.append(loop_acc % self.encoder.modulus)

        revs = numpy.array(sub_secret, dtype=self.encoder.dtype).reshape(share[0].storage.shape)
        s2 = random.sample(list(self.sprotocol._indices), self.sprotocol._d+1)
        s2.sort()
        while s2 == s1:
            s2 = random.sample(list(self.sprotocol._indices), self.sprotocol._d+1)
            s2.sort()
        revealing_coef = self.sprotocol._lagrange_coef(s2)
        sub_secret2 = []
        if len(z_storage[0].shape) > 0:
            for index in numpy.ndindex(z_storage[0].shape):
                loop_acc = 0
                for i,v in enumerate(s2):
                    loop_acc += revealing_coef[i]*bs_storage[v-1][index]
                sub_secret2.append(loop_acc % self.encoder.modulus)
        else:
            loop_acc = 0
            for i,v in enumerate(s2):
                loop_acc += revealing_coef[i]*bs_storage[v-1]
            sub_secret2.append(loop_acc % self.encoder.modulus)

        revs2 = numpy.array(sub_secret2, dtype=self.encoder.dtype).reshape(share[0].storage.shape)
        if len(revs.shape) > 0 or len(revs2.shape) > 0:
            if numpy.any(revs != reva) or numpy.any(revs2 != reva):
                #print(reva, revs, revs2)
                raise ConsistencyError("Secret Shares are inconsistent in the second stage")
        else:
            if revs != reva or revs2 != reva:
                raise ConsistencyError("Secret Shares are inconsistent in the second stage")
        return revs
            

    def share(self, *, src, secret, shape):
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
            The secret array to be shared, which must be encoded with this
            object's :attr:`encoder`.  This value is ignored for all players
            except `src`.
        shape: :class:`tuple`, required
            The shape of the secret.  Note that the shape must be consistently
            specified by all players.

        Returns
        -------
        share: :class:`ActiveArrayShare`
            The local share of the secret shared array.
        """
        if not isinstance(shape, tuple):
            shape = (shape,)

        if self.communicator.rank == src:
            if not isinstance(secret, numpy.ndarray):
                raise ValueError("secret must be an instance of numpy.ndarray.") # pragma: no cover
            if secret.dtype != self.encoder.dtype:
                raise ValueError("secret must be encoded by this protocol's encoder.") # pragma: no cover
            if secret.shape != shape:
                raise ValueError(f"secret.shape must match shape parameter.  Expected {secret.shape}, got {shape} instead.") # pragma: no cover

        return ActiveArrayShare((self.aprotocol.share(src=src, secret=secret, shape=shape), self.sprotocol.share(src=src, secret=secret, shape=shape)))


    def subtract(self, lhs, rhs):
        """Subtract a secret shared value from a secret shared value.

        Note
        ----
        This is a collective operation that *must* be called
        by all players that are members of :attr:`communicator`.

        Parameters
        ----------
        lhs: :class:`ActiveArrayShare`, required
            Shared value.
        rhs: :class:`ActiveArrayShare`, required
            Shared value to be subtracted.

        Returns
        -------
        value: :class:`ActiveArrayShare`
            The difference `lhs` - `rhs`.
        """
        self._assert_binary_compatible(lhs, rhs, "lhs", "rhs")
        return ActiveArrayShare((self.aprotocol.subtract(lhs[0], rhs[0]), self.sprotocol.subtract(lhs[1], rhs[1])))


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
        return ActiveArrayShare((self.aprotocol.sum(operand[0]), self.sprotocol.sum(operand[1])))


    def truncate(self, operand, *, bits=None, src=None, generator=None):
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
        if bits is None:
            bits = self.encoder.precision
        tbm, tshare = self.random_bitwise_secret(bits=bits, src=src, generator=generator, shape=operand[0].storage.shape)
        rbm, rshare = self.random_bitwise_secret(bits=self.encoder.fieldbits-bits, src=src, generator=generator, shape=operand[0].storage.shape)
        atbm = tshare[0]
        stbm = tshare[1]
        arbm = rshare[0]
        srbm = rshare[1]

        return ActiveArrayShare((self.aprotocol.truncate(operand[0], bits=bits, src=src, generator=generator, trunc_mask=atbm, rem_mask=arbm), self.sprotocol.truncate(operand[1], bits=bits, src=src, generator=generator, trunc_mask=stbm, rem_mask=srbm)))



    def uniform(self, *, shape=None, generator=None):
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
    # TODO should the shares from both schemes match? YES!!!

        uniadd = self.aprotocol.uniform(shape=shape, generator=generator)
        shamadd = []
        for i in self.communicator.ranks:
            shamadd.append(self.sprotocol.share(src=i, secret=uniadd.storage, shape=uniadd.storage.shape))
        unisham = cicada.shamir.ShamirArrayShare(numpy.array(sum([x.storage for x in shamadd]), dtype=self.encoder.dtype))
        return (uniadd, unisham)

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
        lhs: :class:`ActiveArrayShare`, required
            secret value to be multiplied.
        rhs: :class:`ActiveArrayShare`, required
            secret value to be multiplied.

        Returns
        -------
        value: :class:`ActiveArrayShare`
            The secret elementwise product of `lhs` and `rhs`.
        """
        self._assert_binary_compatible(lhs, rhs, "lhs", "rhs")
        return ActiveArrayShare((self.aprotocol.untruncated_multiply(lhs[0], rhs[0]), self.sprotocol.untruncated_multiply(lhs[1], rhs[1])))


    def untruncated_divide(self, lhs, rhs):
        """Element-wise division of private values. Note: this may have a chance to leak info is the secret contained in rhs is 
        close to or bigger than 2^precision

        Note
        ----
        This is a collective operation that *must* be called
        by all players that are members of :attr:`communicator`.

        Parameters
        ----------
        lhs: :class:`ActiveArrayShare`, required
            Secret shared array dividend.
        rhs: :class:`numpy.ndarray`, required
            Public array divisor, which must *not* be encoded.

        Returns
        -------
        value: :class:`ActiveArrayShare`
            The secret element-wise result of lhs / rhs.
        """
        self._assert_binary_compatible(lhs, rhs, "lhs", "rhs")
        bits = self.encoder.precision
        tbm, tshare = self.random_bitwise_secret(bits=bits, shape=rhs[0].storage.shape)
        atbm = tshare[0]
        stbm = tshare[1]
        return ActiveArrayShare((self.aprotocol.untruncated_divide(lhs[0], rhs[0], atbm), self.sprotocol.untruncated_divide(lhs[1], rhs[1],stbm)))


    def untruncated_private_public_divide(self, lhs, rhs):
        """Element-wise division of private and public values.

        Note
        ----
        This is a collective operation that *must* be called
        by all players that are members of :attr:`communicator`.

        Parameters
        ----------
        lhs: :class:`ActiveArrayShare`, required
            Secret shared array dividend.
        rhs: :class:`numpy.ndarray`, required
            Public array divisor, which must *not* be encoded.

        Returns
        -------
        value: :class:`ActiveArrayShare`
            The secret element-wise result of lhs / rhs.
        """
        self._assert_unary_compatible(lhs, "lhs")
        return ActiveArrayShare((self.aprotocol.untruncated_private_public_divide(lhs[0], rhs), self.sprotocol.untruncated_private_public_divide(lhs[1], rhs)))

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
        operand: :class:`ActiveArrayShare`, required
            Secret shared value to which the zigmoid function should be applied.

        Returns
        -------
        value: :class:`ActiveArrayShare`
            Secret-shared elementwise zigmoid of `operand`.
        """
        if not isinstance(operand, ActiveArrayShare):
            raise ValueError(f"Expected operand to be an instance of ActiveArrayShare, got {type(operand)} instead.") # pragma: no cover
        return ActiveArrayShare((self.aprotocol.zigmoid(operand[0]), self.sprotocol.zigmoid(operand[1])))
