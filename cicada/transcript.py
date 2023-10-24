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

"""Functionality for generating transcripts of library activity.
"""

import enum
import logging

enable = False

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.propagate = False


class Category(enum.Enum):
    APP = 1
    PROTOCOL = 2
    COMMUNICATOR = 3
    ARITHMETIC = 4


class Formatter(object):
    def __init__(self, appfmt=None, protofmt=None, commfmt=None, mathfmt=None):
        if appfmt is None:
            appfmt = "{processName} {msg}"
        if protofmt is None:
            protofmt = "{processName} {protocol} {operation}"
        if commfmt is None:
            commfmt = "{processName} {arrow} {other} {tag} {payload}"
        if mathfmt is None:
            mathfmt = "{processName} {arithmetic} {operation} {operands} {result}"

        self._appfmt = appfmt
        self._protofmt = protofmt
        self._commfmt = commfmt
        self._mathfmt = mathfmt


    def format(self, record):
        if record.category == Category.APP:
            return self._appfmt.format(**record.__dict__)
        if record.category == Category.PROTOCOL:
            return self._protofmt.format(**record.__dict__)
        if record.category == Category.COMMUNICATOR:
            return self._commfmt.format(**record.__dict__)
        if record.category == Category.ARITHMETIC:
            return self._mathfmt.format(**record.__dict__)
        raise ValueError(f"Unrecognized category: {record.category}")


def log(category, message=None, **extra):
    if not isinstance(category, Category):
        raise ValueError(f"Expected an instance of cicada.transcript.Category, got {type(category)} instead.")

    if enable:
        extra["category"] = category
        logger.info(message, extra=extra)


