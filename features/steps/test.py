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


import unittest

# Repackaging existing tests for PEP-8.

def assert_almost_equal(first, second, places=7, delta=None, msg=None):
    return unittest.TestCase().assertAlmostEqual(first, second, places=places, msg=msg, delta=delta)

def assert_dict_equal(first, second, msg=None):
    return unittest.TestCase().assertDictEqual(first, second, msg)

def assert_equal(first, second, msg=None):
    return unittest.TestCase().assertEqual(first, second, msg)

def assert_false(expr, msg=None):
    return unittest.TestCase().assertFalse(expr, msg)

def assert_is(first, second, msg=None):
    return unittest.TestCase().assertIs(first, second, msg)

def assert_is_instance(obj, cls, msg=None):
    return unittest.TestCase().assertIsInstance(obj, cls, msg)

def assert_is_none(expr, msg=None):
    return unittest.TestCase().assertIsNone(expr, msg)

def assert_logs(logger=None, level=None):
    return unittest.TestCase().assertLogs(logger, level)

def assert_no_logs(logger=None, level=None):
    return unittest.TestCase().assertNoLogs(logger, level)

def assert_sequence_equal(first, second, msg=None, seq_type=None):
    return unittest.TestCase().assertSequenceEqual(first, second, msg, seq_type)

def assert_true(expr, msg=None):
    return unittest.TestCase().assertTrue(expr, msg)
