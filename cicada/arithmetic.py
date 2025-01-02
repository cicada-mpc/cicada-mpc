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

import copy
import inspect
import math
import numbers
import types

import numpy


class Field(object):
    """Performs arithmetic in an integer field.

    Field arrays are :class:`numpy.ndarray` instances containing Python
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
                raise ValueError(f"Expected integer order, got {type(order)} instead.")
            if order < 0:
                raise ValueError(f"Expected non-negative order, got {order} instead.")
            if not self._is_prob_prime(order):
                raise ValueError(f"Expected order to be prime, got a composite instead.")

        self._dtype = numpy.dtype(object)
        self._order = order
        self._bits = order.bit_length()


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
            raise ValueError(f"Expected {label} to be created with a compatible instance of this field.") # pragma: no cover

    def __call__(self, object):
        """Create a field array from an :term:`array-like` object.

        Parameters
        ----------
        object: :term:`array-like`, required
            The array to be converted.

        Returns
        -------
        array: :class:`numpy.ndarray`
            The corresponding field array.
        """
        array = numpy.array(object, dtype=self._dtype)
        array %= self._order
        return array


    def add(self, lhs, rhs):
        """Element-wise addition of two field arrays.

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
        # and to prevent unwanted conversion from a numpy scalar to a Python int.
        result = lhs.copy()
        result += rhs
        result %= self._order
        self._assert_unary_compatible(result, "result")
        return result


    @property
    def dtype(self):
        """Return the :class:`numpy.dtype` used for field arrays."""
        return self._dtype


    @property
    def bits(self):
        """Return the number of bits required to store field values."""
        return self._bits


    @property
    def bytes(self):
        """Return the number of bytes required to store field values."""
        return math.ceil(self._bits / 8)


    def full_like(self, other, fill_value):
        """Return a field array of values with the same shape as another array.

        Parameters
        ----------
        other: :term:`array-like`, required
            The result will have the same shape as this array.
        fill_value: :class:`int`, required
            Field value that will be assigned to every element in the result array.

        Returns
        -------
        array: :class:`numpy.ndarray`
            Field array of `fill_value` with the same shape as `other`.
        """
        result = numpy.full_like(other, fill_value, dtype=self.dtype)
        self._assert_unary_compatible(result, "result")
        return result


    def inplace_add(self, lhs, rhs):
        """Add field arrays in-place.

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
        """Subtract field arrays in-place.

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
            return False # pragma: no cover
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
        num_bytes = math.ceil(math.log2(n)/8)
        for i in range(32):#number of trials more means higher accuracy - 32 -> error probability ~4^-32 ~2^-64
            a =0
            while a == 0 or a == 1:
                a = int.from_bytes(numpy.random.bytes(num_bytes), 'big')%n
            if trial_composite(a):
                return False

        return True


    def multiply(self, lhs, rhs):
        """Element-wise multiplication of two field arrays.

        Parameters
        ----------
        lhs: :class:`numpy.ndarray`, required
            First operand.
        rhs: :class:`numpy.ndarray`, required
            Second operand.

        Returns
        -------
        product: :class:`numpy.ndarray`
            Element-wise product of `lhs` and `rhs`.
        """
        self._assert_binary_compatible(lhs, rhs, "lhs", "rhs")
        result = numpy.array((lhs * rhs) % self._order, dtype=self.dtype)
        self._assert_unary_compatible(result, "result")
        return result


    def negative(self, array):
        """Element-wise negation of a field array.

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


    def ones(self, shape):
        """Return a field array containing ones.

        Parameters
        ----------
        shape: :class:`tuple`, required
            The shape of the output array.

        Returns
        -------
        array: :class:`numpy.ndarray`
            Field array of ones with shape `shape`.
        """
        result = numpy.ones(shape, dtype=self.dtype)
        self._assert_unary_compatible(result, "result")
        return result


    def ones_like(self, other):
        """Return a field array of ones with the same shape as another array.

        Parameters
        ----------
        other: :term:`array-like`, required
            The result will have the same shape as this array.

        Returns
        -------
        array: :class:`numpy.ndarray`
            Field array of zeros with the same shape as `other`.
        """
        return self.ones(other.shape)


    @property
    def order(self):
        """Return the field order."""
        return self._order


    @property
    def posbound(self):
        """Return the boundary between positive and negative values."""
        return self._order // 2


    def subtract(self, lhs, rhs):
        """Return the element-wise difference between two field arrays.

        Parameters
        ----------
        lhs: :class:`numpy.ndarray`, required
            First operand.
        rhs: :class:`numpy.ndarray`, required
            Second operand.
        Returns
        -------
        dif: :class:`numpy.ndarray`
            The difference between the two operands.
        """
        self._assert_binary_compatible(lhs, rhs, "lhs", "rhs")
        result = numpy.array((lhs - rhs) % self._order, dtype=self.dtype)
        self._assert_unary_compatible(result, "result")
        return result


    def sum(self, operand):
        """Sum the elements of a field array.

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
        """Return a random field array, uniformly distributed over the field.

        Parameters
        ----------
        size: :class:`tuple`, required
            A tuple defining the shape of the output array.
        generator: :class:`numpy.random.Generator`, required
            A psuedorandom number generator for sampling.

        Returns
        -------
        random: :class:`numpy.ndarray`
            Field array containing uniform random values with shape `size`.
        """
        elements = int(numpy.prod(size))
        elementbytes = self.bytes
        randombytes = generator.bytes(elements * elementbytes)

        values = [int.from_bytes(randombytes[start : start+elementbytes], "big") % self._order for start in range(0, elements * elementbytes, elementbytes)]
        result = numpy.array(values, dtype=self.dtype).reshape(size)
        self._assert_unary_compatible(result, "result")
        return result


    def _verify(self, array):
        """Verify the given array for correctness.

        Parameters
        ----------
        array: :class:`numpy.ndarray`, required
            A field array created with a compatible field.

        Returns
        -------
        array: :class:`numpy.ndarray`
            The verified array.

        Raises
        ------
        :class:`ValueError`
            If `array` is not a valid field array created with a compatible field.
        """
        if not isinstance(array, numpy.ndarray):
            raise ValueError(f"Expected array to be an instance of numpy.ndarray, got {type(array)} instead.") # pragma: no cover
        if array.dtype != self.dtype:
            raise ValueError(f"Expected array dtype to be object, got {array.dtype} instead.") # pragma: no cover
        for index in numpy.ndindex(array.shape):
            if not isinstance(array[index], int):
                raise ValueError(f"All array values must be type 'int', value at index {index} is {type(array[index])}.") # pragma: no cover

        return array


    def zeros(self, shape):
        """Return a field array containing zeros.

        Parameters
        ----------
        shape: :class:`tuple`, required
            The shape of the output array.

        Returns
        -------
        array: :class:`numpy.ndarray`
            Field array of zeros with shape `shape`.
        """
        result = numpy.zeros(shape, dtype=self.dtype)
        self._assert_unary_compatible(result, "result")
        return result


    def zeros_like(self, other):
        """Return a field array of zeros with the same shape as another array.

        Parameters
        ----------
        other: :term:`array-like`, required
            The result will have the same shape as this array.

        Returns
        -------
        array: :class:`numpy.ndarray`
            Field array of zeros with the same shape as `other`.
        """
        result = numpy.zeros(other.shape, dtype=self.dtype)
        self._assert_unary_compatible(result, "result")
        return result


def field(order):
    def __add__(self, other):
        return ((numpy.asarray(self) + other) % type(self).order).view(type(self))

    def __iadd__(self, other):
        storage = numpy.asarray(self)
        storage += other
        storage %= type(self).order
        return self

    def __imul__(self, other):
        storage = numpy.asarray(self)
        storage *= other
        storage %= type(self).order
        return self

    def __isub__(self, other):
        storage = numpy.asarray(self)
        storage -= other
        storage %= type(self).order
        return self

    def __mul__(self, other):
        return ((numpy.asarray(self) * other) % type(self).order).view(type(self))

    def __new__(cls, array):
        return numpy.asarray(array, dtype=object).view(cls)

    def __repr__(self):
        return f"FieldArray({self.tolist()!r}, order={type(self).order})"

    def __sub__(self, other):
        return ((numpy.asarray(self) - other) % type(self).order).view(type(self))

    def negative(self):
        return (0 - self) % type(self).order

    def sum(self, axis=None, **kwargs):
        return numpy.asarray(numpy.asarray(self).sum(axis=axis) % type(self).order).view(type(self))

    class FieldMeta(type):
        def __new__(cls, name, bases, dct):
            instance = super().__new__(cls, name, bases, dct)
            instance.__add__ = __add__
            instance.__iadd__ = __iadd__
            instance.__imul__ = __imul__
            instance.__isub__ = __isub__
            instance.__mul__ = __mul__
            instance.__neg__ = negative
            instance.__new__ = __new__
            instance.__repr__ = __repr__
            instance.__sub__ = __sub__
            instance.negative = negative
            instance.sum = sum
            return instance

        def __repr__(cls):
            return f"Field(order={cls.order})"

        @property
        def bits(cls):
            return cls.order.bit_length()

        @property
        def bytes(cls):
            return math.ceil(cls.bits / 8)

        def full(cls, shape, fill):
            fill = int(fill) % cls.order
            return numpy.full(shape, fill, dtype=object).view(cls)

        def full_like(cls, other, fill):
            fill = int(fill) % cls.order
            return numpy.full_like(other, fill, dtype=object).view(cls)

        def ones(cls, shape):
            return numpy.ones(shape, dtype=object).view(cls)

        def ones_like(cls, other):
            return numpy.ones_like(other, dtype=object).view(cls)

        def uniform(cls, *, size, generator):
            count = numpy.prod(size)
            randombytes = generator.bytes(count * cls.bytes)
            indices = zip(numpy.arange(count) * cls.bytes, (numpy.arange(count)+1) * cls.bytes)
            values = [int.from_bytes(randombytes[start:end], "big") % cls.order for start, end in indices]
            return cls(values).reshape(size)

        def zeros(cls, shape):
            return numpy.zeros(shape, dtype=object).view(cls)

        def zeros_like(cls, other):
            return numpy.zeros_like(other, dtype=object).view(cls)

    FieldMeta.dtype = object
    FieldMeta.order = order

    return types.new_class("FieldArray", (numpy.ndarray,), dict(metaclass=FieldMeta))

