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
            ShamirArrayShare(self.shamir.storage[index]))) # pragma: no cover


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
        """Additive secret-shared portion of :attr:`storage`.
        """
        return self._storage[0]


    @property
    def shamir(self):
        """Shamir secret-shared portion of :attr:`storage`.
        """
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
    """Exception raised when the consistency of secret shares cannot be confirmed."""
    pass


class ActiveProtocolSuite(object):
    """Protocol suite implementing shared secret computation that is secure against an active adversary.

    Implements "Combining Shamir & additive secret sharing to improve
    efficiency of SMC primitives against malicious adversaries" by Goss, which
    provides honest majority security with abort.

    Both :class:`~cicada.additive.AdditiveProtocolSuite` and
    :class:`~cicada.shamir.ShamirProtocolSuite` are used in the implementation.

    Note
    ----
    Creating the protocol is a collective operation that *must*
    be called by all players that are members of `communicator`.

    Parameters
    ----------
    communicator: :class:`cicada.communicator.interface.Communicator`, required
        The communicator that this protocol will use for communication.
    threshold: :class:`int`, required
        The minimum number of shares :math:`k` needed to recover a secret,
        where :math:`k <= \\frac{n+1}{2}` and :math:`n` is the number of players.
    seed: :class:`int`, optional
        Seed used to initialize random number generators.  For privacy, this
        value should be different for each player.  By default, the seed will
        be chosen at random, and is guaranteed to be different even on forked
        processes.  If you specify `seed` yourself, the actual seed used will
        be the sum of this value and the value of `seed_offset`.
    seed_offset: :class:`int`, optional
        Value added to the value of `seed`.  This value defaults to the player's
        rank.
    order: :class:`int`, optional
        Field size for storing encoded values.  Defaults to the largest prime
        less than :math:`2^{64}`.
    encoding: :class:`object`, optional
        Default encoding to use for operations that require encoding/decoding.
        Uses an instance of :any:`FixedPoint` with 16 bits of
        floating-point precision if :any:`None`.
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
        """Elementwise absolute value of a secret shared array.

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
        result: :class:`ActiveArrayShare`
            Secret-shared elementwise absolute value of `operand`.
        """
        self._assert_unary_compatible(operand, "operand")
        return ActiveArrayShare((
            self.aprotocol.absolute(operand.additive),
            self.sprotocol.absolute(operand.shamir)))


    def add(self, lhs, rhs, *, encoding=None):
        """Privacy-preserving elementwise sum of arrays.

        This method can be used to perform private-private, public-private,
        and private-public addition.  The result is the secret shared
        elementwise sum of the operands.  Note that public-public addition
        isn't allowed, as it isn't privacy-preserving!

        Note
        ----
        This is a collective operation that *must* be called
        by all players that are members of :attr:`communicator`.

        Parameters
        ----------
        lhs: :class:`ActiveArrayShare` or :class:`numpy.ndarray`, required
            Secret shared or public values to be added.
        rhs: :class:`ActiveArrayShare` or :class:`numpy.ndarray`, required
            Secret shared or public values to be added.
        encoding: :class:`object`, optional
            Encodes public operands.  The protocol's :attr:`encoding`
            is used by default if :any:`None`.

        Returns
        -------
        result: :class:`ActiveArrayShare`
            Secret-shared sum of `lhs` and `rhs`.
        """
        encoding = self._require_encoding(encoding)

        # Private-private addition.
        if isinstance(lhs, ActiveArrayShare) and isinstance(rhs, ActiveArrayShare):
            return ActiveArrayShare((
                self.aprotocol.add(lhs.additive, rhs.additive),
                self.sprotocol.add(lhs.shamir, rhs.shamir)))

        # Private-public addition.
        if isinstance(lhs, ActiveArrayShare) and isinstance(rhs, numpy.ndarray):
            return ActiveArrayShare((
                self.aprotocol.add(lhs.additive, rhs),
                self.sprotocol.add(lhs.shamir, rhs)))

        # Public-private addition.
        if isinstance(lhs, numpy.ndarray) and isinstance(rhs, ActiveArrayShare):
            return ActiveArrayShare((
                self.aprotocol.add(lhs, rhs.additive),
                self.sprotocol.add(lhs, rhs.shamir)))

        raise NotImplementedError(f"Privacy-preserving addition not implemented for the given types: {type(lhs)} and {type(rhs)}.") # pragma: no cover


    def bit_compose(self, operand):
        """Compose an array of secret-shared bits into an array of corresponding integer field values.

        The result array will will have one fewer dimensions than the operand,
        which must contain bits in big-endian order in its last dimension.
        Note that the input must contain the field values :math:`0` and :math:`1`.

        Note
        ----
        This is a collective operation that *must* be called
        by all players that are members of :attr:`communicator`.

        Parameters
        ----------
        operand: :class:`ActiveArrayShare`, required
            Secret shared array containing bits to be composed.

        Returns
        -------
        result: :class:`ActiveArrayShare`
            Share of the resulting field values.
        """
        self._assert_unary_compatible(operand, "operand")
        return ActiveArrayShare((
            self.aprotocol.bit_compose(operand.additive),
            self.sprotocol.bit_compose(operand.shamir)))


    def bit_decompose(self, operand, *, bits=None):
        """Decompose operand into shares of its bitwise representation.

        The result array will have one more dimension than the operand,
        containing the returned bits in big-endian order.  Note that the
        results will contain the field values :math:`0` and :math:`1`.

        Note
        ----
        This is a collective operation that *must* be called
        by all players that are members of :attr:`communicator`.

        Parameters
        ----------
        operand: :class:`ActiveArrayShare`, required
            Secret shared array containing values to be decomposed.
        bits: :class:`int`, optional
            The number of rightmost bits in each value to extract.  Defaults to
            all bits (i.e. the number of bits used for storage by the protocol's
            :attr:`field`.

        Returns
        -------
        result: :class:`ActiveArrayShare`
            Share of the bit decomposed secret.
        """
        self._assert_unary_compatible(operand, "operand")
        return ActiveArrayShare((
            self.aprotocol.bit_decompose(operand.additive, bits=bits),
            self.sprotocol.bit_decompose(operand.shamir, bits=bits)))


    @property
    def communicator(self):
        """The :class:`~cicada.communicator.interface.Communicator` used by this protocol."""
        return self._communicator


    def divide(self, lhs, rhs, *, encoding=None):
        """Privacy-preserving elementwise division of arrays.

        This method can be used to perform private-private and
        private-public division.  The result is the secret shared
        elementwise quotient of the operands.

        Note
        ----
        This is a collective operation that *must* be called
        by all players that are members of :attr:`communicator`.

        Parameters
        ----------
        lhs: :class:`ActiveArrayShare`, required
            Secret shared value to be divided.
        rhs: :class:`ActiveArrayShare` or :class:`numpy.ndarray`, required
            Secret shared or public value to be divided.
        encoding: :class:`object`, optional
            Encodes public operands and determines the number of bits to
            shift right from intermediate results.  The protocol's
            :attr:`encoding` is used by default if :any:`None`.

        Returns
        -------
        result: :class:`ActiveArrayShare`
            Secret-shared quotient of `lhs` and `rhs`.
        """
        encoding = self._require_encoding(encoding)

        # Private-private division.
        if isinstance(lhs, ActiveArrayShare) and isinstance(rhs, ActiveArrayShare):
            truncbits = encoding.precision
            tbm, tshare = self.random_bitwise_secret(bits=truncbits, shape=rhs.additive.storage.shape)

            rhsmasked = self.field_multiply(tshare, rhs)
            rhsmasked = self.right_shift(rhsmasked, bits=encoding.precision)
            revealrhsmasked = self.reveal(rhsmasked, encoding=encoding)
            almost_there = self.right_shift(self.field_multiply(lhs, tshare), bits=encoding.precision)
            divisor = encoding.encode(numpy.array(1/revealrhsmasked), self.field)
            quotient = self.field_multiply(almost_there, divisor)
            return self.right_shift(quotient, bits=encoding.precision)

        # Private-public division.
        if isinstance(lhs, ActiveArrayShare) and isinstance(rhs, numpy.ndarray):
            return ActiveArrayShare((
                self.aprotocol.divide(lhs.additive, rhs, encoding=encoding),
                self.sprotocol.divide(lhs.shamir, rhs, encoding=encoding)))

        # Public-private division.
        if isinstance(lhs, numpy.ndarray) and isinstance(rhs, ActiveArrayShare):
            pass

        raise NotImplementedError(f"Privacy-preserving division not implemented for the given types: {type(lhs)} and {type(rhs)}.") # pragma: no cover


    def dot(self, lhs, rhs, *, encoding=None):
        """Privacy-preserving dot product of two secret shared vectors.

        Note
        ----
        This is a collective operation that *must* be called
        by all players that are members of :attr:`communicator`.

        Parameters
        ----------
        lhs: :class:`ActiveArrayShare`, required
            Secret shared vector.
        rhs: :class:`ActiveArrayShare`, required
            Secret shared vector.
        encoding: :class:`object`, optional
            Determines the number of bits to truncate from intermediate
            results.  The protocol's :attr:`encoding` is used by default if
            :any:`None`.

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
        """Elementwise probabilistic equality comparison between secret shared arrays.

        The result is the secret shared elementwise comparison `lhs` == `rhs`.  Note
        that the results will contain the field values :math:`0` and :math:`1`.

        Note
        ----
        This is a collective operation that *must* be called
        by all players that are members of :attr:`communicator`.

        Parameters
        ----------
        lhs: :class:`ActiveArrayShare`, required
            Secret shared array to be compared.
        rhs: :class:`ActiveArrayShare`, required
            Secret shared array to be compared.

        Returns
        -------
        result: :class:`ActiveArrayShare`
            Secret-shared result from comparing `lhs` == `rhs` elementwise.
        """
        self._assert_binary_compatible(lhs, rhs, "lhs", "rhs")
        return ActiveArrayShare((
            self.aprotocol.equal(lhs.additive, rhs.additive),
            self.sprotocol.equal(lhs.shamir, rhs.shamir)))


    @property
    def field(self):
        """Integer :any:`Field` used for arithmetic on and storage of secret shared values."""
        return self._field


    def field_add(self, lhs, rhs):
        """Privacy-preserving elementwise sum of arrays.

        This method can be used to perform private-private, public-private,
        and private-public addition.  The result is the secret shared
        elementwise sum of the operands.  Note that public-public addition
        isn't allowed, as it isn't privacy-preserving!

        Unlike :meth:`add`, :meth:`field_add` only operates on field
        values, no encoding is performed on its inputs.

        Note
        ----
        This is a collective operation that *must* be called
        by all players that are members of :attr:`communicator`.

        Parameters
        ----------
        lhs: :class:`ActiveArrayShare` or :class:`numpy.ndarray`, required
            Secret shared or public value to be added.
        rhs: :class:`ActiveArrayShare` or :class:`numpy.ndarray`, required
            Secret shared or public value to be added.

        Returns
        -------
        result: :class:`ActiveArrayShare`
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

        raise NotImplementedError(f"Privacy-preserving addition not implemented for the given types: {type(lhs)} and {type(rhs)}.") # pragma: no cover


    def field_dot(self, lhs, rhs):
        """Privacy-preserving dot product of two secret shared vectors.

        Unlike :meth:`dot`, :meth:`field_dot` only operates on field values,
        no right shift is performed on the results.

        Note
        ----
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
            self.aprotocol.field_dot(lhs.additive, rhs.additive),
            self.sprotocol.field_dot(lhs.shamir, rhs.shamir)))


    def field_multiply(self, lhs, rhs):
        """Privacy-preserving elementwise multiplication of arrays.

        This method can be used to perform private-private, public-private, and
        private-public multiplication.  The result is the secret shared
        elementwise sum of the operands.  Note that public-public
        multiplication isn't allowed, as it isn't privacy-preserving!

        Unlike :meth:`multiply`, :meth:`field_multiply` only operates on field
        values, no encoding is performed on its inputs, and no right shift
        is performed on the results.

        Note
        ----
        This is a collective operation that *must* be called
        by all players that are members of :attr:`communicator`.

        Parameters
        ----------
        lhs: :class:`ActiveArrayShare` or :class:`numpy.ndarray`, required
            Secret shared or public value to be multiplied.
        rhs: :class:`ActiveArrayShare` or :class:`numpy.ndarray`, required
            Secret shared or public value to be multiplied.

        Returns
        -------
        result: :class:`ActiveArrayShare`
            Secret-shared product of `lhs` and `rhs`.
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

        raise NotImplementedError(f"Privacy-preserving multiplication not implemented for the given types: {type(lhs)} and {type(rhs)}.") # pragma: no cover


    def field_power(self, lhs, rhs):
        """Privacy-preserving elementwise exponentiation.

        Raises secret shared array values to public integer values.  Unlike :meth:`power`,
        :meth:`field_power` only operates on field values, no right shift is performed on the
        results.

        Note
        ----
        This is a collective operation that *must* be called
        by all players that are members of :attr:`communicator`.

        Parameters
        ----------
        lhs: :class:`ActiveArrayShare`, required
            Secret shared values which iwll be raised to a power.
        rhs: :class:`int` or integer :class:`numpy.ndarray`, required
            Public integer power(s) to which each element in `lhs` will be raised.

        Returns
        -------
        result: :class:`ActiveArrayShare`
            Secret-shared result of raising `lhs` to the power(s) in `rhs`.
        """
        if isinstance(lhs, ActiveArrayShare) and isinstance(rhs, (numpy.ndarray, int)):
            if isinstance(rhs, int):
                rhs = self.field.full_like(lhs.additive.storage, rhs)
            return ActiveArrayShare((
                self.aprotocol.field_power(lhs.additive, rhs),
                self.sprotocol.field_power(lhs.shamir, rhs)))

        raise NotImplementedError(f"Privacy-preserving exponentiation not implemented for the given types: {type(lhs)} and {type(rhs)}.") # pragma: no cover


    def field_subtract(self, lhs, rhs):
        """Privacy-preserving elementwise difference of arrays.

        This method can be used to perform private-private, public-private, and
        private-public subtraction.  The result is the secret shared
        elementwise difference of the operands.  Note that public-public
        subtraction isn't allowed, as it isn't privacy-preserving!

        Unlike :meth:`subtract`, :meth:`field_subtract` only operates on field
        values, no encoding is performed on its inputs.

        Note
        ----
        This is a collective operation that *must* be called
        by all players that are members of :attr:`communicator`.

        Parameters
        ----------
        lhs: :class:`ActiveArrayShare` or :class:`numpy.ndarray`, required
            Secret shared or public value to be subtracted.
        rhs: :class:`ActiveArrayShare` or :class:`numpy.ndarray`, required
            Secret shared or public value to be subtracted.

        Returns
        -------
        result: :class:`ActiveArrayShare`
            Secret-shared difference of `lhs` and `rhs`.
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

        raise NotImplementedError(f"Privacy-preserving subtraction not implemented for the given types: {type(lhs)} and {type(rhs)}.") # pragma: no cover


    def field_uniform(self, *, shape=None, generator=None):
        """Generate private random field elements.

        This method can be used to generate a secret shared array containing
        random field elements of any shape.

        Note
        ----
        This is a collective operation that *must* be called
        by all players that are members of :attr:`communicator`.

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
        result: :class:`ActiveArrayShare`
            Secret-shared array of random field elements.
        """
        uniadd = self.aprotocol.field_uniform(shape=shape, generator=generator)
        shamadd = []
        for i in self.communicator.ranks:
            shamadd.append(self.sprotocol.share(src=i, secret=uniadd.storage, shape=uniadd.storage.shape, encoding=Identity()))
        unisham = ShamirArrayShare(numpy.array(sum([x.storage for x in shamadd]), dtype=self.field.dtype))
        return ActiveArrayShare((uniadd, unisham))


    def floor(self, operand, *, encoding=None):
        """Privacy-preserving elementwise floor of encoded, secret-shared arrays.

        Note
        ----
        This is a collective operation that *must* be called
        by all players that are members of :attr:`communicator`.

        Parameters
        ----------
        operand: :class:`ActiveArrayShare`, required
            Secret shared values to which floor should be applied.
        encoding: :class:`object`, optional
            Determines the number of fractional bits used for encoded values.
            The protocol's :attr:`encoding` is used by default if :any:`None`.

        Returns
        -------
        result: :class:`ActiveArrayShare`
            Secret-shared floor of `operand`.
        """
        self._assert_unary_compatible(operand, "operand")
        return ActiveArrayShare((
            self.aprotocol.floor(operand.additive, encoding=encoding),
            self.sprotocol.floor(operand.shamir, encoding=encoding)))


    def less(self, lhs, rhs):
        """Privacy-preserving elementwise less-than comparison.

        The result is the secret shared elementwise comparison :math:`lhs \lt rhs`.
        Note that the results will contain the field values :math:`0` or
        :math:`1`, which do not require decoding if revealed.

        Note
        ----
        This is a collective operation that *must* be called
        by all players that are members of :attr:`communicator`.

        Parameters
        ----------
        lhs: :class:`ActiveArrayShare`, required
            Secret shared values to be compared.
        rhs: :class:`ActiveArrayShare`, required
            Secret shared values to be compared.

        Returns
        -------
        result: :class:`ActiveArrayShare`
            Secret-shared comparison :math:`lhs \lt rhs`.
        """
        self._assert_binary_compatible(lhs, rhs, "lhs", "rhs")
        return ActiveArrayShare((
            self.aprotocol.less(lhs.additive, rhs.additive),
            self.sprotocol.less(lhs.shamir, rhs.shamir)))


    def less_zero(self, operand):
        """Privacy-preserving elementwise less-than-zero comparison.

        The result is the secret shared elementwise comparison :math:`operand \lt 0`.
        Note that the results will contain the field values :math:`0` or
        :math:`1`, which do not require decoding if revealed.

        Note
        ----
        This is a collective operation that *must* be called
        by all players that are members of :attr:`communicator`.

        Parameters
        ----------
        lhs: :class:`ActiveArrayShare`, required
            Secret shared values to be compared.
        rhs: :class:`ActiveArrayShare`, required
            Secret shared values to be compared.

        Returns
        -------
        result: :class:`ActiveArrayShare`
            Secret-shared comparison :math:`operand \lt 0`.
        """
        self._assert_unary_compatible(operand, "operand")
        return ActiveArrayShare((
            self.aprotocol.less_zero(operand.additive),
            self.sprotocol.less_zero(operand.shamir)))


    def logical_and(self, lhs, rhs):
        """Privacy-preserving elementwise logical AND of secret shared arrays.

        The operands *must* contain the field values :math:`0` or :math:`1`.
        The result will be the secret shared elementwise logical AND of `lhs`
        and `rhs`, and will also contain the field values :math:`0` or
        :math:`1`, which do not require decoding if revealed.

        Note
        ----
        This is a collective operation that *must* be called
        by all players that are members of :attr:`communicator`.

        Parameters
        ----------
        lhs: :class:`ActiveArrayShare`, required
            Secret shared array for logical AND.
        rhs: :class:`ActiveArrayShare`, required
            Secret shared array for logical AND.

        Returns
        -------
        result: :class:`ActiveArrayShare`
            Secret-shared elementwise logical AND of `lhs` and `rhs`.
        """
        self._assert_binary_compatible(lhs, rhs, "lhs", "rhs")
        return ActiveArrayShare((
            self.aprotocol.logical_and(lhs.additive, rhs.additive),
            self.sprotocol.logical_and(lhs.shamir, rhs.shamir)))


    def logical_not(self, operand):
        """Privacy-preserving elementwise logical NOT.

        The operand *must* contain the field values :math:`0` or :math:`1`.
        The result will be the secret shared elementwise logical NOT of
        `operand`, and will also contain the field values :math:`0` or
        :math:`1`, which do not require decoding if revealed.

        Note
        ----
        This is a collective operation that *must* be called
        by all players that are members of :attr:`communicator`.

        Parameters
        ----------
        operand: :class:`ActiveArrayShare`, required
            Secret shared array for logical NOT.

        Returns
        -------
        result: :class:`ActiveArrayShare`
            Secret-shared elementwise logical NOT of `operand`.
        """
        self._assert_unary_compatible(operand, "operand")
        return ActiveArrayShare((
            self.aprotocol.logical_not(operand.additive),
            self.sprotocol.logical_not(operand.shamir)))


    def logical_or(self, lhs, rhs):
        """Privacy-preserving elementwise logical OR of secret shared arrays.

        The operands *must* contain the field values :math:`0` or :math:`1`.
        The result will be the secret shared elementwise logical OR of `lhs`
        and `rhs`, and will also contain the field values :math:`0` or
        :math:`1`, which do not require decoding if revealed.

        Note
        ----
        This is a collective operation that *must* be called
        by all players that are members of :attr:`communicator`.

        Parameters
        ----------
        lhs: :class:`ActiveArrayShare`, required
            Secret shared array for logical OR.
        rhs: :class:`ActiveArrayShare`, required
            Secret shared array for logical OR.

        Returns
        -------
        result: :class:`ActiveArrayShare`
            Secret-shared elementwise logical OR of `lhs` and `rhs`.
        """
        self._assert_binary_compatible(lhs, rhs, "lhs", "rhs")
        return ActiveArrayShare((
            self.aprotocol.logical_or(lhs.additive, rhs.additive),
            self.sprotocol.logical_or(lhs.shamir, rhs.shamir)))


    def logical_xor(self, lhs, rhs):
        """Privacy-preserving elementwise logical XOR of secret shared arrays.

        The operands *must* contain the field values :math:`0` or :math:`1`.
        The result will be the secret shared elementwise logical XOR of `lhs`
        and `rhs`, and will also contain the field values :math:`0` or
        :math:`1`, which do not require decoding if revealed.

        Note
        ----
        This is a collective operation that *must* be called
        by all players that are members of :attr:`communicator`.

        Parameters
        ----------
        lhs: :class:`ActiveArrayShare`, required
            Secret shared array for logical XOR.
        rhs: :class:`ActiveArrayShare`, required
            Secret shared array for logical XOR.

        Returns
        -------
        result: :class:`ActiveArrayShare`
            Secret-shared elementwise logical XOR of `lhs` and `rhs`.
        """
        self._assert_binary_compatible(lhs, rhs, "lhs", "rhs")
        return ActiveArrayShare((
            self.aprotocol.logical_xor(lhs.additive, rhs.additive),
            self.sprotocol.logical_xor(lhs.shamir, rhs.shamir)))


    def maximum(self, lhs, rhs):
        """Privacy-preserving elementwise maximum of secret shared arrays.

        The result is the secret shared elementwise maximum of the operands.
        Note: the magnitude of the field elements should be less than one
        quarter of the field order for this method to be accurate in general.

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
        result: :class:`ActiveArrayShare`
            Secret-shared elementwise maximum of `lhs` and `rhs`.
        """
        self._assert_binary_compatible(lhs, rhs, "lhs", "rhs")
        return ActiveArrayShare((
            self.aprotocol.maximum(lhs.additive, rhs.additive),
            self.sprotocol.maximum(lhs.shamir, rhs.shamir)))


    def minimum(self, lhs, rhs):
        """Privacy-preserving elementwise minimum of secret shared arrays.

        The result is the secret shared elementwise minimum of the operands.
        Note: the magnitude of the field elements should be less than one
        quarter of the field order for this method to be accurate in general.

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
        result: :class:`ActiveArrayShare`
            Secret-shared elementwise minimum of `lhs` and `rhs`.
        """
        self._assert_binary_compatible(lhs, rhs, "lhs", "rhs")
        return ActiveArrayShare((
            self.aprotocol.minimum(lhs.additive, rhs.additive),
            self.sprotocol.minimum(lhs.shamir, rhs.shamir)))


    def multiplicative_inverse(self, operand):
        """Privacy-preserving elementwise multiplicative inverse of a secret shared array.

        Returns the multiplicative inverse of a secret shared array
        in the context of the underlying finite field. Explicitly, this
        function returns a same shape array which, when multiplied
        elementwise with `operand`, will return a same shape array comprised
        entirely of ones, assuming `operand` is entirely non-trivial elements.

        This function does not take into account any field-external symantics.
        There is a potential for information leak here if `operand` contains any
        zero elements, that will be revealed. There is a small probability,
        2^-operand.storage.size, for this approach to fail by zero being randomly
        generated by the parties as the mask.

        Note
        ----
        This is a collective operation that *must* be called
        by all players that are members of :attr:`communicator`.

        Parameters
        ----------
        operand: :class:`ActiveArrayShare`, required
            Secret shared operand to be multiplicatively inverted.

        Returns
        -------
        result: :class:`ActiveArrayShare`
            Secret-shared elementwise multiplicative inverse of `operand`.
        """
        self._assert_unary_compatible(operand, "operand")
        return ActiveArrayShare((
            self.aprotocol.multiplicative_inverse(operand.additive),
            self.sprotocol.multiplicative_inverse(operand.shamir)))


    def multiply(self, lhs, rhs, *, encoding=None):
        """Privacy-preserving elementwise multiplication of arrays.

        This method can be used to perform private-private, public-private, and
        private-public multiplication.  The result is the secret shared
        elementwise sum of the operands.  Note that public-public
        multiplication isn't allowed, as it isn't privacy-preserving!

        Unlike :meth:`field_multiply`, :meth:`multiply` is encoding aware:
        encoding is performed on its public inputs, and the results are
        shifted right to produce correct results when decoded.

        Note
        ----
        This is a collective operation that *must* be called
        by all players that are members of :attr:`communicator`.

        Parameters
        ----------
        lhs: :class:`ActiveArrayShare` or :class:`numpy.ndarray`, required
            Secret shared or public value to be multiplied.
        rhs: :class:`ActiveArrayShare` or :class:`numpy.ndarray`, required
            Secret shared or public value to be multiplied.
        encoding: :class:`object`, optional
            Encodes public operands and determines the number of bits to shift
            right the results.  The protocol's :attr:`encoding` is used by
            default if :any:`None`.

        Returns
        -------
        result: :class:`ActiveArrayShare`
            Secret-shared product of `lhs` and `rhs`.
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

        raise NotImplementedError(f"Privacy-preserving multiplication not implemented for the given types: {type(lhs)} and {type(rhs)}.") # pragma: no cover


    def negative(self, operand):
        """Privacy-preserving elementwise additive inverse of a secret shared array.

        Returns the additive inverse of a secret shared array
        in the context of the underlying finite field. Explicitly, this
        function returns a same shape array which, when added
        elementwise with `operand`, will return a same shape array comprised
        entirely of zeros.

        Note
        ----
        This is a collective operation that *must* be called
        by all players that are members of :attr:`communicator`.

        Parameters
        ----------
        operand: :class:`ActiveArrayShare`, required
            Secret shared operand to be additively inverted.

        Returns
        -------
        result: :class:`ActiveArrayShare`
            Secret-shared elementwise additive inverse of `operand`.
        """
        self._assert_unary_compatible(operand, "operand")
        return ActiveArrayShare((
            self.aprotocol.negative(operand.additive),
            self.sprotocol.negative(operand.shamir)))


#    def _pade_approx(self, func, operand,*, encoding=None, center=0, degree=12, scale=3):
#        """Return the pade approximation of `func` sampled with `operand`.
#
#        Note
#        ----
#        This is a collective operation that *must* be called
#        by all players that are members of :attr:`communicator`.
#
#        Parameters
#        ----------
#        func: callable object, required
#            The function to be approximated via the pade method.
#        operand: :class:`ActiveArrayShare`, required
#            Secret-shared values where `func` should be evaluated.
#        center: :class:`float`, optional
#            The value at which the approximation should be centered. Sample
#            errors will be larger the further they are from this point.
#
#        Returns
#        -------
#        result: :class:`ActiveArrayShare`
#            Secret shared result of evaluating the pade approximant of func(operand) with the given parameters.
#        """
#        from scipy.interpolate import approximate_taylor_polynomial, pade
#        num_deg = degree%2+degree//2
#        den_deg = degree//2
#
#        self._assert_unary_compatible(operand, "operand")
#        encoding = self._require_encoding(encoding)
#
#        func_taylor = approximate_taylor_polynomial(func, center, degree, scale)
#        func_pade_num, func_pade_den = pade([x for x in func_taylor][::-1], den_deg, n=num_deg)
#        enc_func_pade_num = encoding.encode(numpy.array([x for x in func_pade_num]), self.field)
#        enc_func_pade_den = encoding.encode(numpy.array([x for x in func_pade_den]), self.field)
#        op_pows_num_list = [self.share(src=1, secret=numpy.array(1), shape=())]
#        for i in range(num_deg):
#            op_pows_num_list.append(self.multiply(operand, op_pows_num_list[-1]))
#        if degree%2:
#            op_pows_den_list=[thing for thing in op_pows_num_list[:-1]]
#        else:
#            op_pows_den_list=[thing for thing in op_pows_num_list]
#
#        num_add_shares = AdditiveArrayShare(numpy.array([x.additive.storage for x in op_pows_num_list]))
#        num_sham_shares = ShamirArrayShare(numpy.array([x.shamir.storage for x in op_pows_num_list]))
#        den_add_shares = AdditiveArrayShare(numpy.array([x.additive.storage for x in op_pows_den_list]))
#        den_sham_shares = ShamirArrayShare(numpy.array([x.shamir.storage for x in op_pows_den_list]))
#        op_pows_num = ActiveArrayShare((num_add_shares, num_sham_shares))
#        op_pows_den = ActiveArrayShare((den_add_shares, den_sham_shares ))
#
#        result_num_prod = self.field_multiply(op_pows_num, enc_func_pade_num)
#        result_num = self.right_shift(self.sum(result_num_prod), bits=encoding.precision)
#
#        result_den_prod = self.field_multiply(op_pows_den, enc_func_pade_den)
#        result_den = self.right_shift(self.sum(result_den_prod), bits=encoding.precision)
#        result = self.divide(result_num, result_den)
#        return result



    def power(self, lhs, rhs, *, encoding=None):
        """Privacy-preserving elementwise exponentiation.

        Raises secret shared array values to public integer values.  Unlike
        :meth:`field_power`, :meth:`power` operates on encoded values, shifting
        the results right to ensure correct decoded results.

        Note
        ----
        This is a collective operation that *must* be called
        by all players that are members of :attr:`communicator`.

        Parameters
        ----------
        lhs: :class:`ActiveArrayShare`, required
            Secret shared values which iwll be raised to a power.
        rhs: :class:`int` or integer :class:`numpy.ndarray`, required
            Public integer power(s) to which each element in `lhs` will be raised.
        encoding: :class:`object`, optional
            Determines the number of bits to shift right the results.  The
            protocol's :attr:`encoding` is used by default if :any:`None`.

        Returns
        -------
        result: :class:`ActiveArrayShare`
            Secret-shared result of raising `lhs` to the power(s) in `rhs`.
        """
        if isinstance(lhs, ActiveArrayShare) and isinstance(rhs, (numpy.ndarray, int)):
            if isinstance(rhs, int):
                rhs = self.field.full_like(lhs.storage, rhs)
            return ActiveArrayShare((
                self.aprotocol.power(lhs.additive, rhs),
                self.sprotocol.power(lhs.shamir, rhs)))

        raise NotImplementedError(f"Privacy-preserving exponentiation not implemented for the given types: {type(lhs)} and {type(rhs)}.") # pragma: no cover


    def random_bitwise_secret(self, *, bits, src=None, generator=None, shape=None):
        """Return secret values created by combining randomly generated bits.

        This method returns two outputs - a secret shared array of randomly
        generated bits, and a secret shared array of values created by
        combining the bits in big-endian order.  It is secure against
        non-colluding semi-honest adversaries.  A subset of players (by
        default: all) generate and secret share vectors of pseudo-random bits
        which are then XOR-ed together elementwise.  Communication and
        computation costs increase with the number of bits and the number of
        players, while security increases with the number of players.

        The bit array will have one more dimension than the secret array,
        containing the bits in big-endian order.

        .. warning::

             If you supply your own generators, be careful to ensure that each
             has a unique seed value to preserve privacy (for example: a
             constant plus the player's rank).  If players receive generators
             with identical seed values, even numbers of players will produce
             all zero bits.

        Note
        ----
        This is a collective operation that *must* be called
        by all players that are members of :attr:`communicator`, even
        if they aren't participating in the random bit generation.

        Parameters
        ----------
        bits: :class:`int`, required
            Number of bits to generate.
        shape: sequence of :class:`int`, optional
            Shape of the output `secrets` array.  The output `bits` array will have this
            shape, plus one extra dimension for the bits.
        src: sequence of :class:`int`, optional
            Players that will contribute to random bit generation.  By default,
            all players contribute.
        generator: :class:`numpy.random.Generator`, optional
            A psuedorandom number generator for sampling.  By default,
            `numpy.random.default_rng()` will be used.

        Returns
        -------
        bits: :class:`ActiveArrayShare`
            Secret shared array of randomly-generated bits, with shape
            :math:`shape \\times bits`.
        secrets: :class:`ActiveArrayShare`
            Secret shared array of values created by combining the generated
            bits in big-endian order, with shape `shape`.
        """
        bs_add, ss_add = self.aprotocol.random_bitwise_secret(bits=bits, src=src, generator=generator, shape=shape)
        sham_bs_add = []
        sham_assembled_add = []
        for i in self.communicator.ranks:
            sham_bs_add.append(self.sprotocol.share(src=i, secret=bs_add.storage, shape=bs_add.storage.shape, encoding=Identity()))
            sham_assembled_add.append(self.sprotocol.share(src=i, secret=ss_add.storage, shape=ss_add.storage.shape, encoding=Identity()))
        bs_sham = ShamirArrayShare(numpy.array(sum([x.storage for x in sham_bs_add])%self._field.order, dtype=self.field.dtype))
        ss_sham = ShamirArrayShare(numpy.array(sum([x.storage for x in sham_assembled_add])%self._field.order, dtype=self.field.dtype))
        bs_active = ActiveArrayShare((bs_add, bs_sham))
        assembled_active = ActiveArrayShare((ss_add, ss_sham))
        return (bs_active, assembled_active)


    def relu(self, operand):
        """Privacy-preserving elementwise ReLU of a secret shared array.

        Note
        ----
        This is a collective operation that *must* be called
        by all players that are members of :attr:`communicator`.

        Parameters
        ----------
        operand: :class:`ActiveArrayShare`, required
            Secret shared operand to which the ReLU function will be applied.

        Returns
        -------
        result: :class:`ActiveArrayShare`
            Secret-shared elementwise ReLU of `operand`.
        """
        self._assert_unary_compatible(operand, "operand")
        return ActiveArrayShare((
            self.aprotocol.relu(operand.additive),
            self.sprotocol.relu(operand.shamir)))


    def reshare(self, operand):
        """Privacy-preserving re-randomization of a secret shared array.

        This method returns a new set of secret shares that contain different
        random values than the input but represent the same secret value.

        Note
        ----
        This is a collective operation that *must* be called
        by all players that are members of :attr:`communicator`.

        Parameters
        ----------
        operand: :class:`ActiveArrayShare`, required
            Secret shared operand which should be re-randomized.

        Returns
        -------
        result: :class:`ActiveArrayShare`
            Secret-shared, re-randomized version of `operand`.

        Raises
        ------
        :class:`ConsistencyError`
            If the consistency of the returned secret shares cannot be confirmed.
        """
        self._assert_unary_compatible(operand, "operand")

        reshared = ActiveArrayShare((
            self.aprotocol.reshare(operand.additive),
            self.sprotocol.reshare(operand.shamir)))

        if not self.verify(reshared):
            raise ConsistencyError("Secret Shares being reshared are inconsistent") # pragma: no cover

        return reshared


    def reveal(self, share, *, dst=None, encoding=None):
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
        encoding: :class:`object`, optional
            Encoding used to extract the revealed secret from field values. The
            protocol's default encoding will be used if `None`.

        Returns
        -------
        value: :class:`numpy.ndarray` or :any:`None`
            The revealed secret, if this player is a member of `dst`, or :any:`None`.

        Raises
        ------
        :class:`ConsistencyError`
            If the consistency of the returned secret shares cannot be confirmed.
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
            raise ConsistencyError("Secret Shares are inconsistent in the first stage") # pragma: no cover
        if len(rev.shape) > 0 and numpy.any(rev):
            raise ConsistencyError("Secret Shares are inconsistent in the first stage") # pragma: no cover

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
                raise ConsistencyError("Secret Shares are inconsistent in the second stage") # pragma: no cover
        else:
            if revs != reva or revs2 != reva:
                raise ConsistencyError("Secret Shares are inconsistent in the second stage") # pragma: no cover

        return encoding.decode(revs, self.field)


    def right_shift(self, operand, *, bits, src=None, generator=None):
        """Privacy-preserving elementwise right-shift of a secret shared array.

        Note
        ----
        This is a collective operation that *must* be called
        by all players that are members of :attr:`communicator`.

        Parameters
        ----------
        operand: :class:`ActiveArrayShare`, required
            Secret-shared values to be shifted right.
        bits: :class:`int`, optional
            Number of bits to shift.
        src: sequence of :class:`int`, optional
            Players who will participate in generating random bits as part of
            the shift process.  More players increases security but
            decreases performance.  Defaults to all players.
        generator: :class:`numpy.random.Generator`, optional
            A psuedorandom number generator for generating random bits.  By
            default, `numpy.random.default_rng()` will be used.

        Returns
        -------
        result: :class:`ActiveArrayShare`
            Secret-shared result of shifting `operand` to the right by `bits` bits.
        """
        if not isinstance(operand, ActiveArrayShare):
            raise ValueError(f"Expected operand to be an instance of ActiveArrayShare, got {type(operand)} instead.") # pragma: no cover

        tbm, tshare = self.random_bitwise_secret(bits=bits, src=src, generator=generator, shape=operand.additive.storage.shape)
        rbm, rshare = self.random_bitwise_secret(bits=self.field.bits-bits, src=src, generator=generator, shape=operand.additive.storage.shape)
        return ActiveArrayShare((
            self.aprotocol.right_shift(operand.additive, bits=bits, src=src, generator=generator, trunc_mask=tshare.additive, rem_mask=rshare.additive),
            self.sprotocol.right_shift(operand.shamir, bits=bits, src=src, generator=generator, trunc_mask=tshare.shamir, rem_mask=rshare.shamir)))


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
        share: :class:`ActiveArrayShare`
            The local share of the secret shared array.
        """
        return ActiveArrayShare((
            self.aprotocol.share(src=src, secret=secret, shape=shape, encoding=encoding),
            self.sprotocol.share(src=src, secret=secret, shape=shape, encoding=encoding)))


    def subtract(self, lhs, rhs, *, encoding=None):
        """Privacy-preserving elementwise difference of arrays.

        This method can be used to perform private-private, public-private, and
        private-public addition.  The result is the secret shared elementwise
        difference of the operands.  Note that public-public subtraction isn't
        allowed, as it isn't privacy-preserving!

        Note
        ----
        This is a collective operation that *must* be called
        by all players that are members of :attr:`communicator`.

        Parameters
        ----------
        lhs: :class:`ActiveArrayShare` or :class:`numpy.ndarray`, required
            Secret shared or public values to be subtracted.
        rhs: :class:`ActiveArrayShare` or :class:`numpy.ndarray`, required
            Secret shared or public values to be subtracted.
        encoding: :class:`object`, optional
            Encodes public operands.  The protocol's :attr:`encoding`
            is used by default if :any:`None`.

        Returns
        -------
        result: :class:`ActiveArrayShare`
            Secret-shared difference of `lhs` and `rhs`.
        """
        encoding = self._require_encoding(encoding)

        # Private-private subtraction.
        if isinstance(lhs, ActiveArrayShare) and isinstance(rhs, ActiveArrayShare):
            return ActiveArrayShare((
                self.aprotocol.subtract(lhs.additive, rhs.additive),
                self.sprotocol.subtract(lhs.shamir, rhs.shamir)))

        # Private-public subtraction.
        if isinstance(lhs, ActiveArrayShare) and isinstance(rhs, numpy.ndarray):
            return ActiveArrayShare((
                self.aprotocol.subtract(lhs.additive, rhs),
                self.sprotocol.subtract(lhs.shamir, rhs)))

        # Public-private subtraction.
        if isinstance(lhs, numpy.ndarray) and isinstance(rhs, ActiveArrayShare):
            return ActiveArrayShare((
                self.aprotocol.subtract(lhs, rhs.additive),
                self.sprotocol.subtract(lhs, rhs.shamir)))

        raise NotImplementedError(f"Privacy-preserving subtraction not implemented for the given types: {type(lhs)} and {type(rhs)}.") # pragma: no cover


    def sum(self, operand):
        """Privacy-preserving sum of a secret shared array's elements.

        Note
        ----
        This is a collective operation that *must* be called
        by all players that are members of :attr:`communicator`.

        Parameters
        ----------
        operand: :class:`ActiveArrayShare`, required
            Secret shared array containing elements to be summed.

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
        """Test whether shares are consistent.

        Tests the consistency of secret shares among all players using a zero
        knowledge proof. This method allows the players to prove to one another
        (in zero knowledge) that a consistent set of shares is known by all
        players.  It can provide a "safe" point at which calculations are known
        to be good, so that parties can "rewind" if consistency problems are
        later discovered in the protocol.

        Note
        ----
        This is a collective operation that *must* be called
        by all players that are members of :attr:`communicator`.

        Parameters
        ----------
        operand: :class:`ActiveArrayShare`, required
            Secret shared operand which will be verified for consistency.

        Returns
        -------
        consistency: :class:`bool`
            :any:`True` if every player has demonstrated that they have consistent shares, otherwise :any:`False`.
        """
        self._assert_unary_compatible(operand, "operand")

        a_share = operand.additive
        s_share = operand.shamir
        zero = ShamirArrayShare(self.sprotocol.field.subtract(s_share.storage, numpy.array((pow(self.sprotocol._revealing_coef[self.communicator.rank], self.field.order-2, self.field.order) * a_share.storage) % self.field.order, dtype=object)))
        consistency = numpy.all(self.sprotocol.reveal(zero, encoding=Identity()) == numpy.zeros(zero.storage.shape))
        return consistency



#    def _taylor_approx(self, func, operand,*, encoding=None, center=0, degree=7, scale=3):
#        """Return the taylor approximation of `func` sampled with `operand`.
#
#        Note
#        ----
#        This is a collective operation that *must* be called
#        by all players that are members of :attr:`communicator`.
#
#        Parameters
#        ----------
#        func: callable object, required
#            The function to be approximated via the taylor method
#        operand: :class:`ActiveArrayShare`, required
#            Secret-shared values where `func` should be evaluated.
#        center: :class:`float`, optional
#            The value at which the approximation should be centered. Sample
#            errors will be larger the further they are from this point.
#
#        Returns
#        -------
#        result: :class:`ActiveArrayShare`
#            Secret shared result of evaluating the taylor approximant of func(operand) with the given parameters
#        """
#        from scipy.interpolate import approximate_taylor_polynomial
#
#        self._assert_unary_compatible(operand, "operand")
#        encoding = self._require_encoding(encoding)
#
#        taylor_poly = approximate_taylor_polynomial(func, center, degree, scale)
#
#        enc_taylor_coef = encoding.encode(numpy.array([x for x in taylor_poly]), self.field)
#        op_pow_list = [self.share(src=1, secret=numpy.array(1), shape=())]
#        for i in range(degree):
#            op_pow_list.append(self.multiply(operand, op_pow_list[-1]))
#
#        op_pow_add_shares = AdditiveArrayShare(numpy.array([x.additive.storage for x in op_pow_list]))
#        op_pow_sham_shares = ShamirArrayShare(numpy.array([x.shamir.storage for x in op_pow_list]))
#        op_pow_shares = ActiveArrayShare((op_pow_add_shares, op_pow_sham_shares))
#
#        result = self.field_multiply(op_pow_shares, enc_taylor_coef)
#        result = self.sum(result)
#        result = self.right_shift(result, bits=encoding.precision)
#        return result


    def zigmoid(self, operand, *, encoding=None):
        r"""Privacy-preserving elementwise zigmoid of a secret shared array.

        Zigmoid is a piecewise approximation to the popular sigmoid activation
        function that is more efficient to compute in an MPC context:

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
            Secret shared operand to which the zigmoid function will be applied.

        Returns
        -------
        result: :class:`ActiveArrayShare`
            Secret-shared elementwise zigmoid of `operand`.
        """
        self._assert_unary_compatible(operand, "operand")
        return ActiveArrayShare((
            self.aprotocol.zigmoid(operand.additive, encoding=encoding),
            self.sprotocol.zigmoid(operand.shamir, encoding=encoding)))

