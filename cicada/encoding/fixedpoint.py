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

"""Functionality for encoding real values in fields using a fixed precision representation."""

import numbers

import numpy


class FixedPoint(object):
    """Converts between real and field values using a fixed-point representation.

    Encoded values are :class:`numpy.ndarray` instances containing Python
    integers, with `precision` bits reserved for encoding fractional digits.
    Encoded values are decoded as 64-bit floating-point arrays.

    Parameters
    ----------
    precision: :class:`int`, optional
        The number of bits reserved to store fractions in encoded values.  Defaults
        to 16.
    """
    def __init__(self, precision=16):
        if not isinstance(precision, numbers.Integral):
            raise ValueError(f"Expected integer precision, got {type(precision)} instead.") # pragma: no cover
        if precision < 0:
            raise ValueError(f"Expected non-negative precision, got {precision} instead.") # pragma: no cover

        self._precision = precision
        self._scale = int(2**self._precision)


    def __eq__(self, other):
        return isinstance(other, FixedPoint) and self._precision == other._precision


    def __repr__(self):
        return f"cicada.encoding.fixedpoint.FixedPoint(precision={self._precision})" # pragma: no cover


    def _assert_unary_compatible(self, array, label):
        if not isinstance(array, numpy.ndarray) and array.dtype == numpy.dtype(object):
            raise ValueError(f"Expected {label} to be an instance of numpy.ndarray with dtype 'object', got {type(array)} instead.") # pragma: no cover


    def decode(self, array, field):
        """Convert an array of field values to an array of real values.

        Parameters
        ----------
        array: :class:`numpy.ndarray`, or :any:`None`, required
            Array of field values created with :meth:`encode`.

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

        order = field.order
        posbound = order // 2

        # Convert from the field to a plain array of integers.
        result = numpy.copy(array, subok=False)
        # Switch from twos-complement notation to negative values.
        result = numpy.where(result > posbound, -(order - result), result)
        # Shift values back to the right and convert to reals.
        return result.astype(numpy.float64) / self._scale


    def encode(self, array, field):
        """Convert array of real values to an array of field values using a fixed point integer representation.

        Parameters
        ----------
        array: :class:`numpy.ndarray` or :any:`None`, required
            The array to convert.

        field: :class:`cicada.arithmetic.Field`, required
            The returned array elements will be members of this field.

        Returns
        -------
        encoded: :class:`numpy.ndarray` or :any:`None`
            Encoded array with the same shape as the input, containing the
            fixed precision integer representation of `array`, or :any:`None`
            if the input was :any:`None`.
        """
        if array is None:
            return array

        order = field.order
        posbound = order // 2

        # Ensure we have an array, but don't copy data if it isn't necessary.
        result = numpy.array(array, dtype=numpy.float64, copy=False)
        # Shift array values left.  Don't do this inline!
        result = result * self._scale
        # Test to be sure our values are in-range for the field.
        if numpy.any(numpy.abs(result) >= posbound):
            raise ValueError("Values to be encoded are too large for representation in the field.") # pragma: no cover
        # Convert to integers, using the Python modulo operator to handle negative values.
        result = numpy.array([int(x) % order for x in numpy.nditer(result)]).reshape(result.shape)
        # Convert to a field.
        result = field(result)

        self._assert_unary_compatible(result, "result")
        return result


    @property
    def precision(self):
        return self._precision
