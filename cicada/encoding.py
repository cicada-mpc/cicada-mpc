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

"""Functionality for encoding domain values using integer fields."""

import numbers

import numpy


class Bits(object):
    """Converts arrays of bit values to and from field values.
    """

    def __eq__(self, other):
        return isinstance(other, Bits)


    def __repr__(self):
        return f"cicada.encoding.Bits()" # pragma: no cover


    def decode(self, array, field):
        """Convert an array of field values to bit values.

        Parameters
        ----------
        array: :class:`numpy.ndarray`, or :any:`None`, required
            Array of field values containing only :math:`0` or :math:`1`.
        field: :class:`cicada.arithmetic.Field`, required
            Field over which the values in `array` are defined.

        Returns
        -------
        decoded: :class:`numpy.ndarray` or :any:`None`
            Array of integers containing the values :math:`0` and :math:`1`, or
            :any:`None` if the input was :any:`None`.

        Raises
        ------
        ValueError
            If `array` contains anything but :math:`0` or :math:`1`.
        """
        if array is None:
            return array
        if not isinstance(array, numpy.ndarray):
            raise ValueError(f"Expected array to be an instance of numpy.ndarray, got {type(array)} instead.") # pragma: no cover
        if not array.dtype == field.dtype:
            raise ValueError(f"Expected array dtype to be {field.dtype}, got {array.dtype} instead.") # pragma: no cover

        # Strict enforcement - input must only contain zeros and ones.
        result = array.astype(bool)
        if not numpy.array_equal(array, result):
            raise ValueError(f"Expected array to contain only zeros and ones, got {array} instead.") # pragma: no cover

        return array.astype(numpy.uint8)


    def encode(self, array, field):
        """Convert an array of bit values to field values.

        Parameters
        ----------
        array: :class:`numpy.ndarray` or :any:`None`, required
            Array to convert containing only :math:`0` or :math:`1`.
        field: :class:`cicada.arithmetic.Field`, required
            Field over which the returned values are defined.

        Returns
        -------
        encoded: :class:`numpy.ndarray` or :any:`None`
            Encoded array with the same shape as the input, containing the
            `field` values :math:`0` and :math:`1`, or :any:`None` if the input
            was :any:`None`.

        Raises
        ------
        ValueError
            If `array` contains anything but :math:`0` or :math:`1`.
        """
        if array is None:
            return array

        if not isinstance(array, numpy.ndarray):
            raise ValueError(f"Expected array to be an instance of numpy.ndarray, got {type(array)} instead.") # pragma: no cover

        # Strict enforcement - input must only contain zeros and ones.
        result = array.astype(bool)
        if not numpy.array_equal(array, result):
            raise ValueError(f"Expected array to contain only zeros and ones, got {array} instead.") # pragma: no cover

        # Convert to the field.
        return field(result)


class Boolean(object):
    """Converts arrays of boolean values to and from field values.
    """

    def __eq__(self, other):
        return isinstance(other, Boolean)


    def __repr__(self):
        return f"cicada.encoding.Boolean()" # pragma: no cover


    def decode(self, array, field):
        """Convert an array of field values to boolean values.

        Parameters
        ----------
        array: :class:`numpy.ndarray`, or :any:`None`, required
            Array of field values containing only :math:`0` or :math:`1`.
        field: :class:`cicada.arithmetic.Field`, required
            Field over which the values in `array` are defined.

        Returns
        -------
        decoded: :class:`numpy.ndarray` or :any:`None`
            Array of boolean values :math:`True` and :math:`False`, or
            :any:`None` if the input was :any:`None`.
        """
        if array is None:
            return array
        if not isinstance(array, numpy.ndarray):
            raise ValueError(f"Expected array to be an instance of numpy.ndarray, got {type(array)} instead.") # pragma: no cover
        if not array.dtype == field.dtype:
            raise ValueError(f"Expected array dtype to be {field.dtype}, got {array.dtype} instead.") # pragma: nocover

        return array.astype(bool)


    def encode(self, array, field):
        """Convert an array of boolean values to field values.

        Parameters
        ----------
        array: :class:`numpy.ndarray` or :any:`None`, required
            Array to convert.  Nonzero values are considered :math:`True`, zero values are considered :math:`False`.
        field: :class:`cicada.arithmetic.Field`, required
            Field over which the returned values are defined.

        Returns
        -------
        encoded: :class:`numpy.ndarray` or :any:`None`
            Encoded array with the same shape as the input, containing the
            `field` values :math:`0` and :math:`1`, or :any:`None` if the input
            was :any:`None`.
        """
        if array is None:
            return array

        if not isinstance(array, numpy.ndarray):
            raise ValueError(f"Expected array to be an instance of numpy.ndarray, got {type(array)} instead.") # pragma: nocover

        # Permissive coercion of truthy values.
        result = array.astype(bool)

        # Convert to the field.
        return field(result)


class FixedPoint(object):
    """Encodes real values in a field using a fixed-point representation.

    Encoded values are :class:`numpy.ndarray` instances containing Python
    integers, with `precision` bits reserved for encoding fractional digits.
    Decoded values will be :class:`numpy.ndarray` instances containining 64-bit
    floating point values.

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
        return f"cicada.encoding.FixedPoint(precision={self._precision})" # pragma: no cover


    def decode(self, array, field):
        """Convert an array of field values to an array of real values.

        Parameters
        ----------
        array: :class:`numpy.ndarray`, or :any:`None`, required
            Array of field values created with :meth:`encode`.
        field: :class:`cicada.arithmetic.Field`, required
            Field used to create `array`.

        Returns
        -------
        decoded: :class:`numpy.ndarray`
            A floating point array with the same shape as the input, containing
            the decoded representation of `array`, or :any:`None` if the input
            was :any:`None`.
        """
        if array is None:
            return array

        if not isinstance(array, numpy.ndarray):
            raise ValueError(f"Expected array to be an instance of numpy.ndarray, got {type(array)} instead.") # pragma: nocover
        if not array.dtype == field.dtype:
            raise ValueError(f"Expected array dtype to be {field.dtype}, got {array.dtype} instead.") # pragma: nocover

        order = field.order
        posbound = order // 2

        # Set aside storage for the result (ensures that we return an array and not a scalar).
        output = numpy.empty_like(array, dtype=numpy.float64)
        # Convert from the field to a plain array of integers.
        result = numpy.copy(array, subok=False)
        # Switch from twos-complement notation to negative values.
        result = numpy.where(result > posbound, -(order - result), result)
        # Shift values back to the right and convert to reals.
        return numpy.divide(result.astype(numpy.float64), self._scale, out=output)


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

        if not isinstance(array, numpy.ndarray):
            raise ValueError(f"Expected array to be an instance of numpy.ndarray, got {type(array)} instead.") # pragma: nocover

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
        result = numpy.array([int(x) % order for x in numpy.nditer(result)], dtype=field.dtype).reshape(result.shape)
        # Convert to a field.
        return field(result)


    @property
    def precision(self):
        return self._precision


class Identity(object):
    """Encodes and decodes field values without modification.

    Encoded values are :class:`numpy.ndarray` instances containing Python
    integers.  Decoded values will be the same.

    """

    def __eq__(self, other):
        return isinstance(other, Identity)


    def __repr__(self):
        return f"cicada.encoding.Identity()" # pragma: no cover


    def decode(self, array, field):
        """Return an array of field values without modification.

        Parameters
        ----------
        array: :class:`numpy.ndarray`, or :any:`None`, required
            Array of field values created with :meth:`encode`.

        Returns
        -------
        decoded: :class:`numpy.ndarray` or :any:`None`
            An array of Python integers, or :any:`None` if the input was
            :any:`None`.
        """
        if array is None:
            return array
        if not isinstance(array, numpy.ndarray):
            raise ValueError(f"Expected array to be an instance of numpy.ndarray, got {type(array)} instead.") # pragma: nocover
        if not array.dtype == field.dtype:
            raise ValueError(f"Expected array dtype to be {field.dtype}, got {array.dtype} instead.") # pragma: nocover
        return array


    def encode(self, array, field):
        """Convert array of integer values to an array of field values without modification.

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

        if not isinstance(array, numpy.ndarray):
            raise ValueError(f"Expected array to be an instance of numpy.ndarray, got {type(array)} instead.") # pragma: nocover

        # Convert to a field.
        return field(array)
