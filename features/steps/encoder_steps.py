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

import logging
import test

from behave import *
import numpy

import cicada.encoder


def assert_is_fixed_field_representation(array):
    test.assert_is_instance(array, numpy.ndarray)
    test.assert_equal(array.dtype, numpy.object)
    for value in array.flat:
        test.assert_is_instance(value, int)


@given(u'a {precision} bit FixedFieldEncoder mod {modulus}')
def step_impl(context, precision, modulus):
    precision = eval(precision)
    modulus = eval(modulus)
    if "encoders" not in context:
        context.encoders = []
    context.encoders.append(cicada.encoder.FixedFieldEncoder(precision=precision, modulus=modulus))


@given(u'a {precision} bit FixedFieldEncoder')
def step_impl(context, precision):
    precision = eval(precision)
    if "encoders" not in context:
        context.encoders = []
    context.encoders.append(cicada.encoder.FixedFieldEncoder(precision=precision))


@given(u'a FixedFieldEncoder')
def step_impl(context):
    if "encoders" not in context:
        context.encoders = []
    context.encoders.append(cicada.encoder.FixedFieldEncoder())


@then(u'the encoders should compare equal')
def step_impl(context):
    lhs, rhs = context.encoders
    test.assert_true(lhs == rhs)


@then(u'the encoders should compare unequal')
def step_impl(context):
    lhs, rhs = context.encoders
    test.assert_true(lhs != rhs)


@when(u'{x} is encoded the shape of the encoded array should be {shape}')
def step_impl(context, x, shape):
    x = numpy.array(eval(x))
    shape = eval(shape)

    encoder = context.encoders[-1]
    encoded = encoder.encode(x)
    assert_is_fixed_field_representation(encoded)
    test.assert_equal(encoded.shape, shape)


@when(u'{x} is encoded the shape of the decoded array should be {shape}')
def step_impl(context, x, shape):
    x = numpy.array(eval(x))
    shape = eval(shape)

    encoder = context.encoders[-1]
    encoded = encoder.encode(x)
    assert_is_fixed_field_representation(encoded)
    decoded = encoder.decode(encoded)
    test.assert_equal(decoded.shape, shape)

@when(u'None is encoded and decoded the result should be None')
def step_impl(context):
    encoder = context.encoders[-1]
    encoded = encoder.encode(None)
    test.assert_is_none(encoded)
    decoded = encoder.decode(encoded)
    test.assert_is_none(decoded)


@when(u'generating zeros with shape {shape} the result should match {result}')
def step_impl(context, shape, result):
    shape = eval(shape)
    result = eval(result)

    encoder = context.encoders[-1]
    encoded = encoder.zeros(shape)
    numpy.testing.assert_array_equal(encoded, result)


@when(u'generating zeros like {other} the result should match {result}')
def step_impl(context, other, result):
    other = numpy.array(eval(other))
    result = numpy.array(eval(result))

    encoder = context.encoders[-1]
    encoded = encoder.zeros_like(other)
    numpy.testing.assert_array_equal(encoded, result)


@when(u'{x} is encoded and decoded the result should match {y}')
def step_impl(context, x, y):
    x = numpy.array(eval(x), dtype=numpy.float64)
    y = numpy.array(eval(y), dtype=numpy.float64)

    encoder = context.encoders[-1]
    encoded = encoder.encode(x)
    assert_is_fixed_field_representation(encoded)
    decoded = encoder.decode(encoded)

    numpy.testing.assert_almost_equal(decoded, y, decimal=4)


@when(u'matrix {A} and vector {x} are encoded and multiplied without truncation, the decoded result should match {y}')
def step_impl(context, A, x, y):
    encoder = context.encoders[-1]
    A = encoder.encode(numpy.array(eval(A)))
    x = encoder.encode(numpy.array(eval(x)))
    y = numpy.array(eval(y))

    result = encoder.untruncated_matvec(A,x)
    assert_is_fixed_field_representation(result)
    decoded = encoder.decode(result)
    if not numpy.allclose(decoded, y, rtol=0, atol=0.001):
       raise ValueError("result mismatch")


@when(u'{b} is subtracted from {a} the result should match {c}')
def step_impl(context, a, b, c):
    encoder = context.encoders[-1]
    a = encoder.encode(numpy.array(eval(a)))
    b = encoder.encode(numpy.array(eval(b)))
    c = numpy.array(eval(c))

    result = encoder.subtract(a, b)
    assert_is_fixed_field_representation(result)
    decoded = encoder.decode(result)
    numpy.testing.assert_almost_equal(decoded, c, decimal=4)



@when(u'{a} is negated the result should match {b}')
def step_impl(context, a, b):
    encoder = context.encoders[-1]
    a = encoder.encode(numpy.array(eval(a)))
    b = numpy.array(eval(b))

    result = encoder.negative(a)
    assert_is_fixed_field_representation(result)
    decoded = encoder.decode(result)
    numpy.testing.assert_almost_equal(decoded, b, decimal=4)


@when(u'{a} is summed the result should match {b}')
def step_impl(context, a, b):
    encoder = context.encoders[-1]
    a = encoder.encode(numpy.array(eval(a)))
    b = numpy.array(eval(b))

    result = encoder.sum(a)
    assert_is_fixed_field_representation(result)
    decoded = encoder.decode(result)
    numpy.testing.assert_almost_equal(decoded, b, decimal=4)

