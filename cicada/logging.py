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

"""Functionality to make logging from multiple processes easier."""

import logging

from cicada.communicator.interface import Communicator


class Logger(object):
    """Wrap a normal Python logger with a Cicada communicator to synchronize player output.

    Note
    ----
    Because :class:`Logger` communicates among players for synchronization, it
    can have a significant effect on performance, even when log messages are
    discarded by log levels or other filtering.

    Furthermore, :class:`Logger` should not be used in error recovery code, since it will
    fail attempting to communicate with players that are (presumably) dead.

    Parameters
    ----------
    logger: :class:`logging.Logger`, required.
        The Python logger to be used for output.
    communicator: :class:`cicada.communicator.interface.Communicator`, required
        The communicator that will be used to synchronize output among players.
    """
    def __init__(self, logger, communicator):
        if not isinstance(communicator, Communicator):
            raise ValueError("A Cicada communicator is required.") # pragma: no cover

        self._logger = logger
        self._communicator = communicator


    def critical(self, msg, *args, src=None, **kwargs):
        """Log a critical message, synchronized between players.

        .. note::

             This is a collective operation that *must* be called by all players that are members of the communicator.

        The arguments match those of meth:`logging.Logger.critical`, with the addition of the following:

        Parameters
        ----------
        src: :class:`int`, optional
            If specified, only the given player will produce log output.
        """
        self.log(logging.CRITICAL, msg, *args, src=src, **kwargs)


    def debug(self, msg, *args, src=None, **kwargs):
        """Log a debug message, synchronized between players.

        .. note::

             This is a collective operation that *must* be called by all players that are members of the communicator.

        The arguments match those of :meth:`logging.Logger.debug`, with the addition of the following:

        Parameters
        ----------
        src: :class:`int`, optional
            If specified, only the given player will produce log output.
        """
        self.log(logging.DEBUG, msg, *args, src=src, **kwargs)


    def error(self, msg, *args, src=None, **kwargs):
        """Log an error message, synchronized between players.

        .. note::

             This is a collective operation that *must* be called by all players that are members of the communicator.

        The arguments match those of :meth:`logging.Logger.error`, with the addition of the following:

        Parameters
        ----------
        src: :class:`int`, optional
            If specified, only the given player will produce log output.
        """
        self.log(logging.ERROR, msg, *args, src=src, **kwargs)


    def info(self, msg, *args, src=None, **kwargs):
        """Log an info message, synchronized between players.

        .. note::

             This is a collective operation that *must* be called by all players that are members of the communicator.

        The arguments match those of :meth:`logging.Logger.info`, with the addition of the following:

        Parameters
        ----------
        src: :class:`int`, optional
            If specified, only the given player will produce log output.
        """
        self.log(logging.INFO, msg, *args, src=src, **kwargs)


    def log(self, level, msg, *args, src=None, **kwargs):
        """Log a message, synchronized between players.

        .. note::

             This is a collective operation that *must* be called by all players that are members of the communicator.

        The arguments match those of :meth:`logging.Logger.log`, with the addition of the following:

        Parameters
        ----------
        src: :class:`int`, optional
            If specified, only the given player will produce log output.
        """
        for i in range(self._communicator.world_size):
            if self._communicator.rank == i:
                if src is None or self._communicator.rank == src:
                    self._logger.log(level, msg, *args, **kwargs)
            self._communicator.barrier()


    def warning(self, msg, *args, src=None, **kwargs):
        """Log a warning message, synchronized between players.

        .. note::

             This is a collective operation that *must* be called by all players that are members of the communicator.

        The arguments match those of :meth:`logging.Logger.warning`, with the addition of the following:

        Parameters
        ----------
        src: :class:`int`, optional
            If specified, only the given player will produce log output.
        """
        self.log(logging.WARNING, msg, *args, src=src, **kwargs)

