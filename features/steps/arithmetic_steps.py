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

import cicada.arithmetic


@given(u'a Field with default order')
def step_impl(context):
    if "fields" not in context:
        context.fields = []
    context.fields.append(cicada.arithmetic.Field())


@given(u'a Field with order {order}')
def step_impl(context, order):
    order = eval(order)
    if "fields" not in context:
        context.fields = []
    context.fields.append(cicada.arithmetic.Field(order=order))


@given(u'a field array {x}')
def step_impl(context, x):
    x = numpy.array(eval(x))
    field = context.fields[-1]
    if "fieldarrays" not in context:
        context.fieldarrays = []
    context.fieldarrays.append(field(x))


@when(u'generating a field array of zeros with shape {shape}')
def step_impl(context, shape):
    shape = eval(shape)
    field = context.fields[-1]
    if "fieldarrays" not in context:
        context.fieldarrays = []
    context.fieldarrays.append(field.zeros(shape))


@when(u'generating a field array of zeros like {other}')
def step_impl(context, other):
    other = numpy.array(eval(other))
    field = context.fields[-1]
    if "fieldarrays" not in context:
        context.fieldarrays = []
    context.fieldarrays.append(field.zeros_like(other))


@when(u'the field array is negated')
def step_impl(context):
    field = context.fields[-1]
    fieldarray = context.fieldarrays[-1]
    context.fieldarrays.append(field.negative(fieldarray))


@then(u'the field array should match {result}')
def step_impl(context, result):
    result = numpy.array(eval(result))
    fieldarray = context.fieldarrays[-1]
    numpy.testing.assert_array_equal(fieldarray, result)


@then(u'the fields should compare equal')
def step_impl(context):
    lhs, rhs = context.fields
    test.assert_true(lhs == rhs)


@then(u'the fields should compare unequal')
def step_impl(context):
    lhs, rhs = context.fields
    test.assert_true(lhs != rhs)


#@when(u'None is encoded and decoded the result should be None')
#def step_impl(context):
#    encoder = context.encoders[-1]
#    encoded = encoder.encode(None)
#    test.assert_is_none(encoded)
#    decoded = encoder.decode(encoded)
#    test.assert_is_none(decoded)
#
#
#@when(u'{x} is encoded and decoded the result should match {y}')
#def step_impl(context, x, y):
#    x = numpy.array(eval(x), dtype=numpy.float64)
#    y = numpy.array(eval(y), dtype=numpy.float64)
#
#    encoder = context.encoders[-1]
#    encoded = encoder.encode(x)
#    assert_is_fixed_field_representation(encoded)
#    decoded = encoder.decode(encoded)
#
#    numpy.testing.assert_almost_equal(decoded, y, decimal=4)
#
#
#@when(u'matrix {A} and vector {x} are encoded and multiplied without truncation, the decoded result should match {y}')
#def step_impl(context, A, x, y):
#    encoder = context.encoders[-1]
#    A = encoder.encode(numpy.array(eval(A)))
#    x = encoder.encode(numpy.array(eval(x)))
#    y = numpy.array(eval(y))
#
#    result = encoder.untruncated_matvec(A,x)
#    assert_is_fixed_field_representation(result)
#    decoded = encoder.decode(result)
#    if not numpy.allclose(decoded, y, rtol=0, atol=0.001):
#       raise ValueError("result mismatch")
#
#
#@when(u'{b} is subtracted from {a} the result should match {c}')
#def step_impl(context, a, b, c):
#    encoder = context.encoders[-1]
#    a = encoder.encode(numpy.array(eval(a)))
#    b = encoder.encode(numpy.array(eval(b)))
#    c = numpy.array(eval(c))
#
#    result = encoder.subtract(a, b)
#    assert_is_fixed_field_representation(result)
#    decoded = encoder.decode(result)
#    numpy.testing.assert_almost_equal(decoded, c, decimal=4)
#
#
#
#@when(u'{a} is negated the result should match {b}')
#def step_impl(context, a, b):
#    encoder = context.encoders[-1]
#    a = encoder.encode(numpy.array(eval(a)))
#    b = numpy.array(eval(b))
#
#    result = encoder.negative(a)
#    assert_is_fixed_field_representation(result)
#    decoded = encoder.decode(result)
#    numpy.testing.assert_almost_equal(decoded, b, decimal=4)
#
#
#@when(u'{a} is summed the result should match {b}')
#def step_impl(context, a, b):
#    encoder = context.encoders[-1]
#    a = encoder.encode(numpy.array(eval(a)))
#    b = numpy.array(eval(b))
#
#    result = encoder.sum(a)
#    assert_is_fixed_field_representation(result)
#    decoded = encoder.decode(result)
#    numpy.testing.assert_almost_equal(decoded, b, decimal=4)
#
