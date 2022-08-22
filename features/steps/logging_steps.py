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
import numbers

from behave import *

from cicada.communicator import SocketCommunicator
import cicada.logging

import test


class LogWatcher(logging.Handler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.records = []

    def emit(self, record):
        self.records.append(record)


@when(u'the players create a Cicada logger, they can access the underlying Python logger')
def step_impl(context):
    def operation(communicator):
        log = cicada.logging.Logger(logging.getLogger(), communicator)
        test.assert_equal(log.logger, logging.getLogger())

    SocketCommunicator.run(world_size=context.players, fn=operation)


@when(u'the players create a Cicada logger, they can change the sync attribute')
def step_impl(context):
    def operation(communicator):
        log = cicada.logging.Logger(logging.getLogger(), communicator)
        test.assert_equal(log.sync, True)
        log.sync = False
        test.assert_equal(log.sync, False)

    SocketCommunicator.run(world_size=context.players, fn=operation)


@when(u'the players create a Cicada logger, they can temporarily change the sync attribute')
def step_impl(context):
    def operation(communicator):
        log = cicada.logging.Logger(logging.getLogger(), communicator)
        test.assert_equal(log.sync, True)
        with log.override(sync=False):
            test.assert_equal(log.sync, False)
        test.assert_equal(log.sync, True)

    SocketCommunicator.run(world_size=context.players, fn=operation)


@when(u'the players log {message} with level {level} and src {src}, the message is logged correctly')
def step_impl(context, src, message, level):
    src = eval(src)
    message = eval(message)
    level = eval(level)

    def operation(communicator, src, message, level):
        logwatcher = LogWatcher()

        logger = logging.getLogger()
        oldlevel = logger.level
        logger.level = level
        oldhandlers = logger.handlers[:]
        logger.handlers = [logwatcher]

        log = cicada.logging.Logger(logger, communicator)

        if level == logging.DEBUG:
            log.debug(message, src=src)
        elif level == logging.INFO:
            log.info(message, src=src)
        elif level == logging.WARNING:
            log.warning(message, src=src)
        elif level == logging.ERROR:
            log.error(message, src=src)
        elif level == logging.CRITICAL:
            log.critical(message, src=src)

        logger.handlers = oldhandlers
        logger.level = oldlevel

        return logwatcher.records


    results = cicada.communicator.SocketCommunicator.run(
        world_size=context.players,
        fn=operation,
        args=(src, message, level),
        identities=context.identities,
        trusted=context.trusted,
        )

    if src is None:
        src = list(range(context.players))
    elif isinstance(src, numbers.Integral):
        src = [src]

    for rank, records in enumerate(results):
        if rank in src:
            test.assert_equal(len(records), 1)
            test.assert_equal(records[0].getMessage(), message)
            test.assert_equal(records[0].levelno, level)
        else:
            test.assert_equal(len(records), 0)


