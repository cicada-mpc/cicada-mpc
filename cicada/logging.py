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
    sync: boolean, optional
        Controls whether log output is synchronized among players.  In general,
        you should enable synchronization (the default) when multiple players
        are logging to the same console, for example during local debugging and
        regression tests.
    """
    def __init__(self, logger, communicator, sync=None):
        if not isinstance(communicator, Communicator):
            raise ValueError("A Cicada communicator is required.") # pragma: no cover

        if sync is None:
            sync = True
        sync = bool(sync)

        self._logger = logger
        self._communicator = communicator
        self._sync = sync


    def _log(self, fn, src, *args, **kwargs):
        for i in range(self.communicator.world_size):
            if self.communicator.rank == i:
                if src is None or self.communicator.rank == src:
                    fn(*args, **kwargs)
            if self._sync:
                self._communicator.barrier()


    @property
    def communicator(self):
        """Returns the :class:`cicada.communicator.interface.Communicator` used by this logger."""
        return self._communicator


    def debug(self, *args, src=None, **kwargs):
        """Log a debug message, with optionally synchronized output among players.

        Note that this is a collective operation that *must* be called
        by all players that are members of :attr:`communicator`.
        """
        self._log(self._logger.debug, src, *args, **kwargs)


    def error(self, *args, src=None, **kwargs):
        """Log an error message, with optionally synchronized output among players.

        Note that this is a collective operation that *must* be called
        by all players that are members of :attr:`communicator`.
        """
        self._log(self._logger.error, src, *args, **kwargs)


    def info(self, *args, src=None, **kwargs):
        """Log an info message, with optionally synchronized output among players.

        Note that this is a collective operation that *must* be called
        by all players that are members of :attr:`communicator`.
        """
        self._log(self._logger.info, src, *args, **kwargs)


    def warning(self, *args, src=None, **kwargs):
        """Log a warning message, with optionally synchronized output among players.

        Note that this is a collective operation that *must* be called
        by all players that are members of :attr:`communicator`.
        """
        self._log(self._logger.warning, src, *args, **kwargs)

