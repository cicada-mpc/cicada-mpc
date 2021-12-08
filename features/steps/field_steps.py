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

import pickle
import test

from behave import *
import numpy

from cicada.math import Field, FieldArray


def assert_is_field_array(array):
    test.assert_is_instance(array, FieldArray)
    test.assert_equal(array.dtype, numpy.object)
    for value in array.flat:
        test.assert_is_instance(value, int)


@when(u'a field array is initialized with {value} and modulus {modulus} its contents should match {out} and modulus {outmod}')
def step_impl(context, value, modulus, out, outmod):
    value = eval(value)
    modulus = eval(modulus)
    out = eval(out)
    outmod = eval(outmod)
    array = FieldArray(value, modulus=modulus)
    numpy.testing.assert_array_equal(array, out)
    test.assert_equal(array.modulus, outmod)


@when(u'a field array is initialized with {value} and modulus {modulus} and serialized the duplicate should match')
def step_impl(context, value, modulus):
    value = eval(value)
    modulus = eval(modulus)
    original = FieldArray(value, modulus=modulus)
    duplicate = pickle.loads(pickle.dumps(original))
    numpy.testing.assert_array_equal(duplicate, original)
    test.assert_equal(duplicate.modulus, original.modulus)


@given(u'a default Field')
def step_impl(context):
    context.field = Field()


@given(u'a Field with modulus {modulus}')
def step_impl(context, modulus):
    modulus = eval(modulus)
    context.field = Field(modulus)


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
#@when(u'matrix {A} and vector {x} are encoded and multiplied, the decoded result should match {y}')
#def step_impl(context, A, x, y):
#    encoder = context.encoders[-1]
#    A = encoder.encode(numpy.array(eval(A)))
#    x = encoder.encode(numpy.array(eval(x)))
#    y = numpy.array(eval(y))
#
#    result = encoder.matvec(A, x)
#    assert_is_fixed_field_representation(result)
#    decoded = encoder.decode(result)
#    test.assert_true(numpy.allclose(decoded, y, rtol=0, atol=0.001))


@when(u'{a} is added to {b} in the field the result should match {c}')
def step_impl(context, a, b, c):
    a = FieldArray(eval(a), modulus=context.field.modulus)
    b = FieldArray(eval(b), modulus=context.field.modulus)
    c = numpy.array(eval(c))

    result = context.field.add(a, b)
    assert_is_field_array(result)
    numpy.testing.assert_array_equal(result, c)


@when(u'{a} is multiplied with {b} in the field the result should match {c}')
def step_impl(context, a, b, c):
    a = FieldArray(eval(a), modulus=context.field.modulus)
    b = FieldArray(eval(b), modulus=context.field.modulus)
    c = numpy.array(eval(c))

    result = context.field.multiply(a, b)
    assert_is_field_array(result)
    numpy.testing.assert_array_equal(result, c)


@when(u'{a} is negated in the field the result should match {b}')
def step_impl(context, a, b):
    a = FieldArray(eval(a), modulus=context.field.modulus)
    b = numpy.array(eval(b))
    result = context.field.negative(a)
    assert_is_field_array(result)
    numpy.testing.assert_array_equal(result, b)


@when(u'{b} is subtracted from {a} in the field the result should match {c}')
def step_impl(context, a, b, c):
    a = FieldArray(eval(a), modulus=context.field.modulus)
    b = FieldArray(eval(b), modulus=context.field.modulus)
    c = numpy.array(eval(c))

    result = context.field.subtract(a, b)
    assert_is_field_array(result)
    numpy.testing.assert_array_equal(result, c)


@when(u'generating FieldArray zeros with shape {shape} the result should match {result}')
def step_impl(context, shape, result):
    shape = eval(shape)
    result = eval(result)
    array = context.field.zeros(shape)
    numpy.testing.assert_array_equal(array, result)


@when(u'generating FieldArray zeros like {other} the result should match {result}')
def step_impl(context, other, result):
    other = numpy.array(eval(other))
    result = eval(result)
    array = context.field.zeros_like(other)
    numpy.testing.assert_array_equal(array, result)


