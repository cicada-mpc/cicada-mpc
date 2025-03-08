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

import inspect
import math

import numpy

from cicada.arithmetic import field, Field, FieldArray
from cicada.communicator.interface import Communicator
from cicada.encoding import Bits, Boolean, FixedPoint, Identity
from cicada.przs import PRZSProtocol


class AdditiveArrayShare(object):
    """Stores the local share of a secret shared array for :class:`AdditiveProtocolSuite`.

    Instances of :class:`AdditiveArrayShare` should only be created
    using :class:`AdditiveProtocolSuite`.
    """
    def __init__(self, storage):
        self.storage = storage


    def __repr__(self):
        return f"AdditiveArrayShare(storage={self._storage!r})" # pragma: no cover


    def __getitem__(self, index):
        return AdditiveArrayShare(self.storage[index]) # pragma: no cover


    @property
    def storage(self):
        """Private storage for the local share of a secret shared array.
        Access is provided only for serialization and communication -
        callers must use :class:`AdditiveProtocolSuite` to manipulate secret
        shares.
        """
        return self._storage


    @storage.setter
    def storage(self, storage):
        if not isinstance(type(storage), Field):
            raise ValueError(f"Expected field array, got {type(storage)}.") # pragma: no cover
        self._storage = storage


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
    order: :class:`int`, optional
        Field size for storing encoded values.  Defaults to the largest prime
        less than :math:`2^{64}`.
    encoding: :class:`object`, optional
        Default encoding to use for operations that require encoding/decoding.
        Uses an instance of :any:`FixedPoint` with 16 bits of
        floating-point precision if :any:`None`.
    """
    def __init__(self, communicator, *, seed=None, seed_offset=None, order=None, encoding=None):
        if not isinstance(communicator, Communicator):
            raise ValueError("A Cicada communicator is required.") # pragma: no cover

        # Choose a random seed, if the caller hasn't chosen one already. The
        # chosen seed could be any number, but we choose a random 64-bit
        # integer here so other players cannot guess its value.  We typically
        # get here from a forked process, so we use numpy's random generator
        # because it will produce different seeds even from forked processes.
        if seed is None:
            seed = numpy.random.default_rng(seed=None).integers(low=0, high=2**63-1, endpoint=True)
        else:
            if seed_offset is None:
                seed_offset = communicator.rank
            seed += seed_offset

        if encoding is None:
            encoding = FixedPoint()


        self._communicator = communicator
        self._field = field(order=order)
        self._encoding = encoding
        self._przs = PRZSProtocol(communicator=communicator, field=self._field, seed=seed)


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
        """Elementwise absolute value of a secret shared array.

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
        result: :class:`AdditiveArrayShare`
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
        lhs: :class:`AdditiveArrayShare` or :class:`numpy.ndarray`, required
            Secret shared or public values to be added.
        rhs: :class:`AdditiveArrayShare` or :class:`numpy.ndarray`, required
            Secret shared or public values to be added.
        encoding: :class:`object`, optional
            Encodes public operands.  The protocol's :attr:`encoding`
            is used by default if :any:`None`.

        Returns
        -------
        result: :class:`AdditiveArrayShare`
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
        operand: :class:`AdditiveArrayShare`, required
            Secret shared array containing bits to be composed.

        Returns
        -------
        result: :class:`AdditiveArrayShare`
            Share of the resulting field values.
        """
        self._assert_unary_compatible(operand, "operand")

        bits = operand.storage.shape[-1]
        exponents = numpy.flip(numpy.arange(bits, dtype=object))
        shift = self.field(numpy.power(2, exponents))
        shifted = operand.storage * shift
        return AdditiveArrayShare(shifted.sum(axis=-1))


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
        operand: :class:`AdditiveArrayShare`, required
            Secret shared array containing values to be decomposed.
        bits: :class:`int`, optional
            The number of rightmost bits in each value to extract.  Defaults to
            all bits (i.e. the number of bits used for storage by the protocol's
            :attr:`field`.

        Returns
        -------
        result: :class:`AdditiveArrayShare`
            Share of the bit decomposed secret.
        """
        self._assert_unary_compatible(operand, "operand")

        if bits is None:
            bits = self.field.bits

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
        """The :class:`~cicada.communicator.interface.Communicator` used by this protocol."""
        return self._communicator


    def divide(self, lhs, rhs, *, encoding=None, rmask=None, mask1=None, rem1=None, mask2=None, rem2=None, mask3=None, rem3=None):
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
        lhs: :class:`AdditiveArrayShare`, required
            Secret shared value to be divided.
        rhs: :class:`AdditiveArrayShare` or :class:`numpy.ndarray`, required
            Secret shared or public value to be divided.
        encoding: :class:`object`, optional
            Encodes public operands and determines the number of bits to
            shift right from intermediate results.  The protocol's
            :attr:`encoding` is used by default if :any:`None`.

        Returns
        -------
        result: :class:`AdditiveArrayShare`
            Secret-shared quotient of `lhs` and `rhs`.
        """
        encoding = self._require_encoding(encoding)

        # Private-private division.
        if isinstance(lhs, AdditiveArrayShare) and isinstance(rhs, AdditiveArrayShare):
            zshare = self.share(src=0, secret=numpy.zeros_like(rhs.storage), shape=rhs.storage.shape)
            check = self.reveal(self.equal(rhs, zshare), encoding=Boolean())
            if not len(check.shape):
                if check:
                    raise ZeroDivisionError()
            else:
                if check.any():
                    raise ZeroDivisionError()
            oops = True
            while oops:
                if rmask is None:
                    _, rmask = self.random_bitwise_secret(bits=encoding.precision, shape=rhs.storage.shape)
                else:
                    oops = False
                if not len(rhs.storage.shape):
                    if self.reveal(self.equal(rmask, zshare), encoding=Boolean()):
                        rmask = None
                else:
                    if self.reveal(self.equal(rmask, zshare), encoding=Boolean()).any():
                        rmask = None
            rhsmasked = self.field_multiply(rmask, rhs)
            if mask1 != None and rem1 != None:
                rhsmasked = self.right_shift(rhsmasked, bits=encoding.precision, trunc_mask=mask1, rem_mask=rem1)
            else:
                rhsmasked = self.right_shift(rhsmasked, bits=encoding.precision)
            revealrhsmasked = self.reveal(rhsmasked, encoding=encoding)
            if mask2 != None and rem2 != None:
                almost_there = self.right_shift(self.field_multiply(lhs, rmask), bits=encoding.precision, trunc_mask=mask2, rem_mask=rem2)
            else:
                almost_there = self.right_shift(self.field_multiply(lhs, rmask), bits=encoding.precision)
            divisor = encoding.encode(numpy.array(1 / revealrhsmasked), self.field)
            quotient = AdditiveArrayShare(self.field.multiply(almost_there.storage, divisor))
            if mask3 != None and rem3 != None:
                return self.right_shift(quotient, bits=encoding.precision, trunc_mask=mask3, rem_mask=rem3)
            else:
                return self.right_shift(quotient, bits=encoding.precision)

        # Private-public division.
        if isinstance(lhs, AdditiveArrayShare) and isinstance(rhs, numpy.ndarray):
            if rhs == numpy.zeros_like(rhs):
                raise ZeroDivisionError()
            divisor = encoding.encode(numpy.array(1 / rhs), self.field)
            result = self.field_multiply(lhs, divisor)
            result = self.right_shift(result, bits=encoding.precision)
            return result

        raise NotImplementedError(f"Privacy-preserving division not implemented for the given types: {type(lhs)} and {type(rhs)}.") # pragma: no cover


    def dot(self, lhs, rhs, *, encoding=None):
        """Privacy-preserving dot product of two secret shared vectors.

        Note
        ----
        This is a collective operation that *must* be called
        by all players that are members of :attr:`communicator`.

        Parameters
        ----------
        lhs: :class:`AdditiveArrayShare`, required
            Secret shared vector.
        rhs: :class:`AdditiveArrayShare`, required
            Secret shared vector.
        encoding: :class:`object`, optional
            Determines the number of bits to truncate from intermediate
            results.  The protocol's :attr:`encoding` is used by default if
            :any:`None`.

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
        """Default encoding to use for operations that require encoding/decoding."""
        return self._encoding


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
        lhs: :class:`AdditiveArrayShare`, required
            Secret shared array to be compared.
        rhs: :class:`AdditiveArrayShare`, required
            Secret shared array to be compared.

        Returns
        -------
        result: :class:`AdditiveArrayShare`
            Secret-shared result from comparing `lhs` == `rhs` elementwise.
        """
        self._assert_binary_compatible(lhs, rhs, "lhs", "rhs")
        diff = self.field_subtract(lhs, rhs)
        return self.logical_not(self.field_power(diff, self.field.order - 1))


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
        lhs: :class:`AdditiveArrayShare`, :class:`FieldArray`, or :class:`numpy.ndarray`, required
            Secret shared or public value to be added.
        rhs: :class:`AdditiveArrayShare`, :class:`FieldArray`, or :class:`numpy.ndarray`, required
            Secret shared or public value to be added.

        Returns
        -------
        result: :class:`AdditiveArrayShare`
            Secret-shared sum of `lhs` and `rhs`.
        """
        # Private-private addition.
        if isinstance(lhs, AdditiveArrayShare) and isinstance(rhs, AdditiveArrayShare):
            return AdditiveArrayShare(lhs.storage + rhs.storage)

        # Private-public addition.
        if isinstance(lhs, AdditiveArrayShare) and isinstance(rhs, self.field):
            if self.communicator.rank == 0:
                return AdditiveArrayShare(lhs.storage + rhs)
            return lhs

        if isinstance(lhs, AdditiveArrayShare) and isinstance(rhs, numpy.ndarray):
            if self.communicator.rank == 0:
                return AdditiveArrayShare(lhs.storage + self.field(rhs))
            return lhs

        # Public-private addition.
        if isinstance(lhs, self.field) and isinstance(rhs, AdditiveArrayShare):
            if self.communicator.rank == 0:
                return AdditiveArrayShare(lhs + rhs.storage)
            return rhs

        if isinstance(lhs, numpy.ndarray) and isinstance(rhs, AdditiveArrayShare):
            if self.communicator.rank == 0:
                return AdditiveArrayShare(self.field(lhs) + rhs.storage)
            return rhs

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
        lhs: :class:`AdditiveArrayShare` :class:`FieldArray`, or :class:`numpy.ndarray`, required
            Secret shared or public value to be multiplied.
        rhs: :class:`AdditiveArrayShare` :class:`FieldArray`, or :class:`numpy.ndarray`, required
            Secret shared or public value to be multiplied.

        Returns
        -------
        result: :class:`AdditiveArrayShare`
            Secret-shared product of `lhs` and `rhs`.
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

            return AdditiveArrayShare(result)

        # Public-private multiplication.
        if isinstance(lhs, self.field) and isinstance(rhs, AdditiveArrayShare):
            return AdditiveArrayShare(lhs * rhs.storage)

        if isinstance(lhs, numpy.ndarray) and isinstance(rhs, AdditiveArrayShare):
            return AdditiveArrayShare(self.field(lhs) * rhs.storage)

        # Private-public multiplication.
        if isinstance(lhs, AdditiveArrayShare) and isinstance(rhs, self.field):
            return AdditiveArrayShare(lhs.storage * rhs)

        if isinstance(lhs, AdditiveArrayShare) and isinstance(rhs, numpy.ndarray):
            return AdditiveArrayShare(lhs.storage * self.field(rhs))

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
        lhs: :class:`AdditiveArrayShare`, required
            Secret shared values which iwll be raised to a power.
        rhs: :class:`int` or integer :class:`numpy.ndarray`, required
            Public integer power(s) to which each element in `lhs` will be raised.

        Returns
        -------
        result: :class:`AdditiveArrayShare`
            Secret-shared result of raising `lhs` to the power(s) in `rhs`.
        """
        if isinstance(lhs, AdditiveArrayShare) and isinstance(rhs, (numpy.ndarray, int)):
            if isinstance(rhs, int):
                rhs = self.field.full_like(lhs.storage, rhs)

            results = []
            for value, power in numpy.nditer([lhs.storage, rhs], order="C", flags=["refs_ok"]):
                value = AdditiveArrayShare(self.field(value))
                result = self.share(src=0, secret=self.field(1), shape=(), encoding=Identity())

                # Snazzy implementation performs exponentiation by squaring.
                while True:
                    if power & 1:
                       result = self.field_multiply(result, value)

                    if not power:
                        break

                    value = self.field_multiply(value, value)
                    power = power >> 1

                results.append(result)

            results = self.field([result.storage.item() for result in results])
            results = results.reshape(lhs.storage.shape, order="C")
            return AdditiveArrayShare(results)

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
        lhs: :class:`AdditiveArrayShare`, :class:`FieldArray`, or :class:`numpy.ndarray`, required
            Secret shared or public value to be subtracted.
        rhs: :class:`AdditiveArrayShare`, :class:`FieldArray`, or :class:`numpy.ndarray`, required
            Secret shared or public value to be subtracted.

        Returns
        -------
        result: :class:`AdditiveArrayShare`
            Secret-shared difference of `lhs` and `rhs`.
        """
        # Private-private subtraction.
        if isinstance(lhs, AdditiveArrayShare) and isinstance(rhs, AdditiveArrayShare):
            return AdditiveArrayShare(lhs.storage - rhs.storage)

        # Public-private subtraction.
        if isinstance(lhs, self.field) and isinstance(rhs, AdditiveArrayShare):
            if self.communicator.rank == 0:
                return AdditiveArrayShare(lhs - rhs.storage)
            return AdditiveArrayShare(-rhs.storage)

        if isinstance(lhs, numpy.ndarray) and isinstance(rhs, AdditiveArrayShare):
            if self.communicator.rank == 0:
                return AdditiveArrayShare(self.field(lhs) - rhs.storage)
            return AdditiveArrayShare(-rhs.storage)

        # Private-public subtraction.
        if isinstance(lhs, AdditiveArrayShare) and isinstance(rhs, self.field):
            if self.communicator.rank == 0:
                return AdditiveArrayShare(lhs.storage - rhs)
            return AdditiveArrayShare(lhs.storage)

        if isinstance(lhs, AdditiveArrayShare) and isinstance(rhs, numpy.ndarray):
            if self.communicator.rank == 0:
                return AdditiveArrayShare(lhs.storage - self.field(rhs))
            return AdditiveArrayShare(lhs.storage)

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
        result: :class:`AdditiveArrayShare`
            Secret-shared array of random field elements.
        """

        if shape is None:
            shape=()

        if generator is None:
            generator = numpy.random.default_rng()

        return AdditiveArrayShare(self.field.uniform(size=shape, generator=generator))


    def floor(self, operand, *, encoding=None):
        """Privacy-preserving elementwise floor of encoded, secret-shared arrays.

        Note
        ----
        This is a collective operation that *must* be called
        by all players that are members of :attr:`communicator`.

        Parameters
        ----------
        operand: :class:`AdditiveArrayShare`, required
            Secret shared values to which floor should be applied.
        encoding: :class:`object`, optional
            Determines the number of fractional bits used for encoded values.
            The protocol's :attr:`encoding` is used by default if :any:`None`.

        Returns
        -------
        result: :class:`AdditiveArrayShare`
            Secret-shared floor of `operand`.
        """
        self._assert_unary_compatible(operand, "operand")
        encoding = self._require_encoding(encoding)

        one = self.share(src=0, secret=self.field.full_like(operand.storage, 2**encoding.precision), shape=operand.storage.shape, encoding=Identity())
        shift_op = self.field.full_like(operand.storage, 2**encoding.precision)
        pl2 = self.field.full_like(operand.storage, self.field.order-1)

        abs_op = self.absolute(operand)
        frac_bits = encoding.precision
        field_bits = self.field.bits
        lsbs = self.bit_decompose(abs_op, bits=encoding.precision)
        lsbs_composed = self.bit_compose(lsbs)
        lsbs_inv = self.negative(lsbs_composed)
        two_lsbs = AdditiveArrayShare(self.field.multiply(lsbs_composed.storage, self.field.full_like(lsbs_composed.storage, 2)))
        ltz = self.less_zero(operand)
        ones2sub = AdditiveArrayShare(self.field.multiply(self.field_power(lsbs_composed, pl2).storage, shift_op))
        sel_2_lsbs = self.field_multiply(self.field_subtract(two_lsbs, ones2sub), ltz)
        return self.field_add(self.field_add(sel_2_lsbs, lsbs_inv), operand)


    def less(self, lhs, rhs):
        r"""Privacy-preserving elementwise less-than comparison.

        The result is the secret shared elementwise comparison :math:`lhs \lt rhs`.
        Note that the results will contain the field values :math:`0` or
        :math:`1`, which do not require decoding if revealed.

        Note
        ----
        This is a collective operation that *must* be called
        by all players that are members of :attr:`communicator`.

        Parameters
        ----------
        lhs: :class:`AdditiveArrayShare`, required
            Secret shared values to be compared.
        rhs: :class:`AdditiveArrayShare`, required
            Secret shared values to be compared.

        Returns
        -------
        result: :class:`AdditiveArrayShare`
            Secret-shared comparison :math:`lhs \lt rhs`.
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
        r"""Privacy-preserving elementwise less-than-zero comparison.

        The result is the secret shared elementwise comparison :math:`operand \lt 0`.
        Note that the results will contain the field values :math:`0` or
        :math:`1`, which do not require decoding if revealed.

        Note
        ----
        This is a collective operation that *must* be called
        by all players that are members of :attr:`communicator`.

        Parameters
        ----------
        lhs: :class:`AdditiveArrayShare`, required
            Secret shared values to be compared.
        rhs: :class:`AdditiveArrayShare`, required
            Secret shared values to be compared.

        Returns
        -------
        result: :class:`AdditiveArrayShare`
            Secret-shared comparison :math:`operand \lt 0`.
        """
        self._assert_unary_compatible(operand, "operand")
        two = self.field.full_like(operand.storage, 2)
        result = self.field_multiply(two, operand)
        return self._lsb(result)


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
        lhs: :class:`AdditiveArrayShare`, required
            Secret shared array for logical AND.
        rhs: :class:`AdditiveArrayShare`, required
            Secret shared array for logical AND.

        Returns
        -------
        result: :class:`AdditiveArrayShare`
            Secret-shared elementwise logical AND of `lhs` and `rhs`.
        """
        self._assert_binary_compatible(lhs, rhs, "lhs", "rhs")
        return self.field_multiply(lhs, rhs)


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
        operand: :class:`AdditiveArrayShare`, required
            Secret shared array for logical NOT.

        Returns
        -------
        result: :class:`AdditiveArrayShare`
            Secret-shared elementwise logical NOT of `operand`.
        """
        self._assert_unary_compatible(operand, "operand")
        return self.field_subtract(self.field.ones_like(operand.storage), operand)


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
        lhs: :class:`AdditiveArrayShare`, required
            Secret shared array for logical OR.
        rhs: :class:`AdditiveArrayShare`, required
            Secret shared array for logical OR.

        Returns
        -------
        result: :class:`AdditiveArrayShare`
            Secret-shared elementwise logical OR of `lhs` and `rhs`.
        """
        self._assert_binary_compatible(lhs, rhs, "lhs", "rhs")
        total = self.field_add(lhs, rhs)
        product = self.field_multiply(lhs, rhs)
        return self.field_subtract(total, product)


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
        lhs: :class:`AdditiveArrayShare`, required
            Secret shared array for logical XOR.
        rhs: :class:`AdditiveArrayShare`, required
            Secret shared array for logical XOR.

        Returns
        -------
        result: :class:`AdditiveArrayShare`
            Secret-shared elementwise logical XOR of `lhs` and `rhs`.
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
        result: :class:`AdditiveArrayShare`
            Additive shared array containing the elementwise least significant
            bits of `operand`.
        """
        flattened = AdditiveArrayShare(operand.storage.flatten(order="C"))
        bits = self.random_bits(shape=flattened.storage.shape + (self.field.bits,))
        mask = self.bit_compose(bits)
        masked = self.field_add(flattened, mask)
        masked = self.reveal(masked, encoding=Identity())

        comp_result = self._public_bitwise_less_than(masked, bits)

        masked %= self.field(2)

        c0xr0 = self.field.zeros(masked.shape)
        for i, lc in enumerate(masked):
            if lc:
                c0xr0[i] = self.field_subtract(self.field(1), AdditiveArrayShare(self.field(bits.storage[i][-1]))).storage
            else:
                c0xr0[i] = bits.storage[i][-1]
        c0xr0 = AdditiveArrayShare(c0xr0)
        result = self.field_multiply(comp_result, c0xr0)
        result = AdditiveArrayShare(self.field(2) * result.storage)
        result = self.field_subtract(c0xr0, result)
        result = self.field_add(comp_result, result)
        return AdditiveArrayShare(result.storage.reshape(operand.storage.shape, order="C"))


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
        lhs: :class:`AdditiveArrayShare`, required
            Secret shared operand.
        rhs: :class:`AdditiveArrayShare`, required
            Secret shared operand.

        Returns
        -------
        result: :class:`AdditiveArrayShare`
            Secret-shared elementwise maximum of `lhs` and `rhs`.
        """
        self._assert_binary_compatible(lhs, rhs, "lhs", "rhs")
        max_share = self.field_add(self.field_add(lhs, rhs), self.absolute(self.field_subtract(lhs, rhs)))
        shift_right = self.field.full_like(lhs.storage, pow(2, self.field.order-2, self.field.order))
        max_share = self.field_multiply(max_share, shift_right)
        return max_share


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
        lhs: :class:`AdditiveArrayShare`, required
            Secret shared operand.
        rhs: :class:`AdditiveArrayShare`, required
            Secret shared operand.

        Returns
        -------
        result: :class:`AdditiveArrayShare`
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
        operand: :class:`AdditiveArrayShare`, required
            Secret shared operand to be multiplicatively inverted.

        Returns
        -------
        result: :class:`AdditiveArrayShare`
            Secret-shared elementwise multiplicative inverse of `operand`.
        """
        self._assert_unary_compatible(operand, "operand")

        mask = self.field_uniform(shape=operand.storage.shape)
        masked_op = self.field_multiply(mask, operand)
        revealed_masked_op = self.reveal(masked_op, encoding=Identity())
        nppowmod = numpy.vectorize(lambda a, b, c: pow(int(a), int(b), int(c)), otypes=[self.field.dtype])
        inv = self.field(nppowmod(revealed_masked_op, self.field.order-2, self.field.order))
        return AdditiveArrayShare(inv * mask.storage)


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
        lhs: :class:`AdditiveArrayShare` or :class:`numpy.ndarray`, required
            Secret shared or public value to be multiplied.
        rhs: :class:`AdditiveArrayShare` or :class:`numpy.ndarray`, required
            Secret shared or public value to be multiplied.
        encoding: :class:`object`, optional
            Encodes public operands and determines the number of bits to shift
            right the results.  The protocol's :attr:`encoding` is used by
            default if :any:`None`.

        Returns
        -------
        result: :class:`AdditiveArrayShare`
            Secret-shared product of `lhs` and `rhs`.
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
        This is a collective operation that *must* be called by all players
        that are members of :attr:`communicator`.

        Parameters
        ----------
        operand: :class:`AdditiveArrayShare`, required
            Secret shared operand to be additively inverted.

        Returns
        -------
        result: :class:`AdditiveArrayShare`
            Secret-shared elementwise additive inverse of `operand`.
        """
        self._assert_unary_compatible(operand, "operand")
        #return self.field_subtract(self.field.full_like(operand.storage, self.field.order), operand)
        return AdditiveArrayShare(-operand.storage)


#    def pade_approx(self, func, operand, *, encoding=None, center=0, degree=12, scale=3):
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
#        operand: :class:`AdditiveArrayShare`, required
#            Secret-shared values where `func` should be evaluated.
#        center: :class:`float`, optional
#            The value at which the approximation should be centered. Sample
#            errors will be larger the further they are from this point.
#
#        Returns
#        -------
#        result: :class:`AdditiveArrayShare`
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
#
#        result_list=[]
#        for op in operand.storage:
#            single_op_share = AdditiveArrayShare(numpy.array(op, dtype=object))
#            op_pows_num_list = [self.share(src=1, secret=numpy.array(1), shape=())]
#            for i in range(num_deg):
#                op_pows_num_list.append(self.multiply(single_op_share, op_pows_num_list[-1]))
#            if degree%2:
#                op_pows_den_list=[thing for thing in op_pows_num_list[:-1]]
#            else:
#                op_pows_den_list=[thing for thing in op_pows_num_list]
#            op_pows_num = AdditiveArrayShare(numpy.array([x.storage for x in op_pows_num_list]))
#            op_pows_den = AdditiveArrayShare(numpy.array([x.storage for x in op_pows_den_list]))
#
#            result_num_prod = self.field_multiply(op_pows_num, enc_func_pade_num)
#            result_num = self.right_shift(self.sum(result_num_prod), bits=encoding.precision)
#
#            result_den_prod = self.field_multiply(op_pows_den, enc_func_pade_den)
#            result_den = self.right_shift(self.sum(result_den_prod), bits=encoding.precision)
#            result_list.append(self.divide(result_num, result_den))
#        return AdditiveArrayShare(numpy.array([s.storage for s in result_list], dtype=object))


    def power(self, lhs, rhs, *, encoding=None):
        """Privacy-preserving elementwise exponentiation.

        Raises secret shared array values to public integer values.  Unlike
        :meth:`field_power`, :meth:`power` operates on encoded values, shifting
        the results to ensure correct decoded results.

        Note
        ----
        This is a collective operation that *must* be called
        by all players that are members of :attr:`communicator`.

        Parameters
        ----------
        lhs: :class:`AdditiveArrayShare`, required
            Secret shared values which will be raised to a power.
        rhs: :class:`numpy.ndarray` containing integers, required
            Public non-negative integer power to which each element in `lhs` will be raised.
            Normal numpy broadcasting rules apply, so `rhs` can be any shape that
            is compatible with `lhs`.
        encoding: :class:`object`, optional
            Determines how far to right shift the results.  The protocol's
            :attr:`encoding` is used by default if :any:`None`.

        Returns
        -------
        result: :class:`AdditiveArrayShare`
            Secret-shared result of raising `lhs` to the power(s) in `rhs`.
        """
        encoding = self._require_encoding(encoding)

        if isinstance(lhs, AdditiveArrayShare) and isinstance(rhs, numpy.ndarray):
            results=[]
            for value, power in numpy.nditer([lhs.storage, rhs], order="C", flags=["refs_ok"]):
                value = AdditiveArrayShare(self.field(value))
                result = self.share(src=0, secret=numpy.array(1.0), shape=(), encoding=encoding)

#                    # Naive implementation performs n multiplications when raising to the n-th power.
#                    for i in range(power):
#                        result = self.field_multiply(result, value)
#                        result = self.right_shift(result, bits=encoding.precision)

                # Fancy implementation performs exponentiation by squaring.
                while True:
                    if power & 1:
                        result = self.field_multiply(result, value)
                        result = self.right_shift(result, bits=encoding.precision)

                    if not power:
                        break

                    value = self.field_multiply(value, value)
                    value = self.right_shift(value, bits=encoding.precision)
                    power = power >> 1

                results.append(result)

            results = self.field([result.storage.item() for result in results])
            results = results.reshape(lhs.storage.shape, order="C")
            return AdditiveArrayShare(results)

        raise NotImplementedError(f"Privacy-preserving exponentiation not implemented for the given types: {type(lhs)} and {type(rhs)}.") # pragma: no cover


    def _public_bitwise_less_than(self, lhspub, rhs):
        """Comparison Operator

        Parameters
        ----------
        lhspub: :class:`ndarray`, required
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
        lhsbits = self.field(lhsbits)

        assert(lhsbits.shape == rhs.storage.shape)
        flatlhsbits = lhsbits.reshape((-1, lhsbits.shape[-1]))
        flatrhsbits = rhs.storage.reshape((-1, rhs.storage.shape[-1]))

        results=[]
        for j in range(len(flatlhsbits)):
            xord = []
            preord = []
            msbdiff=[]
            rhs_bit_at_msb_diff = []
            for i in range(bitwidth):
                rhsbit=AdditiveArrayShare(self.field(flatrhsbits[j,i]))
                if flatlhsbits[j][i] == 1:
                    xord.append(self.field_subtract(self.field(1), rhsbit))
                else:
                    xord.append(rhsbit)
            preord = [xord[0]]
            for i in range(1,bitwidth):
                preord.append(self.logical_or(preord[i-1], xord[i]))
            msbdiff = [preord[0]]
            for i in range(1,bitwidth):
                msbdiff.append(self.field_subtract(preord[i], preord[i-1]))
            for i in range(bitwidth):
                rhsbit=AdditiveArrayShare(self.field(flatrhsbits[j,i]))
                rhs_bit_at_msb_diff.append(self.field_multiply(rhsbit, msbdiff[i]))
            result = rhs_bit_at_msb_diff[0]
            for i in range(1,bitwidth):
                result = self.field_add(result, rhs_bit_at_msb_diff[i])
            results.append(result)
        return AdditiveArrayShare(self.field([x.storage.item() for x in results]).reshape(rhs.storage.shape[:-1]))


    def random_bits(self, *, shape=None, src=None, generator=None):
        """Return securely generated random bits.

        This method returns a secret shared array of randomly generated bits.
        It is secure against non-colluding semi-honest adversaries.  A subset
        of players (by default: all) generate and secret share pseudo-random
        bits which are then XOR-ed together.  Communication and computation
        costs increase with the number of bits and the number of players, while
        security increases with the number of players.

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
        shape: sequence of :class:`int`, optional
            Shape of the output `bits` array.
        src: sequence of :class:`int`, optional
            Players that will contribute to random bit generation.  By default,
            all players contribute.
        generator: :class:`numpy.random.Generator`, optional
            A psuedorandom number generator for sampling.  By default,
            `numpy.random.default_rng()` will be used.

        Returns
        -------
        bits: :class:`AdditiveArrayShare`
            Secret shared array of randomly-generated bits, with shape
            :math:`shape`.
        """
        if shape is None:
            shape = ()
        if src is None:
            src = self.communicator.ranks
        if not src:
            raise ValueError(f"src must include at least one player, got {src} instead.") # pragma: no cover
        if generator is None:
            generator = numpy.random.default_rng()

        # Each participating player generates a secret-shared array of random bits.
        all_bits = []
        for rank in src:
            local_bits = generator.choice(2, size=shape) if self.communicator.rank == rank else None
            all_bits.append(self.share(src=rank, secret=local_bits, shape=shape, encoding=Bits()))

        # Generate the final bits by xor-ing everything together elementwise.
        bits = all_bits[0]
        for local_bits in all_bits[1:]:
            result = self.logical_xor(bits, local_bits)

        return bits


    def relu(self, operand):
        """Privacy-preserving elementwise ReLU of a secret shared array.

        Note
        ----
        This is a collective operation that *must* be called
        by all players that are members of :attr:`communicator`.

        Parameters
        ----------
        operand: :class:`AdditiveArrayShare`, required
            Secret shared operand to which the ReLU function will be applied.

        Returns
        -------
        result: :class:`AdditiveArrayShare`
            Secret-shared elementwise ReLU of `operand`.
        """
        self._assert_unary_compatible(operand, "operand")
        ltz = self.less_zero(operand)
        nltz = self.logical_not(ltz)
        nltz_parts = self.field_multiply(nltz, operand)
        return nltz_parts


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
        operand: :class:`AdditiveArrayShare`, required
            Secret shared operand which should be re-randomized.

        Returns
        -------
        result: :class:`AdditiveArrayShare`
            Secret-shared, re-randomized version of `operand`.
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
        self._assert_unary_compatible(share, "share")

        # Identify who will be receiving shares.
        if dst is None:
            dst = self.communicator.ranks

        encoding = self._require_encoding(encoding)

        # Send data to the other players.
        secret = None
        for recipient in dst:
            received_shares = self.communicator.gather(value=share.storage.view(numpy.ndarray), dst=recipient)

            # If we're a recipient, recover the secret.
            if self.communicator.rank == recipient:
                secret = self.field.zeros_like(received_shares[0])
                for received_share in received_shares:
                    secret += self.field(received_share)

        return encoding.decode(secret)


    def right_shift(self, operand, *, bits, src=None, generator=None, trunc_mask=None, rem_mask=None):
        """Privacy-preserving elementwise right-shift of a secret shared array.

        Note
        ----
        This is a collective operation that *must* be called
        by all players that are members of :attr:`communicator`.

        Also, this approach may probabilstically introduce a small error in the least significant bits
        of the result. The is that we generate masks for the two sections of the secret shared value
        of interest, one to be used in clearing out the low order bits, the other for masking the
        higher order bits that will remain. There is a chance that adding the masks in will generate
        a carry into the region that will remain after the shift. Therefore there is a chance that the
        effects of that carry will remain in the least significant bits of the final result, which,
        with the default parameters and encoding, means there could be an error in the final result on
        the order of 2^-16, and with decreasing probability 2^-15, or 2^-14 depending on how far the
        carry propagates.


        Parameters
        ----------
        operand: :class:`AdditiveArrayShare`, required
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
        result: :class:`AdditiveArrayShare`
            Secret-shared result of shifting `operand` to the right by `bits` bits.
        """
        if not isinstance(operand, AdditiveArrayShare):
            raise ValueError(f"Expected operand to be an instance of AdditiveArrayShare, got {type(operand)} instead.") # pragma: no cover

        # Amount to shift the remaining_mask to the left.
        shift_left = self.field(2**bits)
        # Multiplicative inverse of shift_left.
        shift_right = self.field(pow(2**bits, self.field.order-2, self.field.order))

        if trunc_mask:
            truncation_mask = trunc_mask
        else:
            # Generate random bits that will mask the region to be truncated.
            truncation_mask = self.bit_compose(self.random_bits(src=src, generator=generator, shape=operand.storage.shape + (bits,)))
        if rem_mask:
            remaining_mask = rem_mask
        else:
            # Generate random bits that will mask everything outside the region to be truncated.
            remaining_mask = self.bit_compose(self.random_bits(src=src, generator=generator, shape=operand.storage.shape + (self.field.bits-bits,)))

        remaining_mask.storage = remaining_mask.storage * shift_left

        # Combine the two masks.
        mask = self.field_add(remaining_mask, truncation_mask)

        # Mask the array element.
        masked_element = self.field_add(operand, mask)

        # Reveal the element to all players (because it's masked, no player learns the underlying secret).
        masked_element = self.reveal(masked_element, encoding=Identity())

        # Retain just the bits within the region to be truncated, which need to be removed.
        masked_truncation_bits = masked_element % shift_left

        # Remove the mask, leaving just the bits to be removed from the
        # truncation region.  Because the result of the subtraction is
        # secret shared, the secret still isn't revealed.
        truncation_bits = self.field_subtract(masked_truncation_bits, truncation_mask)

        # Remove the bits in the truncation region from the element.  The result can be safely truncated.
        result = self.field_subtract(operand, truncation_bits)

        # Truncate the element by shifting right to get rid of the (now cleared) bits in the truncation region.
        return AdditiveArrayShare(result.storage * shift_right)


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

        # Generate a pseudorandom zero-sharing.
        przs = self._przs(shape=shape)

        # Add the secret to the PRZS
        if self.communicator.rank == src:
            secret = encoding.encode(secret, self.field)
            przs += secret
        # Package the result.
        return AdditiveArrayShare(przs)


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
        lhs: :class:`AdditiveArrayShare` or :class:`numpy.ndarray`, required
            Secret shared or public values to be subtracted.
        rhs: :class:`AdditiveArrayShare` or :class:`numpy.ndarray`, required
            Secret shared or public values to be subtracted.
        encoding: :class:`object`, optional
            Encodes public operands.  The protocol's :attr:`encoding`
            is used by default if :any:`None`.

        Returns
        -------
        result: :class:`AdditiveArrayShare`
            Secret-shared difference of `lhs` and `rhs`.
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

        raise NotImplementedError(f"Privacy-preserving subtraction not implemented for the given types: {type(lhs)} and {type(rhs)}.") # pragma: no cover


    def sum(self, operand):
        """Privacy-preserving sum of a secret shared array's elements.

        Note
        ----
        This is a collective operation that *must* be called
        by all players that are members of :attr:`communicator`.

        Parameters
        ----------
        operand: :class:`AdditiveArrayShare`, required
            Secret shared array containing elements to be summed.

        Returns
        -------
        value: :class:`AdditiveArrayShare`
            Secret-shared sum of `operand`'s elements.
        """
        self._assert_unary_compatible(operand, "operand")
        return AdditiveArrayShare(operand.storage.sum())


#    def taylor_approx(self, func, operand, *, encoding=None, center=0, degree=7, scale=3):
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
#        operand: :class:`AdditiveArrayShare`, required
#            Secret-shared values where `func` should be evaluated.
#        center: :class:`float`, optional
#            The value at which the approximation should be centered. Sample
#            errors will be larger the further they are from this point.
#
#        Returns
#        -------
#        result: :class:`AdditiveArrayShare`
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
#        result_list=[]
#        for op in operand.storage:
#            single_op_share = AdditiveArrayShare(numpy.array(op, dtype=object))
#            op_pow_list = [self.share(src=1, secret=numpy.array(1), shape=())]
#            for i in range(degree):
#                op_pow_list.append(self.multiply(single_op_share, op_pow_list[-1]))
#
#            op_pow_shares = AdditiveArrayShare(numpy.array([x.storage for x in op_pow_list]))
#
#            result = self.field_multiply(op_pow_shares, enc_taylor_coef)
#            result = self.sum(result)
#            result = self.right_shift(result, bits=encoding.precision)
#            result_list.append(result)
#        return AdditiveArrayShare(numpy.array([s.storage for s in result_list], dtype=object))


    def _verify_storage(self, operand):
        """Verify the storage in a secret share.

        Parameters
        ----------
        operand: :class:`AdditiveArrayShare`, required
            Secret shared array to be verified.

        Returns
        -------
        value: :class:`AdditiveArrayShare`
            The secret shared array.

        Raises
        ------
        :class:`ValueError`
            If `operand` can't be verified.
        """
        self._assert_unary_compatible(operand, "operand")
        self.field._verify(operand.storage)
        return operand


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
        operand: :class:`AdditiveArrayShare`, required
            Secret shared operand to which the zigmoid function will be applied.

        Returns
        -------
        result: :class:`AdditiveArrayShare`
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

