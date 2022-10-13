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
    """Stores the local share of a shared secret array for the Active protocol suite.

    Parameters
    ----------
    storage: tuple(:class:`numpy.ndarray`, :class:`numpy.ndarray`), required
        Local share of a secret array.
    """
    def __init__(self, storage):
        self.storage = storage


    def __repr__(self):
        return f"cicada.active.ActiveArrayShare(storage={self._storage})" # pragma: no cover


    def __getitem__(self, index):
        return ActiveArrayShare((cicada.additive.AdditiveArrayShare(self.additive_subshare.storage[index]), cicada.shamir.ShamirArrayShare(self.shamir_subshare.storage[index])))
                

    @property
    def storage(self):
        """Local share of an shared secret array.

        Returns
        -------
        storage: :class:`object`
            Private storage for the local share of a secret array created by
            the active protocol suite.  Access is provided only for
            serialization and communication - callers must use
            :class:`ActiveProtocolSuite` to manipulate secret shares.
        """
        return self._storage

    @property
    def additive_subshare(self):
        """Local share of an shared secret array.

        Returns
        -------
        storage: :class:`object`
            Private storage for the local share of a secret array created by
            the active protocol suite.  Access is provided only for
            serialization and communication - callers must use
            :class:`ActiveProtocolSuite` to manipulate secret shares.
        """
        return self._storage[0]

    @property
    def shamir_subshare(self):
        """Local share of an shared secret array.

        Returns
        -------
        storage: :class:`object`
            Private storage for the local share of a secret array created by
            the active protocol suite.  Access is provided only for
            serialization and communication - callers must use
            :class:`ActiveProtocolSuite` to manipulate secret shares.
        """
        return self._storage[1]

    @storage.setter
    def storage(self, storage):
        if not len(storage) == 2:
            raise ValueError(f"Expected instances of AdditiveArrayShare and ShamirArrayShare, got {storage} instead.") # pragma: no cover
        if not isinstance(storage[0], cicada.additive.AdditiveArrayShare):
            raise ValueError(f"Expected instances of AdditiveArrayShare and ShamirArrayShare, got {storage} instead.") # pragma: no cover
        if not isinstance(storage[1], cicada.shamir.ShamirArrayShare):
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
        self.aprotocol = cicada.additive.AdditiveProtocolSuite(communicator=communicator, seed=seed, seed_offset=seed_offset, modulus=modulus, precision=precision)
        self.sprotocol = cicada.shamir.ShamirProtocolSuite(communicator=communicator, seed=seed, seed_offset=seed_offset, modulus=modulus, precision=precision, threshold=threshold)


    def _assert_binary_compatible(self, lhs, rhs, lhslabel, rhslabel):
        self._assert_unary_compatible(lhs, lhslabel)
        self._assert_unary_compatible(rhs, rhslabel)
        if lhs.additive_subshare.storage.shape != rhs.additive_subshare.storage.shape :
            raise ValueError(f"{lhslabel} and {rhslabel} additive shares, the additive subshares must be the same shape, got {lhs.additive_subshare.storage.shape} and {rhs.additive_subshare.storage.shape} instead.") # pragma: no cover
        if lhs.shamir_subshare.storage.shape != rhs.shamir_subshare.storage.shape:
            raise ValueError(f"{lhslabel} and {rhslabel} shamir shares, the Shamir subshares must be the same shape, got {lhs.shamir_subshare.storage.shape} and {rhs.shamir_subshare.storage.shape} instead.") # pragma: no cover


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
        return ActiveArrayShare((self.aprotocol.absolute(operand.additive_subshare), self.sprotocol.absolute(operand.shamir_subshare)))


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
        return ActiveArrayShare((self.aprotocol.add(lhs.additive_subshare, rhs.additive_subshare), self.sprotocol.add(lhs.shamir_subshare, rhs.shamir_subshare)))


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

        return ActiveArrayShare((self.aprotocol.additive_inverse(operand.additive_subshare), self.sprotocol.additive_inverse(operand.shamir_subshare)))

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
        return ActiveArrayShare((self.aprotocol.bit_compose(operand.additive_subshare), self.sprotocol.bit_compose(operand.shamir_subshare)))

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
        return ActiveArrayShare((self.aprotocol.bit_decompose(operand.additive_subshare, num_bits), self.sprotocol.bit_decompose(operand.shamir_subshare, num_bits)))

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
        if not isinstance(operand, ActiveArrayShare):
            raise ValueError(f"Expected operand to be an instance of ActiveArrayShare, got {type(operand)} instead.") # pragma: no cover
        a_share = operand.additive_subshare
        s_share = operand.shamir_subshare
        zero = cicada.shamir.ShamirArrayShare(self.sprotocol._encoder.subtract(s_share.storage, numpy.array((pow(self.sprotocol._revealing_coef[self.communicator.rank], self._encoder.modulus-2, self._encoder.modulus) * a_share.storage) % self._encoder.modulus, dtype=object)))
        consistency = numpy.all(self.sprotocol._reveal(zero) == numpy.zeros(zero.storage.shape))
        return consistency

    @property
    def communicator(self):
        """Return the :class:`~cicada.communicator.interface.Communicator` used by this protocol."""
        return self._communicator


    def divide(self, lhs, rhs):
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
        self._assert_binary_compatible(lhs, rhs, "lhs", "rhs")
        result = self.untruncated_divide(lhs, rhs)
        result = self.truncate(result)
        return result


    def dot(self, lhs, rhs):
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
        result = self.untruncated_multiply(lhs, rhs)
        result = self.sum(result)
        result = self.truncate(result)
        return result


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
        return ActiveArrayShare((self.aprotocol.equal(lhs.additive_subshare, rhs.additive_subshare), self.sprotocol.equal(lhs.shamir_subshare, rhs.shamir_subshare)))


    def floor(self, operand):
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
        if not isinstance(operand, ActiveArrayShare):
            raise ValueError(f"Expected operand to be an instance of ActiveArrayShare, got {type(operand)} instead.") # pragma: no cover
        return ActiveArrayShare((self.aprotocol.floor(operand.additive_subshare), self.sprotocol.floor(operand.shamir_subshare)))


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
        return ActiveArrayShare((self.aprotocol.less(lhs.additive_subshare, rhs.additive_subshare), self.sprotocol.less(lhs.shamir_subshare, rhs.shamir_subshare)))


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
        return ActiveArrayShare((self.aprotocol.less_than_zero(operand.additive_subshare), self.sprotocol.less_than_zero(operand.shamir_subshare)))


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
        return ActiveArrayShare((self.aprotocol.logical_and(lhs.additive_subshare, rhs.additive_subshare), self.sprotocol.logical_and(lhs.shamir_subshare, rhs.shamir_subshare)))


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
        return ActiveArrayShare((self.aprotocol.logical_not(operand.additive_subshare), self.sprotocol.logical_not(operand.shamir_subshare)))


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
        return ActiveArrayShare((self.aprotocol.logical_or(lhs.additive_subshare, rhs.additive_subshare), self.sprotocol.logical_or(lhs.shamir_subshare, rhs.shamir_subshare)))


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
        return ActiveArrayShare((self.aprotocol.logical_xor(lhs.additive_subshare, rhs.additive_subshare), self.sprotocol.logical_xor(lhs.shamir_subshare, rhs.shamir_subshare)))


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
        return ActiveArrayShare((self.aprotocol.max(lhs.additive_subshare, rhs.additive_subshare), self.sprotocol.max(lhs.shamir_subshare, rhs.shamir_subshare)))


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
        return ActiveArrayShare((self.aprotocol.min(lhs.additive_subshare, rhs.additive_subshare), self.sprotocol.min(lhs.shamir_subshare, rhs.shamir_subshare)))


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
        return ActiveArrayShare((self.aprotocol.multiplicative_inverse(operand.additive_subshare), self.sprotocol.multiplicative_inverse(operand.shamir_subshare)))


    def multiply(self, lhs, rhs):
        """Return the elementwise product of two secret shared arrays.

        This is a collective operation that *must* be called
        by all players that are members of :attr:`communicator`.

        Parameters
        ----------
        lhs: :class:`ActiveArrayShare`, required
            Secret shared arrays.
        rhs: :class:`ActiveArrayShare`, required
            Secret shared arrays.

        Returns
        -------
        result: :class:`ActiveArrayShare`
            Secret-shared elementwise product of `lhs` and `rhs`.
        """
        self._assert_binary_compatible(lhs, rhs, "lhs", "rhs")
        result = self.untruncated_multiply(lhs, rhs)
        result = self.truncate(result)
        return result


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
        return ActiveArrayShare((self.aprotocol.private_public_power(lhs.additive_subshare, rhspub), self.sprotocol.private_public_power(lhs.shamir_subshare, rhspub)))


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
        return ActiveArrayShare((self.aprotocol.private_public_power_field(lhs.additive_subshare, rhspub), self.sprotocol.private_public_power_field(lhs.shamir_subshare, rhspub)))

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

        return ActiveArrayShare((self.aprotocol.private_public_subtract(lhs.additive_subshare, rhs), self.sprotocol.private_public_subtract(lhs.shamir_subshare, rhs)))


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
            shamadd.append(self.sprotocol._share(src=i, secret=ss_add.storage, shape=ss_add.storage.shape))
        ss_sham = cicada.shamir.ShamirArrayShare(numpy.array(sum([x.storage for x in shamadd]), dtype=self._encoder.dtype))
        shamadd = []
        for i in self.communicator.ranks:
            shamadd.append(self.sprotocol._share(src=i, secret=bs_add.storage, shape=bs_add.storage.shape))
        bs_sham = cicada.shamir.ShamirArrayShare(numpy.array(sum([x.storage for x in shamadd]), dtype=self._encoder.dtype))
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
        return ActiveArrayShare((self.aprotocol.relu(operand.additive_subshare), self.sprotocol.relu(operand.shamir_subshare)))

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
        reshared = ActiveArrayShare((self.aprotocol.reshare(operand=operand.additive_subshare), self.sprotocol.reshare(operand=operand.shamir_subshare)))
        if self.verify(reshared):
            return reshared
        else:
            raise ConsistencyError("Secret Shares being reshared are inconsistent")
        

    def _reveal(self, share, dst=None):
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
        zshare = cicada.shamir.ShamirArrayShare(self.sprotocol._encoder.subtract(share.shamir_subshare.storage, numpy.array((pow(self.sprotocol._revealing_coef[self.communicator.rank], self._encoder.modulus-2, self._encoder.modulus) * share.additive_subshare.storage) % self._encoder.modulus, dtype=self._encoder.dtype)))

        a_storage = numpy.array(self.communicator.allgather(share.additive_subshare.storage), dtype=self._encoder.dtype)
        z_storage = numpy.array(self.communicator.allgather(zshare.storage), dtype=self._encoder.dtype)
        secret = []
        revealing_coef = self.sprotocol._revealing_coef
        for index in numpy.ndindex(z_storage[0].shape):
            secret.append(sum([revealing_coef[i]*z_storage[i][index] for i in range(len(revealing_coef))]))
        rev = numpy.array([x%self._encoder.modulus for x in secret], dtype=self._encoder.dtype).reshape(share.additive_subshare.storage.shape)
        if len(rev.shape) == 0 and rev:
            raise ConsistencyError("Secret Shares are inconsistent in the first stage")
        if len(rev.shape) > 0 and numpy.any(rev):
            raise ConsistencyError("Secret Shares are inconsistent in the first stage")

        secret = []
        for index in numpy.ndindex(a_storage[0].shape):
            secret.append(sum([a_storage[i][index] for i in range(len(revealing_coef))]))
        reva = numpy.array([x%self._encoder.modulus for x in secret], dtype=self._encoder.dtype).reshape(share.additive_subshare.storage.shape)
        bs_storage=numpy.zeros(z_storage.shape, dtype=self._encoder.dtype)
        for i, c in enumerate(revealing_coef):
            bs_storage[i] =  self.sprotocol._encoder.add(z_storage[i], numpy.array((pow(self.sprotocol._revealing_coef[i], self._encoder.modulus-2, self._encoder.modulus) * a_storage[i]) % self._encoder.modulus, dtype=self._encoder.dtype))
        bs_storage %= self._encoder.modulus
        s1 = random.sample(list(self.sprotocol._indices), self.sprotocol._d+1)
        s1.sort()
        revealing_coef = self.sprotocol._lagrange_coef(s1)
        sub_secret = []
        if len(z_storage[0].shape) > 0:
            for index in numpy.ndindex(z_storage[0].shape):
                loop_acc = 0
                for i,v in enumerate(s1):
                    loop_acc += revealing_coef[i]*bs_storage[v-1][index]
                sub_secret.append(loop_acc % self._encoder.modulus)
        else:
            loop_acc = 0
            for i,v in enumerate(s1):
                loop_acc += revealing_coef[i]*bs_storage[v-1]
            sub_secret.append(loop_acc % self._encoder.modulus)

        revs = numpy.array(sub_secret, dtype=self._encoder.dtype).reshape(share.additive_subshare.storage.shape)
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
                sub_secret2.append(loop_acc % self._encoder.modulus)
        else:
            loop_acc = 0
            for i,v in enumerate(s2):
                loop_acc += revealing_coef[i]*bs_storage[v-1]
            sub_secret2.append(loop_acc % self._encoder.modulus)

        revs2 = numpy.array(sub_secret2, dtype=self._encoder.dtype).reshape(share.additive_subshare.storage.shape)
        if len(revs.shape) > 0 or len(revs2.shape) > 0:
            if numpy.any(revs != reva) or numpy.any(revs2 != reva):
                raise ConsistencyError("Secret Shares are inconsistent in the second stage")
        else:
            if revs != reva or revs2 != reva:
                raise ConsistencyError("Secret Shares are inconsistent in the second stage")
        return revs


    def reveal(self, share, dst=None):
        """Reveals a secret shared value to a subset of players.

        Note
        ----
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
            The revealed secret, if this player is a member of `dst`, or :any:`None`.
        """
        return self._encoder.decode(self._reveal(share, dst=dst))


    def reveal_bits(self, share, dst=None):
        """Reveals secret shared bits to a subset of players.

        Note
        ----
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
            The revealed secret, if this player is a member of `dst`, or :any:`None`.
        """
        return self._reveal(share, dst=dst).astype(bool).astype(numpy.uint8)


    def reveal_field(self, share, dst=None):
        """Reveals secret shared field values to a subset of players.

        Note
        ----
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
            The revealed secret, if this player is a member of `dst`, or :any:`None`.
        """
        return self._reveal(share, dst=dst)


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
        return ActiveArrayShare((self.aprotocol.share(src=src, secret=secret, shape=shape), self.sprotocol.share(src=src, secret=secret, shape=shape)))


    def share_bits(self, *, src, secret, shape):
        """Convert an array of bits to an active secret share.

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
        return ActiveArrayShare((self.aprotocol.share_bits(src=src, secret=secret, shape=shape), self.sprotocol.share_bits(src=src, secret=secret, shape=shape)))


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
        return ActiveArrayShare((self.aprotocol.subtract(lhs.additive_subshare, rhs.additive_subshare), self.sprotocol.subtract(lhs.shamir_subshare, rhs.shamir_subshare)))


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
        return ActiveArrayShare((self.aprotocol.sum(operand.additive_subshare), self.sprotocol.sum(operand.shamir_subshare)))


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
            bits = self._encoder.precision
        tbm, tshare = self.random_bitwise_secret(bits=bits, src=src, generator=generator, shape=operand.additive_subshare.storage.shape)
        rbm, rshare = self.random_bitwise_secret(bits=self._encoder.fieldbits-bits, src=src, generator=generator, shape=operand.additive_subshare.storage.shape)
        return ActiveArrayShare((self.aprotocol.truncate(operand.additive_subshare, bits=bits, src=src, generator=generator, trunc_mask=tshare.additive_subshare, rem_mask=rshare.additive_subshare), self.sprotocol.truncate(operand.shamir_subshare, bits=bits, src=src, generator=generator, trunc_mask=tshare.shamir_subshare, rem_mask=rshare.shamir_subshare)))



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
        uniadd = self.aprotocol.uniform(shape=shape, generator=generator)
        shamadd = []
        for i in self.communicator.ranks:
            shamadd.append(self.sprotocol._share(src=i, secret=uniadd.storage, shape=uniadd.storage.shape))
        unisham = cicada.shamir.ShamirArrayShare(numpy.array(sum([x.storage for x in shamadd]), dtype=self._encoder.dtype))
        return ActiveArrayShare((uniadd, unisham))

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
        return ActiveArrayShare((self.aprotocol.untruncated_multiply(lhs.additive_subshare, rhs.additive_subshare), self.sprotocol.untruncated_multiply(lhs.shamir_subshare, rhs.shamir_subshare)))


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
        fieldbits = self._encoder.fieldbits
        truncbits = self._encoder.precision
        tbm, tshare = self.random_bitwise_secret(bits=truncbits, shape=rhs.additive_subshare.storage.shape)

        tbm, mask1 = self.random_bitwise_secret(bits=truncbits, shape=rhs.additive_subshare.storage.shape)
        tbm, rem1 = self.random_bitwise_secret(bits=fieldbits-truncbits, shape=rhs.additive_subshare.storage.shape)
        tbm, mask2 = self.random_bitwise_secret(bits=truncbits, shape=rhs.additive_subshare.storage.shape)
        tbm, rem2 = self.random_bitwise_secret(bits=fieldbits-truncbits, shape=rhs.additive_subshare.storage.shape)
        rev = self.reveal(tshare)
        resa = self.aprotocol.untruncated_divide(lhs.additive_subshare, rhs.additive_subshare, tshare.additive_subshare, mask1.additive_subshare, rem1.additive_subshare, mask2.additive_subshare, rem2.additive_subshare)
        ress = self.sprotocol.untruncated_divide(lhs.shamir_subshare, rhs.shamir_subshare,tshare.shamir_subshare, mask1.shamir_subshare, rem1.shamir_subshare, mask2.shamir_subshare, rem2.shamir_subshare)
        return ActiveArrayShare((resa, ress))


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
        return ActiveArrayShare((self.aprotocol.untruncated_private_public_divide(lhs.additive_subshare, rhs), self.sprotocol.untruncated_private_public_divide(lhs.shamir_subshare, rhs)))

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
        return ActiveArrayShare((self.aprotocol.zigmoid(operand.additive_subshare), self.sprotocol.zigmoid(operand.shamir_subshare)))
