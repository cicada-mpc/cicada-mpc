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

Use-cases include detailed debugging, logging network traffic, function
tracing, and MPC-in-the-head for zero knowledge proofs.  The latter case
is described in

    Ishai, Yuval, et al. "Zero-knowledge from secure multiparty computation." *Proceedings of the thirty-ninth annual ACM symposium on Theory of computing. 2007.*

Examples of this technique appear in
https://csrc.nist.gov/projects/pqc-dig-sig/round-1-additional-signatures as
proposals for NIST PQC standardization.
"""

import collections
import enum
import json
import logging

import hunter
import numpy

from .active import ActiveArrayShare
from .additive import AdditiveArrayShare
from .communicator.interface import tagname
from .shamir import ShamirArrayShare


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.propagate = False


class Formatter(object):
    """Custom log formatter for transcription events.

    Unlike the generic :class:`logging.Formatter` objects provided with Python, this
    class is configured with more than one format string, to handle each type of
    event that can be logged.  In addition to the standard format fields provided
    by :ref:`logrecord-attributes`, the format strings can use the following.

    For sent-message and received-message events:

    * message.arrow - message direction, relative to the player logging the event.
    * message.comm - communicator that sent / received the message.
    * message.comm.name - name of the communicator that sent / received the message.
    * message.comm.rank - rank of the player logging the event.
    * message.dir - message direction, relative to the player logging the event.
    * message.dst - rank of the player receiving the message.
    * message.other - rank of the player sending or receiving with the player logging the event.
    * message.payload - message payload contents.
    * message.src - rank of the player sending the message.
    * message.tag - message type.
    * message.verb - message direction, relative to the player logging the event.

    For function-call events:

    * trace.args - function arguments.
    * trace.depth - stack depth at the time the function is called (note: depth only reflects function calls that weren't filtered).
    * trace.fqname - fully qualified function name, including module.
    * trace.indent - stack depth formatted as a string for indented output.
    * trace.kind - "call"
    * trace.name - function name.
    * trace.qname - qualified function name.
    * trace.signature - function arguments formatted as a Python function signature.

    For function-return events:

    * trace.depth - stack depth at the time the function is called (note: depth only reflects function calls that weren't filtered).
    * trace.fqname - fully qualified function name, including module.
    * trace.indent - stack depth formatted as a string for indented output.
    * trace.kind - "call"
    * trace.locals - function locals when the function returns.
    * trace.name - function name.
    * trace.qname - qualified function name.
    * trace.result - function return value (note: some filters may provide a return value for reference even for inline functions).


    Parameters
    ----------
    fmt: :class:`str`, optional
        Format string for general purpose events.
    msgfmt: :class:`str`, optional
        Format string for sent- and received-message events.
    callfmt: :class:`str`, optional
        Format string for function-call events.
    retfmt: :class:`str`, optional
        Format string for function-return events.
    """
    def __init__(self, fmt=None, msgfmt=None, callfmt=None, retfmt=None):
        if fmt is None:
            fmt = "{processName}: {msg}"
        if msgfmt is None:
            msgfmt = "{processName}: {message.arrow} {message.other} {message.tag} {message.payload}"
        if callfmt is None:
            callfmt = "{processName}: {trace.indent}{trace.qname}({trace.signature})"
        if retfmt is None:
            retfmt = "{processName}: {trace.indent}{trace.qname} => {trace.result}"

        self._fmt = fmt
        self._msgfmt = msgfmt
        self._callfmt = callfmt
        self._retfmt = retfmt

        self._depth = 0


    def format(self, record):
        """Formats a log record for display."""
        if hasattr(record, "message"):
            msg = self._msgfmt.format_map(record.__dict__)
            return msg

        if hasattr(record, "trace"):
            trace = record.trace
            if trace.kind == "call":
                self._depth, trace.indent = self._depth + 1, "  " * self._depth
                trace.signature = ", ".join([f"{key}={value!r}" for key, value in trace.args.items()])
                msg = self._callfmt.format_map(record.__dict__)
                return msg
            if trace.kind == "return":
                self._depth, trace.indent = self._depth - 1, "  " * self._depth
                msg = self._retfmt.format_map(record.__dict__)
                return msg

        msg = self._fmt.format_map(record.__dict__)
        return msg


class _FunctionTrace(object):
    pass


class HideAllFunctions(object):
    """Removes all function call events from the transcript output."""
    def __call__(self, record):
        return not hasattr(record, "trace")


class HideFunctions(object):
    """Removes an explicit list of function call events from the transcript output.

    The list of functions to exclude can be supplied at creation, or modified afterwards
    using the `exclude` property.

    Parameters
    ----------
    exclude: sequence of :class:`str`, required
        A set of fully qualified function names (including module) to be
        excluded from the output.
    """
    def __init__(self, exclude=[]):
        self._exclude = set(exclude)

    def __call__(self, record):
        if hasattr(record, "trace") and record.trace.fqname in self._exclude:
            return False
        return True

    @property
    def exclude(self):
        """The set of functions that will be hidden from output."""
        return self._exclude

    @exclude.setter
    def exclude(self, value):
        self._exclude = set(value)


class HideCommunicationFunctions(HideFunctions):
    """Removes collective and point-to-point communication functions from the transcript output."""
    def __init__(self):
        super().__init__(exclude=[
            "cicada.communicator.socket.SocketCommunicator.allgather",
            "cicada.communicator.socket.SocketCommunicator.barrier",
            "cicada.communicator.socket.SocketCommunicator.broadcast",
            "cicada.communicator.socket.SocketCommunicator.gather",
            "cicada.communicator.socket.SocketCommunicator.gatherv",
            "cicada.communicator.socket.SocketCommunicator.irecv",
            "cicada.communicator.socket.SocketCommunicator.isend",
            "cicada.communicator.socket.SocketCommunicator.recv",
            "cicada.communicator.socket.SocketCommunicator.scatter",
            "cicada.communicator.socket.SocketCommunicator.scatterv",
            "cicada.communicator.socket.SocketCommunicator.send",
            ])


class HideDefaultFunctions(HideFunctions):
    """Removes a curated collection of low-utility function call events from the transcript output.

    Uses :class:`HideFunctions` to filter-out a set of function calls judged by
    the developers to be noisy and of little use in most scenarios.  Naturally,
    this is somewhat arbitrary, so callers are free to modify this object's
    list of exclusions using the `exclude` property after creation, or
    substitute their own filters as desired.
    """
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
    """Removes __init__ function calls from transcript output."""
    def __call__(self, record):
        if hasattr(record, "trace") and record.trace.name == "__init__":
            return False
        return True


class HidePrivateFunctions(object):
    """Removes private function calls (functions whose name begins with an underscore) from transcript output."""
    def __call__(self, record):
        if hasattr(record, "trace"):
            trace = record.trace
            if trace.name.startswith("_") and not trace.name.startswith("__"):
                return False
        return True


class HideSelfArguments(object):
    """Removes the `self` argument from transcript outputs."""
    def __call__(self, record):
        if hasattr(record, "trace") and record.trace.kind == "call":
            record.trace.args = {key: value for key, value in record.trace.args.items() if key != "self"}
        return True


class HideSpecialFunctions(object):
    """Removes special (dunder) function calls from transcript output."""
    def __call__(self, record):
        if hasattr(record, "trace"):
            trace = record.trace
            if trace.name.startswith("__") and trace.name.endswith("__") and trace.name != "__init__":
                return False
        return True


class _LogFunctionCalls(hunter.actions.ColorStreamAction):
    def __call__(self, event):
        if not hasattr(event.function_object, "__qualname__"):
            return

        # Get the function name with varying degrees of specificity.
        fqname = event.module + "." + event.function_object.__qualname__
        qname = event.function_object.__qualname__
        name = event.function_object.__name__

        # Convert the hunter event into our own class for portability.
        trace = _FunctionTrace()
        trace.fqname = fqname
        trace.qname = qname
        trace.name = name
        trace.kind = event.kind
        if event.kind == "call":
            trace.args = event.locals
        if event.kind == "return":
            trace.locals = event.locals
            trace.result = event.arg

        log(trace=trace)


class _JSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, numpy.ndarray):
            return obj.tolist()
        if isinstance(obj, ActiveArrayShare):
            return obj.storage.tolist()
        if isinstance(obj, AdditiveArrayShare):
            return obj.storage.tolist()
        if isinstance(obj, ShamirArrayShare):
            return obj.storage.tolist()
        return None


class JSONArguments(object):
    """Convert function call arguments and return values into JSON-compatible strings.

    The new, JSON-formatted values can be accessed in format strings as {jsonargs} (for
    function calls), {jsonlocals} (for function returns) and {jsonresult} (for function returns).
    """
    def __call__(self, record):
        if hasattr(record, "trace") and record.trace.kind == "call":
            record.trace.jsonargs = ",".join([f"{key},{json.dumps(value, cls=_JSONEncoder)}" for key, value in record.trace.args.items()])
        if hasattr(record, "trace") and record.trace.kind == "return":
            record.trace.jsonlocals = ",".join([f"{key},{json.dumps(value, cls=_JSONEncoder)}" for key, value in record.trace.locals.items()])
            record.trace.jsonresult = json.dumps(record.trace.result, cls=_JSONEncoder)
        return True


class MapInlineResults(object):
    """For inline functions that modify their arguments, makes the modified value visible in the transcript.

    Parameters
    ----------
    mapping: :class:`dict` of `str` keys and values, required
        The mapping keys must the fully-qualified function names, and the
        values must be the arguments that will hold the modified value after
        the function returns.
    """
    def __init__(self, mapping):
        self._mapping = mapping

    def __call__(self, record):
        if hasattr(record, "trace") and record.trace.kind == "return" and record.trace.fqname in self._mapping:
            record.trace.result = record.trace.locals[self._mapping[record.trace.fqname]]
        return True


class _Message(object):
    pass


class ShowReceivedMessages(object):
    """Converts function call events into message-received events.

    Note that this filter needs access to private communicator function calls to operate, so it
    *must* be added to a handler before adding filters like :class:`HidePrivateFunctions` that
    remove private function call events.
    """
    def __call__(self, record):
        if hasattr(record, "trace") and record.trace.fqname == "cicada.communicator.socket.SocketCommunicator._queue_message":
            if record.trace.kind == "call":
                communicator = record.trace.args["self"]
                src = record.trace.args["src"]
                payload = record.trace.args["payload"]
                tag = record.trace.args["tag"]

                record.msg = "Received message"
                record.message = _Message()
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
    """Converts function call events into message-sent events.

    Note that this filter needs access to private communicator function calls to operate, so it
    *must* be added to a handler before adding filters like :class:`HidePrivateFunctions` that
    remove private function call events.
    """
    def __call__(self, record):
        if hasattr(record, "trace") and record.trace.fqname == "cicada.communicator.socket.SocketCommunicator._send":
            if record.trace.kind == "call":
                communicator = record.trace.args["self"]
                dst = record.trace.args["dst"]
                payload = record.trace.args["payload"]
                tag = record.trace.args["tag"]

                record.msg = "Sent message"
                record.message = _Message()
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


def basic_config(handler, fmt=None, msgfmt=None, callfmt=None, retfmt=None):
    """Configures a log handler with a default set of filters and formatter, for transcript logging.

    Callers can add filters to the handler before or after calling this
    function to further customize its behavior.
    """
    handler.addFilter(HideSpecialFunctions())
    handler.addFilter(HideInitFunctions())
    handler.addFilter(HidePrivateFunctions())
    handler.addFilter(HideDefaultFunctions())
    handler.addFilter(HideCommunicationFunctions())
    handler.addFilter(HideSelfArguments())
    handler.addFilter(MapInlineResults({
        "cicada.arithmetic.Field.inplace_add": "lhs",
        "cicada.arithmetic.Field.inplace_subtract": "lhs",
    }))

    handler.setFormatter(Formatter(fmt=fmt, msgfmt=msgfmt, callfmt=callfmt, retfmt=retfmt))

    return handler


def log(message=None, **extra):
    """Log events to the transcription logger.

    Application code should use this to log general-purpose events for transcription.
    """
    logger.info(message, extra=extra)


def record():
    """Enable transcription.

    All transcription functionality depends on tracing function calls, so this must
    be called to begin transcription.  The result is a context manager that can be
    used in with-statements.
    """
    return hunter.trace(module_startswith="cicada", kind_in=("call", "return"), action=_LogFunctionCalls())

