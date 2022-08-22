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

import contextlib
import logging
import numbers

from cicada.communicator.interface import Communicator, Tag


class Logger(object):
    """Wrap a normal Python logger with a Cicada communicator to synchronize player output.

    Note
    ----
    Because :class:`Logger` communicates among players for synchronization, it
    can have a significant effect on performance, even when log messages are
    discarded by log levels or other filtering.

    Furthermore, :class:`Logger` should not be used in error recovery code, since it will
    fail attempting to communicate with players that are (presumably) dead.

    You can pass `sync=False` when creating :class:`Logger` to disable synchronization,
    e.g. if you're running your code on separate hosts or in separate terminal sessions.

    Parameters
    ----------
    logger: :class:`logging.Logger`, required.
        The Python logger to be used for output.
    communicator: :class:`cicada.communicator.interface.Communicator`, required
        The communicator that will be used to synchronize output among players.
    sync: :class:`bool`, optional
        Used to control synchronization, which is enabled by default.
    """
    def __init__(self, logger, communicator, sync=True):
        if not isinstance(communicator, Communicator):
            raise ValueError("A Cicada communicator is required.") # pragma: no cover

        self._logger = logger
        self._communicator = communicator
        self._sync = sync


    def critical(self, msg, *args, src=None, **kwargs):
        """Log a critical message, synchronized among players.

        .. note::

             This is a collective operation that *must* be called by all players that are members of the communicator.

        The arguments match those of :meth:`logging.Logger.critical`, with the addition of the following:

        Parameters
        ----------
        src: :class:`int` or sequence of :class:`int`, optional
            If specified, only the given player(s) will produce log output.
        """
        self.log(logging.CRITICAL, msg, *args, src=src, **kwargs)


    def debug(self, msg, *args, src=None, **kwargs):
        """Log a debug message, synchronized among players.

        .. note::

             This is a collective operation that *must* be called by all players that are members of the communicator.

        The arguments match those of :meth:`logging.Logger.debug`, with the addition of the following:

        Parameters
        ----------
        src: :class:`int` or sequence of :class:`int`, optional
            If specified, only the given player(s) will produce log output.
        """
        self.log(logging.DEBUG, msg, *args, src=src, **kwargs)


    def error(self, msg, *args, src=None, **kwargs):
        """Log an error message, synchronized among players.

        .. note::

             This is a collective operation that *must* be called by all players that are members of the communicator.

        The arguments match those of :meth:`logging.Logger.error`, with the addition of the following:

        Parameters
        ----------
        src: :class:`int` or sequence of :class:`int`, optional
            If specified, only the given player(s) will produce log output.
        """
        self.log(logging.ERROR, msg, *args, src=src, **kwargs)


    def info(self, msg, *args, src=None, **kwargs):
        """Log an info message, synchronized among players.

        .. note::

             This is a collective operation that *must* be called by all players that are members of the communicator.

        The arguments match those of :meth:`logging.Logger.info`, with the addition of the following:

        Parameters
        ----------
        src: :class:`int` or sequence of :class:`int`, optional
            If specified, only the given player(s) will produce log output.
        """
        self.log(logging.INFO, msg, *args, src=src, **kwargs)


    def log(self, level, msg, *args, src=None, **kwargs):
        """Log a message, synchronized among players.

        .. note::

             This is a collective operation that *must* be called by all players that are members of the communicator.

        The arguments match those of :meth:`logging.Logger.log`, with the addition of the following:

        Parameters
        ----------
        src: :class:`int` or sequence of :class:`int`, optional
            If specified, only the given player(s) will produce log output.
        """
        communicator = self._communicator

        if src is None:
            src = communicator.ranks
        elif isinstance(src, numbers.Integral):
            src = [src]

        # Wait for our turn to generate output.
        if self._sync and communicator.rank:
            communicator.recv(src=communicator.rank-1, tag=Tag.LOGSYNC)

        # Generate output.
        if communicator.rank in src:
            self._logger.log(level, msg, *args, **kwargs)

        # Notify the next player that it's their turn.
        if self._sync and communicator.rank < communicator.world_size-1:
            communicator.send(dst=communicator.rank+1, value=None, tag=Tag.LOGSYNC)

        # The last player notifies the group that the output is complete.
        if self._sync and communicator.rank == communicator.world_size-1:
            for rank in communicator.ranks:
                communicator.send(dst=rank, value=None, tag=Tag.LOGSYNC)

        # Wait until output is complete before we return.
        if self._sync:
            communicator.recv(src=communicator.world_size-1, tag=Tag.LOGSYNC)


    @property
    def logger(self):
        """Returns the underlying Python :class:`logging.Logger`."""
        return self._logger


    @contextlib.contextmanager
    def override(self, *, sync=None):
        """Temporarily change logging behavior.

        Use :meth:`override` to temporarily modify logger behavior in a with statement::

            with log.override(sync=False):
                # Do uncoordinated logging here.
            # Go back to coordinated logging here.

        .. note::

            Changes to logging behavior *must* be consistent for *all* players that are members of the communicator.

        Parameters
        ----------
        sync: :class:`bool`, optional
            If specified, override the logger sync property.

        Returns
        -------
        context: :class:`object`
            A context manager object that will restore the loger state when exited.
        """
        original_context = {
            "sync": self._sync,
        }

        try:
            if sync is not None:
                self._sync = sync
            yield original_context
        finally:
            if sync is not None:
                self._sync = original_context["sync"]

    @property
    def sync(self):
        """Controls whether coordinated logging is enabled or not.

        .. note::

            Changes to `sync` *must* be consistent for *all* players that are members of the communicator.
        """
        return self._sync


    @sync.setter
    def sync(self, value):
        self._sync = bool(value)


    def warning(self, msg, *args, src=None, **kwargs):
        """Log a warning message, synchronized among players.

        .. note::

             This is a collective operation that *must* be called by all players that are members of the communicator.

        The arguments match those of :meth:`logging.Logger.warning`, with the addition of the following:

        Parameters
        ----------
        src: :class:`int` or sequence of :class:`int`, optional
            If specified, only the given player(s) will produce log output.
        """
        self.log(logging.WARNING, msg, *args, src=src, **kwargs)

