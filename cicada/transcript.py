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

import copy
import logging
import types

import hunter
import numpy

from .communicator.interface import tagname


class _CallLogger(hunter.actions.Action):
    def __init__(self):
        self.stack = []

    def __call__(self, event):
        if not hasattr(event.function_object, "__qualname__"):
            return

        fqname = event.module + "." + event.function_object.__qualname__
        qname = event.function_object.__qualname__
        name = event.function_object.__name__

        #####################################################################################
        # Log sent messages

        if event.kind == "call" and fqname == "cicada.communicator.socket.SocketCommunicator._send":
            communicator = event.locals["self"]
            dst = event.locals["dst"]
            payload = event.locals["payload"]
            tag = event.locals["tag"]

            net = Message()
            net.arrow = "-->"
            net.comm = communicator
            net.dir = ">"
            net.dst = dst
            net.other = dst
            net.payload = payload
            net.src = communicator.rank
            net.tag = tagname(tag)
            net.verb = "sent"

            logger.info("Sent message", extra={"net": net})

        #####################################################################################
        # Log received messages

        if event.kind == "call" and fqname == "cicada.communicator.socket.SocketCommunicator._queue_message":
            communicator = event.locals["self"]
            src = event.locals["src"]
            payload = event.locals["payload"]
            tag = event.locals["tag"]

            net = Message()
            net.arrow = "<--"
            net.comm = communicator
            net.dir = "<"
            net.dst = communicator.rank
            net.other = src
            net.payload = payload
            net.src = src
            net.tag = tagname(tag)
            net.verb = "received"

            logger.info("Received message", extra={"net": net})

        #####################################################################################
        # Log consistency verification code

        # Hide __init__ functions.
        if name in ["__init__"]:
            return

        # Hide private functions.
        if name.startswith("_") and not name.startswith("__"):
            return

        # Hide unimportant functions.
        if fqname in [
            "cicada.additive.AdditiveProtocolSuite.add",
            "cicada.additive.AdditiveProtocolSuite.communicator",
            "cicada.additive.AdditiveProtocolSuite.field",
            "cicada.additive.AdditiveProtocolSuite.field_add",
            "cicada.additive.AdditiveProtocolSuite.reveal",
            "cicada.additive.AdditiveProtocolSuite.share",
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
            "cicada.przs.PRZSProtocol.__call__",
            "cicada.przs.PRZSProtocol.field",
            "cicada.transcript.Formatter.format",
            "cicada.transcript.HideCode.filter",
            "cicada.transcript.HideContextMessages.filter",
            "cicada.transcript.HideNetworkMessages.filter",
            "cicada.transcript.HideSentMessages.filter",
            "cicada.transcript.HideReceivedMessages.filter",
            "cicada.transcript.log",
            "cicada.transcript.record",
            "cicada.transcript.code_handler",
            "cicada.transcript.net_handler",
            "cicada.transcript.set_handler",
            ]:
            return

        if event.kind == "call":
            # Make copies of the function arguments where appropriate,
            # in case they're modified in place by the function.
            args = {}
            for key, value in event.locals.items():
                if key in ["self"]:
                    args[key] = value
                else:
                    args[key] = copy.deepcopy(value)

            self.stack.append(args)
            return

        if event.kind == "return":
            args = self.stack.pop()
            locals = event.locals
            result = event.arg

            if fqname in ["cicada.arithmetic.Field.inplace_add", "cicada.arithmetic.Field.inplace_subtract"]:
                o = self.repr(args["self"])
                lhs = self.repr(args["lhs"])
                rhs = self.repr(args["rhs"])
                result = self.repr(locals["lhs"])

                _log_code(event, f"lhs = {lhs}", first=True)
                _log_code(event, f"{o}.{name}(lhs=lhs, rhs={rhs})")
                _log_code(event, f"cicada.transcript.assert_equal(lhs, {result})", last=True)

            elif fqname == "cicada.arithmetic.Field.uniform":
                o = self.repr(args["self"])
                size = self.repr(args["size"])
                bg = self.repr(args["generator"].bit_generator)
                state = self.repr(args["generator"].bit_generator.state)
                result = self.repr(result)

                _log_code(event, f"bg = {bg}", first=True)
                _log_code(event, f"bg.state = {state}")
                _log_code(event, f"cicada.transcript.assert_equal({o}.{name}(size={size}, generator=numpy.random.Generator(bg)), {result})", last=True)

            elif "self" in args:
                o = self.repr(args["self"])
                signature = ", ".join([f"{key}={self.repr(value)}" for key, value in args.items() if key != "self"])
                result = self.repr(result)

                _log_code(event, f"cicada.transcript.assert_equal({o}.{name}({signature}), {result})", first=True, last=True)

            else:
                signature = ", ".join([f"{key}={self.repr(value)}" for key, value in args.items()])
                result = self.repr(result)

                _log_code(event, f"cicada.transcript.assert_equal({name}({signature}), {result})", first=True, last=True)


    def repr(self, o):
        if isinstance(o, numpy.ndarray):
            return f"numpy.array({o.tolist()}, dtype='{o.dtype}')"
        if isinstance(o, numpy.random.Generator):
            return f"numpy.random.Generator({self.repr(o.bit_generator)})"
        if isinstance(o, numpy.random.PCG64):
            return f"numpy.random.PCG64()"
        return repr(o)


class Code(types.SimpleNamespace):
    pass


class Formatter(object):
    """Custom log formatter for transcription messages.

    Unlike the generic :class:`logging.Formatter` objects provided with Python, this
    class is configured with more than one format string, to handle each type of
    event that can be logged.  In addition to the standard format fields provided
    by :ref:`logrecord-attributes`, the format strings can use the following.

    For sent-message and received-message events:

    * net.arrow - message direction, relative to the player logging the event.
    * net.comm - communicator that sent / received the message.
    * net.comm.name - name of the communicator that sent / received the message.
    * net.comm.rank - rank of the player logging the event.
    * net.dir - message direction, relative to the player logging the event.
    * net.dst - rank of the player receiving the message.
    * net.other - rank of the player sending or receiving with the player logging the event.
    * net.payload - message payload contents.
    * net.src - rank of the player sending the message.
    * net.tag - message type.
    * net.verb - message direction, relative to the player logging the event.

    For code events:

    * code.filename - the full path to the file containing the original statement.
    * code.first - this is the first line of generated code associated with the original statement.
    * code.last - this is the last line of generated code associated with the original statement.
    * code.lineno - line number of the file containing the original statement.

    Parameters
    ----------
    fmt: :class:`str`, optional
        Format string for general purpose events.
    netfmt: :class:`str`, optional
        Format string for sent- and received-message events.
    codefmt: :class:`str`, optional
        Format string for code-generation events.
    """
    def __init__(self, fmt, netfmt, codefmt, codepre, codepost):
        self._fmt = fmt
        self._netfmt = netfmt
        self._codefmt = codefmt
        self._codepre = codepre
        self._codepost = codepost


    def format(self, record):
        """Formats a log record for display."""

        # Format network messages.
        if hasattr(record, "net"):
            msg = self._netfmt.format_map(record.__dict__)
            return msg

        # Format code.
        if hasattr(record, "code"):
            msg = self._codefmt.format_map(record.__dict__)
            if self._codepre and record.code.first:
                msg = self._codepre.format_map(record.__dict__) + msg
            if self._codepost and record.code.last:
                msg = msg + self._codepost.format_map(record.__dict__)
            return msg

        # Format generic messages.
        msg = self._fmt.format_map(record.__dict__)
        return msg


class HideCode(object):
    def filter(self, record):
        if hasattr(record, "code"):
            return False
        return True


class HideContextMessages(object):
    def filter(self, record):
        if not hasattr(record, "code") and not hasattr(record, "net"):
            return False
        return True


class HideNetworkMessages(object):
    def filter(self, record):
        if hasattr(record, "net"):
            return False
        return True


class HideReceivedMessages(object):
    def filter(self, record):
        if hasattr(record, "net") and record.net.verb == "received":
            return False
        return True


class HideSentMessages(object):
    def filter(self, record):
        if hasattr(record, "net") and record.net.verb == "sent":
            return False
        return True


class Message(types.SimpleNamespace):
    pass


def _log_code(event, message, first=False, last=False):
    code = Code()
    code.filename = event.filename
    code.lineno = event.lineno
    code.first = first
    code.last = last

    logger.info(message, extra={"code": code})


def assert_equal(lhs, rhs):
    """Test two objects for equality.

    Seamlessly handles special types such as numpy.ndarray, etc.
    """
    if isinstance(lhs, numpy.ndarray) or isinstance(rhs, numpy.ndarray):
        if not numpy.array_equal(lhs, rhs):
            raise AssertionError(f"{lhs} != {rhs}")
        return

    if not lhs == rhs:
        raise AssertionError(f"{lhs} != {rhs}")


def code_handler(handler=None, fmt=None, netfmt=None, codefmt=None, codepre=None, codepost=None, sent=False, received=False):
    if handler is None:
        handler = logging.StreamHandler()

    if fmt is None:
        fmt = "# {msg}"
    if netfmt is None:
        netfmt = "# {net.comm.rank} {net.arrow} {net.other} {net.tag} {net.payload}"
    if codefmt is None:
        codefmt = "{msg}"
    if codepost is None:
        codepost = "\n"

    if not sent:
        handler.addFilter(HideSentMessages())
    if not received:
        handler.addFilter(HideReceivedMessages())
    handler.setFormatter(Formatter(fmt=fmt, netfmt=netfmt, codefmt=codefmt, codepre=codepre, codepost=codepost))

    return handler


def net_handler(handler=None, fmt=None, netfmt=None, codefmt=None, codepre=None, codepost=None, sent=True, received=True, code=False):
    if handler is None:
        handler = logging.StreamHandler()

    if fmt is None:
        fmt = "{processName}: {msg}"
    if netfmt is None:
        netfmt = "{processName}: {net.arrow} {net.other} {net.tag} {net.payload}"
    if codefmt is None:
        codefmt = "{processName}: {msg}"

    if not code:
        handler.addFilter(HideCode())
    if not sent:
        handler.addFilter(HideSentMessages())
    if not received:
        handler.addFilter(HideReceivedMessages())
    handler.setFormatter(Formatter(fmt=fmt, netfmt=netfmt, codefmt=codefmt, codepre=codepre, codepost=codepost))

    return handler


def set_handler(logger, handler):
    logger.level = logging.INFO
    while logger.handlers:
        logger.removeHandler(logger.handlers[0])
    logger.addHandler(handler)


def log(message=None):
    """Log general-purpose events into the transcription.

    Application code should use this to provide context for the more detailed
    network and consistency verification transcript contents.
    """
    logger.info(message)


def record():
    """Enable transcription.

    All transcription functionality depends on tracing function calls, so this must
    be called to begin transcription.  The result is a context manager that can be
    used in with-statements.
    """
    return hunter.trace(module_startswith="cicada", kind_in=("call", "return"), action=_CallLogger())


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

