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

"""Functionality for encoding and manipulating real values using integer fields.
"""

from math import log2, ceil
import numbers

import numpy


class FixedFieldEncoder(object):
    """Encodes real values as non-negative integers in a field with fixed precision.

    Encoded values are :class:`numpy.ndarray` instances containing Python
    integers, with `precision` bits reserved for encoding fractional digits.
    For a prime constant modulus, values greater than (modulus+1)/2 are
    interpreted to be negative.  Encoded values are decoded as 64-bit
    floating-point arrays.

    Parameters
    ----------
    modulus: :class:`int`, optional
        Field size for storing encoded values.  Defaults to the largest prime
        less than :math:`2^{64}`.
    precision: :class:`int`, optional
        The number of bits reserved to store fractions in encoded values.  Defaults
        to 16.
    """
    def __init__(self, modulus=18446744073709551557, precision=16):
        if not isinstance(modulus, numbers.Integral):
            raise ValueError(f"Expected integer modulus, got {type(modulus)} instead.") # pragma: no cover
        if modulus < 0:
            raise ValueError(f"Expected non-negative modulus, got {modulus} instead.") # pragma: no cover
        if not isinstance(precision, numbers.Integral):
            raise ValueError(f"Expected integer precision, got {type(precision)} instead.") # pragma: no cover
        if precision < 0:
            raise ValueError(f"Expected non-negative precision, got {precision} instead.") # pragma: no cover

        self._dtype = numpy.dtype(object)
        self._decoded_type = numpy.float64
        self._precision = precision
        self._scale = int(2**self._precision)
        self._modulus = modulus
        self._posbound = (modulus)//2
        self._fieldbits = modulus.bit_length()


    def __eq__(self, other):
        return isinstance(other, FixedFieldEncoder) and self._precision == other._precision and self._modulus == other._modulus


    def __repr__(self):
        return f"cicada.encoder.FixedFieldEncoder(modulus={self._modulus}, precision={self._precision})" # pragma: no cover


    def _assert_binary_compatible(self, lhs, rhs, lhslabel, rhslabel):
        self._assert_unary_compatible(lhs, lhslabel)
        self._assert_unary_compatible(rhs, rhslabel)


    def _assert_unary_compatible(self, array, label):
        if not isinstance(array, numpy.ndarray):
            raise ValueError(f"Expected {label} to be an instance of numpy.ndarray, got {type(array)} instead.") # pragma: no cover
        if array.dtype != self.dtype:
            raise ValueError(f"Expected {label} to be created with a compatible instance of this encoder.") # pragma: no cover

    def add(self, lhs, rhs):
        """Add two encoded arrays.

        Parameters
        ----------
        lhs: :class:`numpy.ndarray`, required
            First operand.
        rhs: :class:`numpy.ndarray`, required
            Second operand.
        Returns
        -------
        sum: :class:`numpy.ndarray`
            The sum of the two operands.
        """
        self._assert_binary_compatible(lhs, rhs, "lhs", "rhs")

        # We make an explicit copy and use in-place operators to avoid overflow
        # and/or unwanted conversion from a numpy scalar to a Python int.
        result = lhs.copy()
        result += rhs
        result %= self._modulus
        self._assert_unary_compatible(result, "result")
        return result


    def decode(self, array):
        """Convert encoded values to real values.

        Parameters
        ----------
        array: :class:`numpy.ndarray`, or :any:`None`, required
            Integer fixed point representation returned by :meth:`encode`.

        Returns
        -------
        decoded: :class:`numpy.ndarray`
            A floating point array with the same shape as the input, containing
            the decoded representation of `array`, or :any:`None` if the input
            was :any:`None`.
        """
        if array is None:
            return array

        self._assert_unary_compatible(array, "array")
        return numpy.where(array > self._posbound, -(self._modulus - array) / self._scale, array / self._scale).astype(numpy.float64)


    @property
    def dtype(self):
        """Return the :class:`numpy.dtype` used for arrays encoded with this encoder."""
        return self._dtype


    def encode(self, array):
        """Convert array to a fixed point integer representation.

        Parameters
        ----------
        array: :class:`numpy.ndarray` or :any:`None`, required
            The array to convert.

        Returns
        -------
        encoded: :class:`numpy.ndarray` or :any:`None`
            Encoded array with the same shape as the input, containing the
            fixed precision integer representation of `array`, or :any:`None`
            if the input was :any:`None`.
        """
        if array is None:
            return array

        if not isinstance(array, numpy.ndarray):
            raise ValueError("Value to be encoded must be an instance of numpy.ndarray.") # pragma: no cover
        if not all([abs(int(int(x)*self._scale)) < self._posbound for x in numpy.nditer(array, ['refs_ok'])]):
            raise ValueError("Value to be encoded is too large for representation in the field.") # pragma: no cover

        if array.ndim == 0:
            result = numpy.array(int(array * self._scale) % self._modulus, dtype=self.dtype)
        else:
            result = numpy.array([int(x) for x in numpy.nditer(array * self._scale)], dtype=self.dtype).reshape(array.shape)

        self._assert_unary_compatible(result, "result")
        return result


    @property
    def fieldbits(self):
        """Return the number of bits required to store field values."""
        return self._fieldbits


    @property
    def fieldbytes(self):
        """Return the number of bytes required to store field values."""
        return ceil(self._fieldbits / 8)


    def inplace_add(self, lhs, rhs):
        """In-place addition of an encoded array.

        Parameters
        ----------
        lhs: :class:`numpy.ndarray`, required
            First operand.

        rhs: :class:`numpy.ndarray`, required
            Second operand.  This value will be added in-place to `lhs`.
        """
        self._assert_binary_compatible(lhs, rhs, "lhs", "rhs")
        lhs += rhs
        lhs %= self._modulus


    def inplace_subtract(self, lhs, rhs):
        """In-place subtraction of an encoded array.

        Parameters
        ----------
        lhs: :class:`numpy.ndarray`, required
            First operand.

        rhs: :class:`numpy.ndarray`, required
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
        array: :class:`numpy.ndarray`, required
            The array to negate.

        Returns
        -------
        negated: :class:`numpy.ndarray`
            Array with the same shape as `array`, containing the negated
            elements.
        """
        self._assert_unary_compatible(array, "array")
        result = numpy.array((0 - array) % self._modulus, dtype=self.dtype)
        self._assert_unary_compatible(result, "result")
        return result


    @property
    def precision(self):
        """Return the number of bits used to store fractional values."""
        return self._precision


    def subtract(self, lhs, rhs):
        """ Subtraction of two encoded arrays.

        Parameters
        ----------
        lhs: :class:`numpy.ndarray`, required
            First operand.
        rhs: :class:`numpy.ndarray`, required
            Second operand.
        Returns
        -------
        dif: :class:`numpy.ndarray`
            The difference of the two operands.
        """
        self._assert_binary_compatible(lhs, rhs, "lhs", "rhs")
        result = numpy.array((lhs - rhs) % self._modulus, dtype=self.dtype)
        self._assert_unary_compatible(result, "result")
        return result


    def sum(self, operand):
        """Sum array elements.

        Parameters
        ----------
        operand: :class:`numpy.ndarray`, required
            Operand.

        Returns
        -------
        sum: :class:`numpy.ndarray`
            The sum of the input array elements.
        """
        self._assert_unary_compatible(operand, "operand")
        result = numpy.array(numpy.sum(operand, axis=None) % self._modulus, dtype=self.dtype)
        self._assert_unary_compatible(result, "result")
        return result


    def uniform(self, *, size, generator):
        """Return a random encoded array, uniformly distributed over the ring.

        Parameters
        ----------
        size: :class:`tuple`, required
            A tuple defining the shape of the output array.
        generator: :class:`numpy.random.Generator`, required
            A psuedorandom number generator for sampling.

        Returns
        -------
        random: :class:`numpy.ndarray`
            Encoded array containing uniform random values with shape `size`.
        """
        elements = int(numpy.prod(size))
        elementbytes = self.fieldbytes
        randombytes = generator.bytes(elements * elementbytes)

        values = [int.from_bytes(randombytes[start : start+elementbytes], "big") for start in range(0, elements * elementbytes, elementbytes)]
        result = numpy.array(values, dtype=self.dtype).reshape(size)
        self._assert_unary_compatible(result, "result")
        return result


    def untruncated_matvec(self, A, x):
        """Return a matrix-vector product, without truncation.

        The results are shifted to the left by :attr:`precision` bits,
        which we refer to as `untruncated` values.  To recover the actual
        values, the results should be shifted to the right by :attr:`precision`
        bits.

        Note
        ----
        Shifting untruncated shares of secret shared values will produce
        nonsense results!  See
        :meth:`cicada.additive.AdditiveProtocolSuite.truncate` for a way to truncate
        untruncated secret shared values.

        Parameters
        ----------
        A: :class:`numpy.ndarray`, required
           Encoded :math:`M \\times N` matrix.
        x: :class:`numpy.ndarray`, required
           Encoded size :math:`N` vector.

        Returns
        -------
        y: :class:`numpy.ndarray`
           Encoded, untruncated size :math:`M` vector.
        """
        self._assert_binary_compatible(A, x, "A", "x")
        result = numpy.array(numpy.dot(A, x), dtype=self.dtype)
        self._assert_unary_compatible(result, "result")
        return result


    def untruncated_multiply(self, lhs, rhs):
        """Multiply two arrays element-wise, without truncation.

        The results are shifted to the left by :attr:`precision` bits,
        which we refer to as `untruncated` values.  To recover the actual
        values, the results should be shifted to the right by :attr:`precision`
        bits.

        Note
        ----
        Shifting untruncated shares of secret shared values will produce
        nonsense results!  See
        :meth:`cicada.additive.AdditiveProtocolSuite.truncate` for a way to truncate
        untruncated secret shared values.


        Parameters
        ----------
        lhs: :class:`numpy.ndarray`, required
            First operand.
        rhs: :class:`numpy.ndarray`, required
            Second operand.

        Returns
        -------
        product: :class:`numpy.ndarray`
            Encoded, untruncated elementwise product of `lhs` and `rhs`.
        """
        self._assert_binary_compatible(lhs, rhs, "lhs", "rhs")
        result = numpy.array((lhs * rhs) % self._modulus, dtype=self.dtype)
        self._assert_unary_compatible(result, "result")
        return result


    def zeros(self, shape):
        """Return an encoded array of zeros.

        Parameters
        ----------
        shape: :class:`tuple`, required
            The shape of the output array.

        Returns
        -------
        array: :class:`numpy.ndarray`
            Encoded array of zeros with shape `shape`.
        """
        result = numpy.zeros(shape, dtype=self.dtype)
        self._assert_unary_compatible(result, "result")
        return result


    def zeros_like(self, other):
        """Return an encoded array of zeros with the same shape as another array.

        Parameters
        ----------
        other: :class:`numpy.ndarray`, required
            The result will have the same shape as this array.

        Returns
        -------
        array: :class:`numpy.ndarray`
            Encoded array of zeros with the same shape as `other`.
        """
        result = numpy.zeros(other.shape, dtype=self.dtype)
        self._assert_unary_compatible(result, "result")
        return result


