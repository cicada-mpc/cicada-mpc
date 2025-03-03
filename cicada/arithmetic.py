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
import numbers
import types

import numpy


class Field(object):
    """Base class for fields (field array types)."""
    pass


class FieldArray(object):
    """Base class for field arrays."""
    pass


def _reconstruct(order):
    f = field(order)
    return f([])


def field(order=None):
    """Return a field (new field array type) with the given order."""
    if order is None:
        order = 18446744073709551557

    if order in field.cache:
        return field.cache[order]


    def probably_prime(n):
        """
        Miller-Rabin probabilistic primality test.

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


    if not isinstance(order, numbers.Integral):
        raise ValueError(f"Expected integer order, got {type(order)} instead.")
    if order < 0:
        raise ValueError(f"Expected non-negative order, got {order} instead.")
    if not probably_prime(order):
        raise ValueError(f"Expected order to be prime, got a composite instead.")

    def __add__(self, other):
        if not isinstance(other, type(self)):
            raise ValueError(f"Cannot add arrays from different fields {type(self)} and {type(other)}.")
        return ((numpy.asarray(self) + other) % type(self).order).view(type(self))

    def __reduce__(self):
        view = self.view(numpy.ndarray)
        state = view.__reduce__()
        return (_reconstruct, (type(self).order,), state)

    def __setstate__(self, state):
        numpy.ndarray.__setstate__(self, state[2])

    def __iadd__(self, other):
        if not isinstance(other, type(self)):
            raise ValueError(f"Cannot add arrays from different fields {type(self)} and {type(other)}.")
        array = numpy.asarray(self)
        array += other
        array %= type(self).order
        return self

    def __imul__(self, other):
        if not isinstance(other, type(self)):
            raise ValueError(f"Cannot multiply arrays from different fields {type(self)} and {type(other)}.")
        array = numpy.asarray(self)
        array *= other
        array %= type(self).order
        return self

    def __isub__(self, other):
        if not isinstance(other, type(self)):
            raise ValueError(f"Cannot subtract arrays from different fields {type(self)} and {type(other)}.")
        array = numpy.asarray(self)
        array -= other
        array %= type(self).order
        return self

    def __mul__(self, other):
        if not isinstance(other, type(self)):
            raise ValueError(f"Cannot multiply arrays from different fields {type(self)} and {type(other)}.")
        return ((numpy.asarray(self) * other) % type(self).order).view(type(self))

    def __new__(cls, array):
        array = numpy.asarray(array, dtype=cls.dtype)
        require_integers(array)
        if numpy.any(numpy.logical_or(array < 0, array >= cls.order)):
            raise ValueError(f"Field values must be in the range [0, {order}).")
        return array.view(cls)

    def __repr__(self):
        return f"FieldArray({self.tolist()!r}, order={type(self).order})"

    def __sub__(self, other):
        if not isinstance(other, type(self)):
            raise ValueError(f"Cannot subtract arrays from different fields {type(self)} and {type(other)}.")
        return ((numpy.asarray(self) - other) % type(self).order).view(type(self))

    def negative_implementation(value):
        return (0 - value) % order

    negative_implementation = numpy.frompyfunc(negative_implementation, 1, 1)

    def negative(self):
        return negative_implementation(self)

    def sum(self, axis=None, **kwargs):
        return numpy.asarray(numpy.asarray(self).sum(axis=axis) % type(self).order).view(type(self))

    def require_integers(value):
        if not isinstance(value, (int, numpy.integer)):
            raise ValueError(f"Field values must be integers, {value!r} is not allowed.")

    require_integers = numpy.frompyfunc(require_integers, 1, 0)

    class FieldMeta(type, Field):
        def __new__(cls, name, bases, namespace):
            instance = super().__new__(cls, name, bases, namespace)
            instance.__add__ = __add__
            instance.__reduce__ = __reduce__
            instance.__setstate__ = __setstate__
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

        @property
        def dtype(cls):
            return object

        def full(cls, shape, fill):
            fill = int(fill) % cls.order
            return numpy.full(shape, fill, dtype=cls.dtype).view(cls)

        def full_like(cls, other, fill):
            fill = int(fill) % cls.order
            return numpy.full_like(other, fill, dtype=cls.dtype).view(cls)

        def ones(cls, shape):
            return numpy.ones(shape, dtype=cls.dtype).view(cls)

        def ones_like(cls, other):
            return numpy.ones_like(other, dtype=cls.dtype).view(cls)

        def uniform(cls, *, size=None, generator=None):
            if size is None:
                size = ()
            if generator is None:
                generator = numpy.random.default_rng()

            count = int(numpy.prod(size))
            randombytes = generator.bytes(count * cls.bytes)
            indices = zip(numpy.arange(count) * cls.bytes, (numpy.arange(count)+1) * cls.bytes)
            values = [int.from_bytes(randombytes[start:end], "big") % cls.order for start, end in indices]
            return cls(values).reshape(size)

        def zeros(cls, shape):
            return numpy.zeros(shape, dtype=cls.dtype).view(cls)

        def zeros_like(cls, other):
            return numpy.zeros_like(other, dtype=cls.dtype).view(cls)

    FieldMeta.order = order

    new_class = types.new_class("FieldArray", (numpy.ndarray, FieldArray), dict(metaclass=FieldMeta))
    field.cache[order] = new_class
    return new_class

field.cache = {}
