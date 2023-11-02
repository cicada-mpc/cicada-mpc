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
            protofmt = "{processName} {operation}"
        if commfmt is None:
            commfmt = "{processName} {arrow} {other} {tag} {payload}"
        if mathfmt is None:
            mathfmt = "{processName} {operation} {operands} {result}"

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

    extra["category"] = category
    logger.info(message, extra=extra)


#########################################################################################
# Functionality for non-intrusive transcript-logging using the Hunter library

import hunter
import numpy

from .communicator.interface import tagname


def _operands(locals, args):
    results = [locals.get(arg) for arg in args]
    for index, item in enumerate(results):
        if isinstance(item, numpy.ndarray):
            results[index] = item.tolist()
    return results


class TraceCall(object):
    def __init__(self, category, args=None):
        if args is None:
            args = []
        self._category = category
        self._args = args

    def __call__(self, event):
        if event.kind != "call":
            return
        log(
            self._category,
            "",
            operands = _operands(event.locals, self._args),
            operation = event.function_object.__qualname__,
            result = None,
            )


class TraceCallReturn(object):
    def __init__(self, category, args=None):
        if args is None:
            args = []
        self._category = category
        self._args = args
        self._stack = []

    def __call__(self, event):
        if event.kind == "call":
            self._stack.append((event.function, event.locals))
            return

        if event.kind == "return":
            log(
                self._category,
                "",
                operands = _operands(self._stack.pop()[1], self._args),
                operation = event.function_object.__qualname__,
                result = event.arg,
                )


class TraceSendMessage(object):
    def __call__(self, event):
        if event.kind != "call":
            return

        communicator = event.locals["self"]
        dst = event.locals["dst"]
        payload = event.locals["payload"]
        tag = event.locals["tag"]

        log(
            Category.COMMUNICATOR,
            "Sent message",
            arrow = "-->",
            comm = communicator.name,
            dir = ">",
            dst = dst,
            other = dst,
            payload = payload,
            rank = communicator.rank,
            src = communicator.rank,
            tag = tagname(tag),
            verb = "send",
            )


class TraceQueueMessage(object):
    def __call__(self, event):
        if event.kind != "call":
            return

        communicator = event.locals["self"]
        payload = event.locals["payload"]
        src = event.locals["src"]
        tag = event.locals["tag"]

        log(
            Category.COMMUNICATOR,
            "Received message",
            arrow = "<--",
            comm = communicator.name,
            dir = "<",
            dst = communicator.rank,
            other = src,
            payload = payload,
            rank = communicator.rank,
            src = src,
            tag = tagname(tag),
            verb = "receive",
            )


class Trace(hunter.actions.ColorStreamAction):
    def __init__(self):
        self.mappings = {
            "AdditiveProtocolSuite.reveal" : TraceCall(Category.PROTOCOL),
            "AdditiveProtocolSuite.share" : TraceCall(Category.PROTOCOL),
            "Field.add" : TraceCallReturn(Category.ARITHMETIC, args=["lhs", "rhs"]),
            "Field.inplace_add" : TraceCallReturn(Category.ARITHMETIC, args=["lhs", "rhs"]),
            "FixedPoint.encode" : TraceCallReturn(Category.ARITHMETIC),
            "PRZSProtocol.__init__" : TraceCall(Category.PROTOCOL),
            "SocketCommunicator._queue_message" : TraceQueueMessage(),
            "SocketCommunicator._send" : TraceSendMessage(),
            }

    def __call__(self, event):
        if not hasattr(event.function_object, "__qualname__"):
            return

        qualname = event.function_object.__qualname__
        if qualname not in self.mappings:
            return

        self.mappings[qualname](event)

#        if event.kind == "call":
#            self._stack.append((event.function, event.locals))
#            #print("call", event.function_object, event.locals)
#
#        if event.kind == "return":
#            # module = event.module
#            function = event.function_object.__qualname__
#            _, arguments = self._stack.pop()
#            if "self" in arguments:
#                del arguments["self"]
#            result = event.arg
#            self._log.info(f"{function}({arguments}) => {result}")


def record():
    return hunter.trace(kind_in=("call", "return"), action=Trace())
