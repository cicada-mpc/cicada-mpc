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
import unittest
import test

from behave import *
import numpy

import cicada.arithmetic


@given(u'a default Field')
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


@when(u'a field with order {order} is created, it should not raise an exception')
def step_impl(context, order):
    order = eval(order)
    field = cicada.arithmetic.Field(order=order)


@when(u'a field with order {order} is created, it should raise an exception')
def step_impl(context, order):
    order = eval(order)
    with unittest.TestCase().assertRaises(ValueError) as cm:
        field = cicada.arithmetic.Field(order=order)
    print(cm.exception)


@when(u'generating a field array of uniform random values with shape {shape}')
def step_impl(context, shape):
    shape = eval(shape)
    field = context.fields[-1]
    generator = numpy.random.default_rng()
    if "fieldarrays" not in context:
        context.fieldarrays = []
    context.fieldarrays.append(field.uniform(size=shape, generator=generator))


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
    fieldarray = context.fieldarrays.pop()
    context.fieldarrays.append(field.negative(fieldarray))


@when(u'the field array is summed')
def step_impl(context):
    field = context.fields[-1]
    fieldarray = context.fieldarrays.pop()
    context.fieldarrays.append(field.sum(fieldarray))


@when(u'the second field array is subtracted from the first')
def step_impl(context):
    field = context.fields[-1]
    b = context.fieldarrays.pop()
    a = context.fieldarrays.pop()
    context.fieldarrays.append(field.subtract(a, b))


@when(u'the second field array is added to the first')
def step_impl(context):
    field = context.fields[-1]
    b = context.fieldarrays.pop()
    a = context.fieldarrays.pop()
    context.fieldarrays.append(field.add(a, b))


@when(u'the second field array is added in-place to the first')
def step_impl(context):
    field = context.fields[-1]
    b = context.fieldarrays.pop()
    a = context.fieldarrays[-1]
    field.inplace_add(a, b)


@when(u'the second field array is subtracted in-place from the first')
def step_impl(context):
    field = context.fields[-1]
    b = context.fieldarrays.pop()
    a = context.fieldarrays[-1]
    field.inplace_subtract(a, b)


@then(u'the field array should match {result}')
def step_impl(context, result):
    field = context.fields[-1]
    result = field(eval(result))
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


@then(u'the field array shape should match {shape}')
def step_impl(context, shape):
    shape = eval(shape)
    fieldarray = context.fieldarrays[-1]
    test.assert_equal(shape, fieldarray.shape)


@then(u'the field array values should be in-range for the field')
def step_impl(context):
    field = context.fields[-1]
    fieldarray = context.fieldarrays[-1]
    test.assert_true(numpy.all(fieldarray >= 0))
    test.assert_true(numpy.all(fieldarray < field.order))



