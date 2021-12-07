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

"""Functionality for encoding and manipulating binary values in integer fields.
"""

import numbers

import numpy

import cicada.math


class BinaryFieldArray(cicada.math.FieldArray):
    def __new__(cls, other, *, modulus):
        self = super().__new__(cls, other, modulus=modulus)
        return self


class BinaryFieldEncoder(object):
    """Encodes binary values as non-negative integers in a field.

    Encoded values are :class:`BinaryFieldArray` instances containing Python
    integers.  For a prime constant modulus, values greater than (modulus+1)/2
    are interpreted to be negative.  Encoded values are decoded as 64-bit
    integer arrays.

    Parameters
    ----------
    modulus: :class:`int`, optional
        Field size for storing encoded values.  Defaults to the largest prime
        less than 2^64 (i.e. 2**64-59).
    """
    def __init__(self, modulus=18446744073709551557):
        self._field = cicada.math.Field(modulus=modulus)


    def __eq__(self, other):
        return isinstance(other, BinaryFieldEncoder) and self._field == other._field


    def __repr__(self):
        return f"BinaryFieldEncoder(field={self._field!r})" # pragma: no cover


    def decode(self, array):
        """Convert encoded values to real values.

        Parameters
        ----------
        array: :class:`BinaryFieldArray`, or :any:`None`, required
            Binary field representation returned by :meth:`encode`.

        Returns
        -------
        decoded: :class:`numpy.ndarray`
            An integer array with the same shape as the input, containing
            the decoded representation of `array`, or :any:`None` if the input
            was :any:`None`.
        """
        if array is None:
            return array

        if not isinstance(array, BinaryFieldArray):
            raise ValueError(f"Expected BinaryFieldArray, got {type(array)} instead.") # pragma: no cover
        if array.modulus != self._field.modulus:
            raise ValueError(f"Expected modulus {self._field.modulus}, got {array.modulus} instead.") # pragma: no cover
        if not numpy.all(numpy.isin(array, [0, 1])):
            raise ValueError("Values to be decoded must be 0 or 1.") # pragma: no cover

        return array.astype(numpy.int64)


    def encode(self, array):
        """Convert binary values to encoded values.

        Parameters
        ----------
        array: array-like object, or :any:`None`, required
            The array to convert.

        Returns
        -------
        encoded: :class:`BinaryFieldArray` or :any:`None`
            Encoded array with the same shape as the input, containing the
            field representation of `array`, or :any:`None` if the input was
            :any:`None`.
        """
        if array is None:
            return array

        if not isinstance(array, numpy.ndarray):
            array = numpy.asarray(array, dtype=numpy.int64)

        if not numpy.all(numpy.isin(array, [0, 1])):
            raise ValueError("Values to be encoded must be 0 or 1.") # pragma: no cover

        return BinaryFieldArray(array, modulus=self._field.modulus)


    @property
    def field(self):
        return self._field


