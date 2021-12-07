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

import cicada.math


def assert_is_field_array(array):
    test.assert_is_instance(array, numpy.ndarray)
    test.assert_equal(array.dtype, numpy.object)
    for value in array.flat:
        test.assert_is_instance(value, int)


@given(u'a Field')
def step_impl(context):
    context.field = cicada.math.Field()


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


@when(u'{b} is subtracted from {a} in the field the result should match {c}')
def step_impl(context, a, b, c):
    a = cicada.math.FieldArray(eval(a), modulus=context.field.modulus)
    b = cicada.math.FieldArray(eval(b), modulus=context.field.modulus)
    c = cicada.math.FieldArray(eval(c), modulus=context.field.modulus)

    result = context.field.subtract(a, b)
    assert_is_field_array(result)
    numpy.testing.assert_array_equal(result, c)



@when(u'{a} is negated in the field the result should match {b}')
def step_impl(context, a, b):
    encoder = context.encoders[-1]
    a = encoder.encode(numpy.array(eval(a)))
    b = numpy.array(eval(b))

    result = encoder.negative(a)
    assert_is_fixed_field_representation(result)
    decoded = encoder.decode(result)
    numpy.testing.assert_almost_equal(decoded, b, decimal=4)



