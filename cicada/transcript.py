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


class Formatter(object):
    def __init__(self, fmt=None, msgfmt=None, callfmt=None, retfmt=None):
        if fmt is None:
            fmt = "{processName}: {msg}"
        if msgfmt is None:
            msgfmt = "{processName}: comm {message.comm.name} player {message.comm.rank}: {message.arrow} {message.other} {message.tag} {message.payload}"
        if callfmt is None:
            callfmt = "{processName}: {trace.indent}{trace.fqname}({trace.args})"
        if retfmt is None:
            retfmt = "{processName}: {trace.indent}{trace.fqname} => {trace.result}"

        self._fmt = fmt
        self._msgfmt = msgfmt
        self._callfmt = callfmt
        self._retfmt = retfmt

        self._depth = 0


    def format(self, record):
        if hasattr(record, "message"):
            msg = self._msgfmt.format_map(record.__dict__)
            return msg

        if hasattr(record, "trace"):
            trace = record.trace
            if trace.kind == "call":
                self._depth, trace.indent = self._depth + 1, "  " * self._depth
                trace.args = ", ".join([f"{key}={value!r}" for key, value in trace.locals.items()])
                msg = self._callfmt.format_map(record.__dict__)
                return msg
            if trace.kind == "return":
                self._depth, trace.indent = self._depth - 1, "  " * self._depth
                msg = self._retfmt.format_map(record.__dict__)
                return msg

        msg = self._fmt.format_map(record.__dict__)
        return msg


class FunctionTrace(object):
    pass


class HideFunctions(object):
    def __init__(self, exclude):
        self._exclude = set(exclude)

    def __call__(self, record):
        if hasattr(record, "trace") and record.trace.fqname in self._exclude:
            return False
        return True


class HideCommunicationFunctions(HideFunctions):
    def __init__(self):
        super().__init__(exclude=[
            "cicada.communicator.socket.SocketCommunicator.isend",
            "cicada.communicator.socket.SocketCommunicator.irecv",
            ])


class HideDefaultFunctions(HideFunctions):
    def __init__(self):
        super().__init__(exclude=[
            "cicada.additive.AdditiveProtocolSuite.communicator",
            "cicada.additive.AdditiveProtocolSuite.field",
            "cicada.arithmetic.Field.bytes",
            "cicada.arithmetic.Field.dtype",
            "cicada.arithmetic.Field.order",
            "cicada.communicator.interface.Communicator.ranks",
            "cicada.communicator.interface.tagname",
            "cicada.communicator.socket.SocketCommunicator.free",
            "cicada.communicator.socket.SocketCommunicator.irecv.<locals>.Result.value",
            "cicada.communicator.socket.SocketCommunicator.irecv.<locals>.Result.wait",
            "cicada.communicator.socket.SocketCommunicator.isend.<locals>.Result.wait",
            "cicada.communicator.socket.SocketCommunicator.rank",
            "cicada.communicator.socket.SocketCommunicator.run",
            "cicada.communicator.socket.SocketCommunicator.world_size",
            "cicada.communicator.socket.connect.NetstringSocket.close",
            "cicada.communicator.socket.connect.NetstringSocket.feed",
            "cicada.communicator.socket.connect.NetstringSocket.fileno",
            "cicada.communicator.socket.connect.NetstringSocket.messages",
            "cicada.communicator.socket.connect.NetstringSocket.next_message",
            "cicada.communicator.socket.connect.NetstringSocket.send",
            "cicada.communicator.socket.connect.Timer.elapsed",
            "cicada.communicator.socket.connect.Timer.expired",
            "cicada.communicator.socket.connect.connect",
            "cicada.communicator.socket.connect.direct",
            "cicada.communicator.socket.connect.getLogger",
            "cicada.communicator.socket.connect.getpeerurl",
            "cicada.communicator.socket.connect.gettls",
            "cicada.communicator.socket.connect.geturl",
            "cicada.communicator.socket.connect.listen",
            "cicada.przs.PRZSProtocol.field",
            "cicada.transcript.Formatter.format",
            "cicada.transcript.log",
            "cicada.transcript.record",
            ])


class HideInitFunctions(object):
    def __call__(self, record):
        if hasattr(record, "trace") and record.trace.name == "__init__":
            return False
        return True


class HidePrivateFunctions(object):
    def __call__(self, record):
        if hasattr(record, "trace"):
            trace = record.trace
            if trace.name.startswith("_") and not trace.name.startswith("__"):
                return False
        return True


class HideSelfArguments(object):
    def __call__(self, record):
        if hasattr(record, "trace") and record.trace.kind == "call":
            record.trace.locals = {key: value for key, value in record.trace.locals.items() if key != "self"}
        return True


class HideSpecialFunctions(object):
    def __call__(self, record):
        if hasattr(record, "trace"):
            trace = record.trace
            if trace.name.startswith("__") and trace.name.endswith("__") and trace.name != "__init__":
                return False
        return True


class LogFunctionCalls(hunter.actions.ColorStreamAction):
    def __call__(self, event):
        if not hasattr(event.function_object, "__qualname__"):
            return

        # Get the function name with varying degrees of specificity.
        fqname = event.module + "." + event.function_object.__qualname__
        qname = event.function_object.__qualname__
        name = event.function_object.__name__

        # Convert the hunter event into our own class for portability.
        trace = FunctionTrace()
        trace.fqname = fqname
        trace.qname = qname
        trace.name = name
        trace.kind = event.kind
        if event.kind == "call":
            trace.locals = event.locals
        if event.kind == "return":
            trace.locals = event.locals
            trace.result = event.arg

        log(trace=trace)


class MapInlineResults(object):
    def __init__(self, mapping):
        self._mapping = mapping

    def __call__(self, record):
        if hasattr(record, "trace") and record.trace.kind == "return" and record.trace.fqname in self._mapping:
            record.trace.result = record.trace.locals[self._mapping[record.trace.fqname]]
        return True


class Message(object):
    pass


class ShowReceivedMessages(object):
    def __call__(self, record):
        if hasattr(record, "trace") and record.trace.fqname == "cicada.communicator.socket.SocketCommunicator._queue_message":
            if record.trace.kind == "call":
                communicator = record.trace.locals["self"]
                src = record.trace.locals["src"]
                payload = record.trace.locals["payload"]
                tag = record.trace.locals["tag"]

                record.msg = "Received message"
                record.message = Message()
                record.message.arrow = "<--"
                record.message.comm = communicator
                record.message.dir = "<"
                record.message.dst = communicator.rank
                record.message.other = src
                record.message.payload = payload
                record.message.src = src
                record.message.tag = tagname(tag)
                record.message.verb = "receive"

                del record.trace

                return True

            if record.trace.kind == "return":
                return False

        return True


class ShowSentMessages(object):
    def __call__(self, record):
        if hasattr(record, "trace") and record.trace.fqname == "cicada.communicator.socket.SocketCommunicator._send":
            if record.trace.kind == "call":
                communicator = record.trace.locals["self"]
                dst = record.trace.locals["dst"]
                payload = record.trace.locals["payload"]
                tag = record.trace.locals["tag"]

                record.msg = "Sent message"
                record.message = Message()
                record.message.arrow = "-->"
                record.message.comm = communicator
                record.message.dir = ">"
                record.message.dst = dst
                record.message.other = dst
                record.message.payload = payload
                record.message.src = communicator.rank
                record.message.tag = tagname(tag)
                record.message.verb = "send"

                del record.trace

                return True

            if record.trace.kind == "return":
                return False

        return True


def log(message=None, **extra):
    logger.info(message, extra=extra)


def record():
    return hunter.trace(module_startswith="cicada", kind_in=("call", "return"), action=LogFunctionCalls())

