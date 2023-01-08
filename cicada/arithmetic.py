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

"""Functionality for working with field arithmetic.
"""

from math import log2, ceil
import numbers

import numpy


class Field(object):
    """Performs arithmetic in an integer field.

    Field values are :class:`numpy.ndarray` instances containing Python
    integers.

    Parameters
    ----------
    order: :class:`int`, optional
        Field size.  Defaults to the largest prime less than :math:`2^{64}`.
    """
    def __init__(self, order=None):
        if order is None:
            order = 18446744073709551557
        else:
            if not isinstance(order, numbers.Integral):
                raise ValueError(f"Expected integer order, got {type(order)} instead.") # pragma: no cover
            if order < 0:
                raise ValueError(f"Expected non-negative order, got {order} instead.") # pragma: no cover
            if not self._is_prob_prime(order):
                raise ValueError(f"Expected order to be prime, got a composite instead.")

        self._dtype = numpy.dtype(object)
        self._decoded_type = numpy.float64
        self._order = order
        self._fieldbits = order.bit_length()


    def __eq__(self, other):
        return isinstance(other, Field) and self._order == other._order


    def __repr__(self):
        return f"cicada.arithmetic.Field(order={self._order})" # pragma: no cover


    def _assert_binary_compatible(self, lhs, rhs, lhslabel, rhslabel):
        self._assert_unary_compatible(lhs, lhslabel)
        self._assert_unary_compatible(rhs, rhslabel)


    def _assert_unary_compatible(self, array, label):
        if not isinstance(array, numpy.ndarray):
            raise ValueError(f"Expected {label} to be an instance of numpy.ndarray, got {type(array)} instead.") # pragma: no cover
        if array.dtype != self.dtype:
            raise ValueError(f"Expected {label} to be created with a compatible instance of this encoder.") # pragma: no cover

    def __call__(self, array):
        return numpy.array(array, dtype=self._dtype)


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
        result %= self._order
        self._assert_unary_compatible(result, "result")
        return result


    @property
    def dtype(self):
        """Return the :class:`numpy.dtype` used for arrays encoded with this encoder."""
        return self._dtype


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
        lhs %= self._order


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
        lhs %= self._order

    def _is_prob_prime(self, n):# Rabin-Miller probabalistic primality test
        """
        Miller-Rabin primality test.

        A return value of False means n is certainly not prime. A return value of
        True means n is very likely a prime.
        """
        if not isinstance(n, int):
            raise ValueError('Expected argument to primality test to be integral')
            return False
        if n in [0,1,4,6,8,9]:
            return False

        if n in [2,3,5,7]:
            return True

        s = 0
        d = n-1
        while d%2==0:
            d>>=1
            s+=1
        assert(2**s * d == n-1)

        def trial_composite(a):
            if pow(a, d, n) == 1:
                return False
            for i in range(s):
                if pow(a, 2**i * d, n) == n-1:
                    return False
            return True
        num_bytes = ceil(log2(n)/8)
        for i in range(32):#number of trials more means higher accuracy - 32 -> error probability ~4^-32 ~2^-64
            a =0
            while a == 0 or a == 1:
                a = int.from_bytes(numpy.random.bytes(num_bytes), 'big')%n
            if trial_composite(a):
                return False

        return True

    @property
    def order(self):
        """Return the field order."""
        return self._order


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
        result = numpy.array((0 - array) % self._order, dtype=self.dtype)
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
        result = numpy.array((lhs - rhs) % self._order, dtype=self.dtype)
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
        result = numpy.array(numpy.sum(operand, axis=None) % self._order, dtype=self.dtype)
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
        result = numpy.array((lhs * rhs) % self._order, dtype=self.dtype)
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

