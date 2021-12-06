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


class BinaryFieldArray(numpy.ndarray):
    def __new__(cls, other, *, modulus):
        if not isinstance(modulus, numbers.Integral):
            raise ValueError(f"Expected integer modulus, got {type(modulus)} instead.") # pragma: no cover
        if modulus < 0:
            raise ValueError(f"Expected non-negative modulus, got {modulus} instead.") # pragma: no cover

        self = numpy.asarray(other, dtype=numpy.dtype(numpy.object)).view(cls)
        self.modulus = modulus
        return self


    def __array_finalize__(self, other):
        if other is None:
            return
        self.modulus = getattr(other, "modulus", None)


    def __reduce__(self):
        fn, fn_state, state = super(FixedFieldArray, self).__reduce__()
        return fn, fn_state, state + (self.modulus,)


    def __setstate__(self, state):
        self.modulus = state[-1]
        super(FixedFieldArray, self).__setstate__(state[:-1])


class BinaryFieldEncoder(object):
    """Encodes binary values as non-negative integers in a field.

    Encoded values are :class:`BinaryFieldArray` instances containing Python
    integers.
    For a prime constant modulus, values greater than (modulus+1)/2 are
    interpreted to be negative.  Encoded values are decoded as 64-bit
    integer arrays.

    Parameters
    ----------
    modulus: :class:`int`, optional
        Field size for storing encoded values.  Defaults to the largest prime
        less than 2^64 (i.e. 2**64-59).
    """
    def __init__(self, modulus=18446744073709551557):
        if not isinstance(modulus, numbers.Integral):
            raise ValueError(f"Expected integer modulus, got {type(modulus)} instead.") # pragma: no cover
        if modulus < 2:
            raise ValueError(f"Expected modulus > 1, got {modulus} instead.") # pragma: no cover

        self._modulus = modulus


    def __eq__(self, other):
        return isinstance(other, BinaryFieldEncoder) and self._modulus == other._modulus


    def __repr__(self):
        return f"cicada.encoder.BinaryFieldEncoder(modulus={self._modulus})" # pragma: no cover


    def _assert_compatible(self, array, label):
        if not isinstance(array, BinaryFieldArray):
            raise ValueError(f"{label} must be an instance of BinaryFieldArray, got {type(array)} instead.") # pragma: no cover
        if array.modulus != self._modulus:
            raise ValueError(f"{label} modulus must be {self._modulus}, got {array.modulus} instead.") # pragma: no cover


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

        self._assert_compatible(array, "array")
        return array.astype(numpy.int64)


    def encode(self, array):
        """Convert binary values to encoded values.

        Parameters
        ----------
        array: :class:`numpy.ndarray` or :any:`None`, required
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
            raise ValueError("Value to be encoded must be an instance of numpy.ndarray.") # pragma: no cover

        if not numpy.all(numpy.isin(array, [0, 1])):
            raise ValueError("Values to be encoded must be 0 or 1.") # pragma: no cover

        if array.ndim == 0:
            result = BinaryFieldArray(int(array) % self._modulus, modulus=self._modulus)
        else:
            result = BinaryFieldArray([int(x) for x in numpy.nditer(array)], modulus=self._modulus).reshape(array.shape)

        self._assert_compatible(result, "result")
        return result


