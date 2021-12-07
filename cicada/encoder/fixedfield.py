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

"""Functionality for encoding real values using integer fields.
"""

import numbers

import numpy

import cicada.math

class FixedFieldArray(cicada.math.FieldArray):
    def __new__(cls, other, *, modulus, precision):
        self = super().__new__(cls, other, modulus=modulus)

        if not isinstance(precision, numbers.Integral):
            raise ValueError(f"Expected integer precision, got {type(precision)} instead.") # pragma: no cover
        if precision < 0:
            raise ValueError(f"Expected non-negative precision, got {precision} instead.") # pragma: no cover

        self.precision = precision
        return self


    def __array_finalize__(self, other):
        if other is None:
            return
        self.modulus = getattr(other, "modulus", None)
        self.precision = getattr(other, "precision", None)


    def __reduce__(self):
        fn, fn_state, state = super(FixedFieldArray, self).__reduce__()
        return fn, fn_state, state + (self.precision,)


    def __setstate__(self, state):
        self.precision = state[-1]
        super(FixedFieldArray, self).__setstate__(state[:-1])


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
        less than 2^64 (i.e. 2**64-59).
    precision: :class:`int`, optional
        The number of bits reserved to store fractions in encoded values.  Defaults
        to 16.
    """
    def __init__(self, modulus=18446744073709551557, precision=16):
        self._field = cicada.math.Field(modulus=modulus)

        if not isinstance(precision, numbers.Integral):
            raise ValueError(f"Expected integer precision, got {type(precision)} instead.") # pragma: no cover
        if precision < 0:
            raise ValueError(f"Expected non-negative precision, got {precision} instead.") # pragma: no cover

        self._precision = precision
        self._scale = int(2**self._precision)


    def __eq__(self, other):
        return isinstance(other, FixedFieldEncoder) and self._field == other._field and self._precision == other._precision


    def __repr__(self):
        return f"cicada.encoder.FixedFieldEncoder(field={self._field!r}, precision={self._precision})" # pragma: no cover


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

        if not isinstance(array, FixedFieldArray):
            raise ValueError(f"{label} must be an instance of FixedFieldArray, got {type(array)} instead.") # pragma: no cover
        if array.modulus != self._modulus:
            raise ValueError(f"{label} modulus must be {self._modulus}, got {array.modulus} instead.") # pragma: no cover
        if array.precision != self._precision:
            raise ValueError(f"{label} precision must be {self._precision}, got {array.precision} instead.") # pragma: no cover

        return numpy.where(array > self._posbound, -(self._modulus - array) / self._scale, array / self._scale).astype(numpy.float64)


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
            array = numpy.asarray(array)

        if not all([abs(int(int(x)*self._scale)) < self._field.maxvalue for x in numpy.nditer(array, ["refs_ok"])]):
            raise ValueError("Value to be encoded is too large for representation in the field.") # pragma: no cover

        if array.ndim == 0:
            result = FixedFieldArray(int(array * self._scale) % self._modulus, modulus=self._field.modulus, precision=self._precision)
        else:
            result = FixedFieldArray([int(x) for x in numpy.nditer(array * self._scale, ["refs_ok"])], modulus=self._field.modulus, precision=self._precision).reshape(array.shape)

        return result


    @property
    def field(self):
        return self._field


    @property
    def precision(self):
        """Return the number of bits used to store fractional values."""
        return self._precision


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
        random: :class:`numpy.ndarray`
            Encoded array containing uniform random values with shape `size`.
        """
        values = []
        for index in range(int(numpy.prod(size))):
            values.append(int.from_bytes(generator.bytes(self.fieldbytes), 'big') % self._modulus)
        result = FixedFieldArray(values, modulus=self._modulus, precision=self._precision).reshape(size)
        return result


    def zeros(self, shape):
        """Return an encoded array of zeros.

        Parameters
        ----------
        shape: tuple, required
            The shape of the output array.

        Returns
        -------
        array: :class:`numpy.ndarray`
            Encoded array of zeros with shape `shape`.
        """
        result = FixedFieldArray(numpy.zeros(shape), modulus=self._modulus, precision=self._precision)
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
        result = FixedFieldArray(numpy.zeros(other.shape), modulus=self._modulus, precision=self._precision)
        return result


