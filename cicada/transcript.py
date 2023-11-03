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

import collections
import enum
import logging

import hunter
import numpy

from .additive import AdditiveArrayShare
from .communicator.interface import tagname


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.propagate = False


class Category(enum.Enum):
    GENERIC = 1
    OPERATION = 2
    MESSAGE = 3


class Placeholder(object):
    def __bool__(self):
        return False

    def __format__(self, format_spec):
        return ""

    def __getattr__(self, key):
        return Placeholder()

    def __getitem__(self, key):
        return Placeholder()


class Fields(object):
    def __init__(self, fields):
        self._fields = dict(fields)

    def _mapvalue(self, value):
        if isinstance(value, AdditiveArrayShare):
            return value.storage.tolist()
        if isinstance(value, numpy.ndarray):
            return value.tolist()
        return value


    def __getitem__(self, key):
        if key not in self._fields:
            return Placeholder()
        value = self._fields[key]
        if isinstance(value, list):
            value = [self._mapvalue(item) for item in value]
        else:
            value = self._mapvalue(value)
        return value


class Formatter(object):
    def __init__(self, fmt=None, opfmt=None, msgfmt=None):
        if fmt is None:
            fmt = "Comm {comm.name} player {comm.rank}: {msg}"
        if opfmt is None:
            opfmt = "Comm {comm.name} player {comm.rank}: {operation} {operands} {result}"
        if msgfmt is None:
            msgfmt = "Comm {comm.name} player {comm.rank}: {arrow} {other} {tag} {payload}"

        self._fmt = fmt
        self._opfmt = opfmt
        self._msgfmt = msgfmt


    def format(self, record):
        fields = Fields(record.__dict__)

        if record.category == Category.GENERIC:
            return self._fmt.format_map(fields)
        if record.category == Category.OPERATION:
            return self._opfmt.format_map(fields)
        if record.category == Category.MESSAGE:
            return self._msgfmt.format_map(fields)

        raise ValueError(f"Unrecognized category: {record.category}")


def log(message=None, *, category=Category.GENERIC, **extra):
    if not isinstance(category, Category):
        raise ValueError(f"Expected an instance of cicada.transcript.Category, got {type(category)} instead.")

    extra["category"] = category
    logger.info(message, extra=extra)


def _arguments(locals, kwargs):
    return [locals.get(arg) for arg in kwargs]


class LogResult(object):
    def __init__(self, kwargs=None, result=None):
        if kwargs is None:
            kwargs = []

        self._kwargs = kwargs
        self._result = result
        self._stack = []

    def __call__(self, event):
        if event.kind == "call":
            self._stack.append(_arguments(event.locals, self._kwargs))
            return

        if event.kind == "return":
            if self._result is None:
                result = event.arg
            elif isinstance(self._result, str):
                result = event.locals.get(self._result)
            else:
                result = _arguments(event.locals, self._result)

            kwargs = dict(
                category = Category.OPERATION,
                operands = self._stack.pop(),
                operation = event.function_object.__qualname__,
                result = result,
            )

            if "self" in event.locals and hasattr(event.locals["self"], "communicator"):
                kwargs["comm"] = event.locals["self"].communicator

            log("", **kwargs)


class LogSendMessage(object):
    def __call__(self, event):
        if event.kind != "call":
            return

        communicator = event.locals["self"]
        dst = event.locals["dst"]
        payload = event.locals["payload"]
        tag = event.locals["tag"]

        log(
            "Sent message",
            category = Category.MESSAGE,
            arrow = "-->",
            comm = communicator,
            dir = ">",
            dst = dst,
            other = dst,
            payload = payload,
            src = communicator.rank,
            tag = tagname(tag),
            verb = "send",
            )


class LogReceiveMessage(object):
    def __call__(self, event):
        if event.kind != "call":
            return

        communicator = event.locals["self"]
        payload = event.locals["payload"]
        src = event.locals["src"]
        tag = event.locals["tag"]

        log(
            "Received message",
            category = Category.MESSAGE,
            arrow = "<--",
            comm = communicator,
            dir = "<",
            dst = communicator.rank,
            other = src,
            payload = payload,
            src = src,
            tag = tagname(tag),
            verb = "receive",
            )


class LogEvents(hunter.actions.ColorStreamAction):
    def __init__(self):
        self.mappings = {
            "AdditiveProtocolSuite.reveal" : LogResult(kwargs=["share"]),
            "AdditiveProtocolSuite.share" : LogResult(kwargs=["secret"]),
            "Field.add" : LogResult(kwargs=["lhs", "rhs"]),
            "Field.inplace_add" : LogResult(kwargs=["lhs", "rhs"], result="lhs"),
            "FixedPoint.decode" : LogResult(kwargs=["array"]),
            "FixedPoint.encode" : LogResult(kwargs=["array"]),
            "SocketCommunicator._queue_message" : LogReceiveMessage(),
            "SocketCommunicator._send" : LogSendMessage(),
            }

    def __call__(self, event):
        if hasattr(event.function_object, "__qualname__"):
            qualname = event.function_object.__qualname__
            if qualname in self.mappings:
                self.mappings[qualname](event)


def record():
    return hunter.trace(module_startswith="cicada", kind_in=("call", "return"), action=LogEvents())
