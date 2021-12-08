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

"""Functionality for manipulating integer fields.
"""

import logging
import math
import numbers

import numpy


log = logging.getLogger(__name__)


class FieldArray(numpy.ndarray):
    def __new__(cls, other, *, modulus=None):
        if isinstance(other, FieldArray):
            modulus = other.modulus
        elif modulus is None:
            raise ValueError("Field modulus must be specified.") # pragma: no cover
        if not isinstance(modulus, numbers.Integral):
            raise ValueError(f"Expected integer modulus, got {type(modulus)} instead.") # pragma: no cover
        if modulus < 1:
            raise ValueError(f"Expected positive modulus, got {modulus} instead.") # pragma: no cover

        if not isinstance(other, numpy.ndarray):
            other = numpy.array(other, dtype=object)
        if other.ndim == 0:
            other = numpy.array(int(other) % modulus, dtype=object)
        else:
            other = numpy.array([int(x) % modulus for x in numpy.nditer(other, flags=["refs_ok"])], dtype=object).reshape(other.shape)

        self = other.view(cls) # Calls __array_finalize__() with `other`
        self.modulus = modulus
        return self


    def __array_finalize__(self, other):
        self.modulus = getattr(other, "modulus", None)


    def __reduce__(self):
        fn, fn_state, state = super(FieldArray, self).__reduce__()
        return fn, fn_state, state + (self.modulus,)


    def __setstate__(self, state):
        self.modulus = state[-1]
        super(FieldArray, self).__setstate__(state[:-1])


class Field(object):
    """Manipulates values from a field of non-negative integers.

    Parameters
    ----------
    modulus: :class:`int`, optional
        Field size.  Defaults to the largest prime less than 2^64 (i.e.
        2**64-59).
    """
    def __init__(self, modulus=18446744073709551557):
        if not isinstance(modulus, numbers.Integral):
            raise ValueError(f"Expected integer modulus, got {type(modulus)} instead.") # pragma: no cover
        if modulus < 0:
            raise ValueError(f"Expected non-negative modulus, got {modulus} instead.") # pragma: no cover

        self._fieldbits = modulus.bit_length()
        self._modulus = modulus
        self._maxpositive = modulus // 2


    def __eq__(self, other):
        return isinstance(other, Field) and self._modulus == other._modulus


    def __repr__(self):
        return f"Field(modulus={self._modulus})" # pragma: no cover


    def _assert_compatible(self, array, label):
        if not isinstance(array, FieldArray):
            raise ValueError(f"{label} must be an instance of FieldArray, got {type(array)} instead.") # pragma: no cover
        if array.modulus != self._modulus:
            raise ValueError(f"{label} modulus must be {self._modulus}, got {array.modulus} instead.") # pragma: no cover

    def _assert_binary_compatible(self, lhs, rhs, lhslabel, rhslabel):
        self._assert_compatible(lhs, lhslabel)
        self._assert_compatible(rhs, rhslabel)
        if lhs.shape != rhs.shape:
            raise ValueError(f"{lhslabel} and {rhslabel} shapes should match, got {lhs.shape} and {rhs.shape} instead.") # pragma: no cover


    def add(self, lhs, rhs):
        """Add two encoded arrays.

        Parameters
        ----------
        lhs: :class:`FieldArray`, required
            First operand.
        rhs: :class:`FieldArray`, required
            Second operand.
        Returns
        -------
        sum: :class:`FieldArray`
            The sum of the two operands.
        """
        self._assert_binary_compatible(lhs, rhs, "lhs", "rhs")

        # We make an explicit copy and use in-place operators to avoid overflow
        # and/or unwanted conversion from a numpy scalar to a Python int.
        result = lhs.copy()
        result += rhs
        result %= self._modulus
        return result


    def dot(self, A, x):
        """Return a matrix-vector product, without truncation.

        The results are shifted to the left by :attr:`precision` bits,
        which we refer to as `untruncated` values.  To recover the actual
        values, the results should be shifted to the right by :attr:`precision`
        bits.

        Note
        ----
        Shifting untruncated shares of secret shared values will produce
        nonsense results!  See
        :meth:`cicada.additive.AdditiveProtocol.truncate` for a way to truncate
        untruncated secret shared values.

        Parameters
        ----------
        A: :class:`FieldArray`, required
           Encoded :math:`M \\times N` matrix.
        x: :class:`FieldArray`, required
           Encoded size :math:`N` vector.

        Returns
        -------
        y: :class:`FieldArray`
           Encoded, untruncated size :math:`M` vector.
        """
        self._assert_compatible(A, "A")
        self._assert_compatible(x, "x")
        return FieldArray(numpy.dot(A, x) % self._modulus, modulus=self._modulus)


    @property
    def fieldbits(self):
        """Return the number of bits required to store field values."""
        return self._fieldbits


    @property
    def fieldbytes(self):
        """Return the number of bytes required to store field values."""
        return math.ceil(self._fieldbits / 8)


    def inplace_add(self, lhs, rhs):
        """In-place addition of an encoded array.

        Parameters
        ----------
        lhs: :class:`FieldArray`, required
            First operand.

        rhs: :class:`FieldArray`, required
            Second operand.  This value will be added in-place to `lhs`.
        """
        self._assert_binary_compatible(lhs, rhs, "lhs", "rhs")
        lhs += rhs
        lhs %= self._modulus


    def inplace_subtract(self, lhs, rhs):
        """In-place subtraction of an encoded array.

        Parameters
        ----------
        lhs: :class:`FieldArray`, required
            First operand.

        rhs: :class:`FieldArray`, required
            Second operand.  This value will be subtracted in-place from `lhs`.
        """
        self._assert_binary_compatible(lhs, rhs, "lhs", "rhs")
        lhs -= rhs
        lhs %= self._modulus


    @property
    def modulus(self):
        """Return the field size (modulus)."""
        return self._modulus


    def negative(self, array):
        """Element-wise numerical negative.

        Parameters
        ----------
        array: :class:`FieldArray`, required
            The array to negate.

        Returns
        -------
        negated: :class:`FieldArray`
            Array with the same shape as `array`, containing the negated
            elements.
        """
        self._assert_compatible(array, "array")
        return FieldArray((0 - array) % self._modulus, modulus=self._modulus)


    @property
    def maxpositive(self):
        return self._maxpositive


    def multiply(self, lhs, rhs):
        """Multiply two field arrays element-wise.

        Parameters
        ----------
        lhs: :class:`FieldArray`, required
            First operand.
        rhs: :class:`FieldArray`, required
            Second operand.

        Returns
        -------
        product: :class:`FieldArray`
            Elementwise product of `lhs` and `rhs`.
        """
        self._assert_binary_compatible(lhs, rhs, "lhs", "rhs")
        return FieldArray((lhs * rhs) % self._modulus, modulus=self._modulus)


    def subtract(self, lhs, rhs):
        """ Subtraction of two encoded arrays.

        Parameters
        ----------
        lhs: :class:`FieldArray`, required
            First operand.
        rhs: :class:`FieldArray`, required
            Second operand.
        Returns
        -------
        dif: :class:`FieldArray`
            The difference of the two operands.
        """
        self._assert_binary_compatible(lhs, rhs, "lhs", "rhs")
        return FieldArray((lhs - rhs) % self._modulus, modulus=self._modulus)


    def uniform(self, *, size, generator):
        """Return a random encoded array, uniformly distributed over the field.

        Parameters
        ----------
        size: tuple, required
            A tuple defining the shape of the output array.
        generator: :class:`numpy.random.Generator`, required
            A psuedorandom number generator for sampling.

        Returns
        -------
        random: :class:`FieldArray`
            Encoded array containing uniform random values with shape `size`.
        """
        values = []
        for index in range(int(numpy.prod(size))):
            values.append(int.from_bytes(generator.bytes(self.fieldbytes), "big") % self._modulus)
        return FieldArray(values, modulus=self._modulus).reshape(size)


    def zeros(self, shape):
        """Return an encoded array of zeros.

        Parameters
        ----------
        shape: tuple, required
            The shape of the output array.

        Returns
        -------
        array: :class:`FieldArray`
            Encoded array of zeros with shape `shape`.
        """
        return FieldArray(numpy.zeros(shape), modulus=self._modulus)


    def zeros_like(self, other):
        """Return an encoded array of zeros with the same shape as another array.

        Parameters
        ----------
        other: :class:`FieldArray`, required
            The result will have the same shape as this array.

        Returns
        -------
        array: :class:`FieldArray`
            Encoded array of zeros with the same shape as `other`.
        """
        return FieldArray(numpy.zeros(other.shape), modulus=self._modulus)


