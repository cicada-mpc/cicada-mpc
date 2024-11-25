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

from .active import ActiveProtocolSuite
from .additive import AdditiveProtocolSuite
from .communicator.interface import tagname
from .shamir import ShamirProtocolSuite, ShamirBasicProtocolSuite


class _CallLogger(hunter.actions.Action):
    def __init__(self):
        self.stack = []

        self.display_whitelist = set([
            "cicada.active.ActiveProtocolSuite.absolute",
            "cicada.active.ActiveProtocolSuite.add",
            "cicada.active.ActiveProtocolSuite.bit_compose",
            "cicada.active.ActiveProtocolSuite.bit_decompose",
            "cicada.active.ActiveProtocolSuite.divide",
            "cicada.active.ActiveProtocolSuite.dot",
            "cicada.active.ActiveProtocolSuite.equal",
            "cicada.active.ActiveProtocolSuite.field_add",
            "cicada.active.ActiveProtocolSuite.field_dot",
            "cicada.active.ActiveProtocolSuite.field_multiply",
            "cicada.active.ActiveProtocolSuite.field_power",
            "cicada.active.ActiveProtocolSuite.field_subtract",
            "cicada.active.ActiveProtocolSuite.field_uniform",
            "cicada.active.ActiveProtocolSuite.floor",
            "cicada.active.ActiveProtocolSuite.less",
            "cicada.active.ActiveProtocolSuite.less_zero",
            "cicada.active.ActiveProtocolSuite.logical_and",
            "cicada.active.ActiveProtocolSuite.logical_not",
            "cicada.active.ActiveProtocolSuite.logical_or",
            "cicada.active.ActiveProtocolSuite.logical_xor",
            "cicada.active.ActiveProtocolSuite.maximum",
            "cicada.active.ActiveProtocolSuite.minimum",
            "cicada.active.ActiveProtocolSuite.multiplicative_inverse",
            "cicada.active.ActiveProtocolSuite.multiply",
            "cicada.active.ActiveProtocolSuite.negative",
            "cicada.active.ActiveProtocolSuite.power",
            "cicada.active.ActiveProtocolSuite.random_bitwise_secret",
            "cicada.active.ActiveProtocolSuite.relu",
            "cicada.active.ActiveProtocolSuite.reshare",
            "cicada.active.ActiveProtocolSuite.reveal",
            "cicada.active.ActiveProtocolSuite.right_shift",
            "cicada.active.ActiveProtocolSuite.share",
            "cicada.active.ActiveProtocolSuite.subtract",
            "cicada.active.ActiveProtocolSuite.sum",
            "cicada.active.ActiveProtocolSuite.zigmoid",

            "cicada.additive.AdditiveProtocolSuite.absolute",
            "cicada.additive.AdditiveProtocolSuite.add",
            "cicada.additive.AdditiveProtocolSuite.bit_compose",
            "cicada.additive.AdditiveProtocolSuite.bit_decompose",
            "cicada.additive.AdditiveProtocolSuite.divide",
            "cicada.additive.AdditiveProtocolSuite.dot",
            "cicada.additive.AdditiveProtocolSuite.equal",
            "cicada.additive.AdditiveProtocolSuite.field_add",
            "cicada.additive.AdditiveProtocolSuite.field_dot",
            "cicada.additive.AdditiveProtocolSuite.field_multiply",
            "cicada.additive.AdditiveProtocolSuite.field_power",
            "cicada.additive.AdditiveProtocolSuite.field_subtract",
            "cicada.additive.AdditiveProtocolSuite.field_uniform",
            "cicada.additive.AdditiveProtocolSuite.floor",
            "cicada.additive.AdditiveProtocolSuite.less",
            "cicada.additive.AdditiveProtocolSuite.less_zero",
            "cicada.additive.AdditiveProtocolSuite.logical_and",
            "cicada.additive.AdditiveProtocolSuite.logical_not",
            "cicada.additive.AdditiveProtocolSuite.logical_or",
            "cicada.additive.AdditiveProtocolSuite.logical_xor",
            "cicada.additive.AdditiveProtocolSuite.maximum",
            "cicada.additive.AdditiveProtocolSuite.minimum",
            "cicada.additive.AdditiveProtocolSuite.multiplicative_inverse",
            "cicada.additive.AdditiveProtocolSuite.multiply",
            "cicada.additive.AdditiveProtocolSuite.negative",
            "cicada.additive.AdditiveProtocolSuite.power",
            "cicada.additive.AdditiveProtocolSuite.random_bitwise_secret",
            "cicada.additive.AdditiveProtocolSuite.relu",
            "cicada.additive.AdditiveProtocolSuite.reshare",
            "cicada.additive.AdditiveProtocolSuite.reveal",
            "cicada.additive.AdditiveProtocolSuite.right_shift",
            "cicada.additive.AdditiveProtocolSuite.share",
            "cicada.additive.AdditiveProtocolSuite.subtract",
            "cicada.additive.AdditiveProtocolSuite.sum",
            "cicada.additive.AdditiveProtocolSuite.zigmoid",

            "cicada.shamir.ShamirBasicProtocolSuite.add",
            "cicada.shamir.ShamirBasicProtocolSuite.bit_compose",
            "cicada.shamir.ShamirBasicProtocolSuite.field_add",
            "cicada.shamir.ShamirBasicProtocolSuite.field_subtract",
            "cicada.shamir.ShamirBasicProtocolSuite.field_uniform",
            "cicada.shamir.ShamirBasicProtocolSuite.negative",
            "cicada.shamir.ShamirBasicProtocolSuite.reshare",
            "cicada.shamir.ShamirBasicProtocolSuite.reveal",
            "cicada.shamir.ShamirBasicProtocolSuite.share",
            "cicada.shamir.ShamirBasicProtocolSuite.subtract",
            "cicada.shamir.ShamirBasicProtocolSuite.sum",

            "cicada.shamir.ShamirProtocolSuite.absolute",
            "cicada.shamir.ShamirProtocolSuite.add",
            "cicada.shamir.ShamirProtocolSuite.bit_compose",
            "cicada.shamir.ShamirProtocolSuite.bit_decompose",
            "cicada.shamir.ShamirProtocolSuite.divide",
            "cicada.shamir.ShamirProtocolSuite.dot",
            "cicada.shamir.ShamirProtocolSuite.equal",
            "cicada.shamir.ShamirProtocolSuite.field_add",
            "cicada.shamir.ShamirProtocolSuite.field_dot",
            "cicada.shamir.ShamirProtocolSuite.field_multiply",
            "cicada.shamir.ShamirProtocolSuite.field_power",
            "cicada.shamir.ShamirProtocolSuite.field_subtract",
            "cicada.shamir.ShamirProtocolSuite.field_uniform",
            "cicada.shamir.ShamirProtocolSuite.floor",
            "cicada.shamir.ShamirProtocolSuite.less",
            "cicada.shamir.ShamirProtocolSuite.less_zero",
            "cicada.shamir.ShamirProtocolSuite.logical_and",
            "cicada.shamir.ShamirProtocolSuite.logical_not",
            "cicada.shamir.ShamirProtocolSuite.logical_or",
            "cicada.shamir.ShamirProtocolSuite.logical_xor",
            "cicada.shamir.ShamirProtocolSuite.maximum",
            "cicada.shamir.ShamirProtocolSuite.minimum",
            "cicada.shamir.ShamirProtocolSuite.multiplicative_inverse",
            "cicada.shamir.ShamirProtocolSuite.multiply",
            "cicada.shamir.ShamirProtocolSuite.negative",
            "cicada.shamir.ShamirProtocolSuite.power",
            "cicada.shamir.ShamirProtocolSuite.random_bitwise_secret",
            "cicada.shamir.ShamirProtocolSuite.relu",
            "cicada.shamir.ShamirProtocolSuite.reshare",
            "cicada.shamir.ShamirProtocolSuite.reveal",
            "cicada.shamir.ShamirProtocolSuite.right_shift",
            "cicada.shamir.ShamirProtocolSuite.share",
            "cicada.shamir.ShamirProtocolSuite.subtract",
            "cicada.shamir.ShamirProtocolSuite.sum",
            "cicada.shamir.ShamirProtocolSuite.zigmoid",
            ])

        self.test_whitelist = set([
            "cicada.arithmetic.Field.__call__",
            "cicada.arithmetic.Field.add",
            "cicada.arithmetic.Field.full_like",
            "cicada.arithmetic.Field.inplace_add",
            "cicada.arithmetic.Field.inplace_subtract",
            "cicada.arithmetic.Field.multiply",
            "cicada.arithmetic.Field.negative",
            "cicada.arithmetic.Field.ones",
            "cicada.arithmetic.Field.ones_like",
            "cicada.arithmetic.Field.subtract",
            "cicada.arithmetic.Field.sum",
            "cicada.arithmetic.Field.uniform",
            "cicada.arithmetic.Field.zeros",
            "cicada.arithmetic.Field.zeros_like",
            "cicada.encoding.Bits.decode",
            "cicada.encoding.Bits.encode",
            "cicada.encoding.Boolean.decode",
            "cicada.encoding.Boolean.encode",
            "cicada.encoding.FixedPoint.decode",
            "cicada.encoding.FixedPoint.encode",
            "cicada.encoding.Identity.decode",
            "cicada.encoding.Identity.encode",
            ])


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

        # Identify functions that should be displayed in the transcript.
        display = True if fqname in self.display_whitelist else False

        # Identify functions that should generate consistency verification code in the transcript.
        test = True if fqname in self.test_whitelist else False

        # Convert display function calls into comments.
        if event.kind == "call" and display:
            args = event.locals
            o = self.repr(args["self"])
            signature = ", ".join([f"{key}={self.repr(value)}" for key, value in args.items() if key != "self"])
            _log_code(event, f"# {o}.{name}({signature})", first=True, last=True)
            return

        # Make copies of test function call arguments, in-case they're modified in-place.
        if event.kind == "call" and test:
            args = {}
            for key, value in event.locals.items():
                if key in ["self"]:
                    args[key] = value
                else:
                    args[key] = copy.deepcopy(value)

            self.stack.append(args)
            return

        # Convert test function calls into consistency verification statements.
        if event.kind == "return" and test:
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
        if isinstance(o, ActiveProtocolSuite):
            return f"cicada.active.ActiveProtcolSuite()"
        if isinstance(o, AdditiveProtocolSuite):
            return f"cicada.additive.AdditiveProtocolSuite()"
        if isinstance(o, ShamirBasicProtocolSuite):
            return f"cicada.additive.ShamirBasicProtocolSuite()"
        if isinstance(o, ShamirProtocolSuite):
            return f"cicada.additive.ShamirProtocolSuite()"
        if isinstance(o, numpy.ndarray):
            return f"numpy.array({o.tolist()}, dtype='{o.dtype}')"
        if isinstance(o, numpy.random.Generator):
            return f"numpy.random.Generator({self.repr(o.bit_generator)})"
        if isinstance(o, numpy.random.PCG64):
            return f"numpy.random.PCG64()"
        return repr(o)


class Code(types.SimpleNamespace):
    """Stores code-related metadata for use in :class:`Formatter`."""
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
        Format string for context records.
    netfmt: :class:`str`, optional
        Format string for sent- and received-message records.
    codefmt: :class:`str`, optional
        Format string for consistency verification records.
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
    """Log filter that hides code records."""
    def filter(self, record):
        if hasattr(record, "code"):
            return False
        return True


class HideContextMessages(object):
    """Log filter that hides context message records."""
    def filter(self, record):
        if not hasattr(record, "code") and not hasattr(record, "net"):
            return False
        return True


class HideReceivedMessages(object):
    """Log filter that hides network message records for received messages."""
    def filter(self, record):
        if hasattr(record, "net") and record.net.verb == "received":
            return False
        return True


class HideSentMessages(object):
    """Log filter that hides network message records for sent messages."""
    def filter(self, record):
        if hasattr(record, "net") and record.net.verb == "sent":
            return False
        return True


class Message(types.SimpleNamespace):
    """Stores message-related metadata for use in :class:`Formatter`."""
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
    """Create a :class:`logging.Handler`, configured to display consistency verification code records.

    Parameters
    ----------
    handler: :class:`logging.Handler`, optional
        The handler to be configured. Defaults to a new instance of
        :class:`logging.StreamHandler` if :any:`None`.
    fmt: :class:`str`, optional
        Format string for context records.
    netfmt: :class:`str`, optional
        Format string for sent- and received-message records.
    codefmt: :class:`str`, optional
        Format string for consistency verification records.
    codepre: :class:`str`, optional
        Format string displayed before each group of consistency verification code records.
    codpost: :class:`str`, optional
        Format string displayed after each group of consistency verification code records.
    """
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
    """Create a log handler, configured to display network message records.

    """
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
    """Set the handler for a logger, removing any other handlers.

    Parameters
    ----------
    logger: :class:`logging.Logger`, required
        The logger to be modified.
    handler: :class:`logging.Handler`, required
        The handler to be assigned to `logger`.
    """
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

