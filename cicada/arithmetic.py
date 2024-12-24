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

import math

import galois
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

        if not galois.is_prime(order):
            raise ValueError(f"Field order must be prime.")

        self._field = galois.GF(order)


    def __eq__(self, other):
        return isinstance(other, Field) and self._field is other._field


    def __repr__(self):
        return f"cicada.arithmetic.Field(order={self.order})" # pragma: no cover


    def _assert_binary_compatible(self, lhs, rhs, lhslabel, rhslabel):
        self._assert_unary_compatible(lhs, lhslabel)
        self._assert_unary_compatible(rhs, rhslabel)


    def _assert_unary_compatible(self, array, label):
        if not isinstance(array, self._field):
            raise ValueError(f"Expected {label} to be created with this field or a compatible field.") # pragma: no cover


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
        return self._field(object)


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
        return lhs + rhs


    @property
    def bits(self):
        """Return the number of bits required to store field values."""
        return self._field.order.bit_length()


    @property
    def bytes(self):
        """Return the number of bytes required to store field values."""
        return math.ceil(self._field.order.bit_length() / 8)


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
        return self._field(numpy.full_like(other, fill_value))


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
        return lhs * rhs


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
        return numpy.negative(array)


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
        return self._field.Ones(shape)


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
        return self._field.Ones(other.shape)


    @property
    def order(self):
        """Return the field order."""
        return self._field.order


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
        return lhs - rhs


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
        return numpy.sum(operand)


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
        return self._field.Random(shape=size, seed=generator)


    def _verify(self, array):
        """Verify the given array for correctness.

        Parameters
        ----------
        array: :class:`galois.FieldArray`, required
            A field array created with a compatible field.

        Returns
        -------
        array: :class:`galois.FieldArray`
            The verified array.

        Raises
        ------
        :class:`ValueError`
            If `array` is not a valid field array created with a compatible field.
        """
        if not isinstance(array, self._field):
            raise ValueError(f"Expected array to be created with this field or a compatible field.") # pragma: no cover
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
        return self._field.Zeros(shape)


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
        return self._field.Zeros(other.shape)


