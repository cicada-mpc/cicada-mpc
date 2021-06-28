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


import os
import pkgutil
import re
import subprocess
import sys

from behave import *

root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


@given(u'all Cicada sources.')
def step_impl(context):
    context.sources = []
    for directory, subdirectories, filenames in os.walk(root_dir):
        for filename in filenames:
            extension = os.path.splitext(filename)[1]
            if extension == ".py":
                pass
            else:
                continue
            context.sources.append(os.path.join(directory, filename))
    context.sources = sorted(context.sources)


@then(u'every Python source must contain a copyright notice.')
def step_impl(context):
    copyright_notice = """# Copyright 2021 National Technology & Engineering Solutions
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
"""
    missing = []
    for source in context.sources:
        if os.path.splitext(source)[1] not in [".py"]:
            continue
        with open(source, "r") as stream:
            if not stream.read().startswith(copyright_notice):
                missing.append(source)
    if missing:
        raise AssertionError("Missing copyright notices:\n\n%s" % "\n".join(missing))


