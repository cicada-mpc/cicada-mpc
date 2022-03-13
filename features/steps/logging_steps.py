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

from behave import *

import cicada.communicator
import cicada.logging

import test


@when(u'the players log {message} with level {level}, the message is logged at the correct level')
def step_impl(context, message, level):
    message = eval(message)
    level = eval(level)

    def operation(communicator, message, level):
        logger = logging.getLogger()
        log = cicada.logging.Logger(logger, communicator)
        with test.assert_logs(logger, level=level) as log_watcher:
            if level == logging.DEBUG:
                log.debug(message)
            elif level == logging.INFO:
                log.info(message)
            elif level == logging.WARNING:
                log.warning(message)
            elif level == logging.ERROR:
                log.error(message)
            elif level == logging.CRITICAL:
                log.critical(message)
        return log_watcher

    results = cicada.communicator.SocketCommunicator.run(
        world_size=context.players,
        fn=operation,
        args=(message, level),
        identities=context.identities,
        trusted=context.trusted,
        )

    for log_watcher in results:
        test.assert_equal(len(log_watcher.records), 1)
        test.assert_equal(log_watcher.records[0].getMessage(), message)


