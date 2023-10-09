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

"""Defines abstract interfaces for network communication."""

from abc import ABCMeta, abstractmethod
import enum

class Communicator(metaclass=ABCMeta):
    """Abstract base class for objects that manage collective communications for secure multiparty computation.
    """
    def __enter__(self):
        return self


    def __exit__(self, exc_type, exc_val, exc_tb):
        self.free()
        return False


    @abstractmethod
    def allgather(self, value):
        """All-to-all communication.

        Note
        ----
        This method is a collective operation that *must* be called
        by all players that are members of the communicator.

        Parameters
        ----------
        value: Any picklable :class:`object`, required
            Local value that will be sent to all players.

        Returns
        -------
        values: sequence of :class:`object`
            Collection of objects gathered from every player, in rank order.
        """
        pass # pragma: no cover

    @abstractmethod
    def barrier(self):
        """Block the local process until all players have entered the barrier.

        Note
        ----
        This method is a collective operation that *must* be called
        by all players that are members of the communicator.
        """
        pass # pragma: no cover

    @abstractmethod
    def broadcast(self, *, src, value):
        """One-to-all communication.

        The `src` player broadcasts a single object to all players.

        Note
        ----
        This method is a collective operation that *must* be called
        by all players that are members of the communicator.

        Parameters
        ----------
        src: :class:`int`, required
            Rank of the player who is broadcasting.
        value: Any picklable :class:`object` or `None`, required
            Value to be broadcast by `src`.  Ignored for all other players.

        Returns
        -------
        value: :class:`object`
            The broadcast value.
        """
        pass # pragma: no cover

    @abstractmethod
    def free(self):
        """Free the communicator.

        This should be called if the communicator is no longer needed so that
        resources can be freed.  Note that communicators cannot be reused after
        they have been freed, a new communicator must be created instead.
        """
        pass # pragma: no cover

    @abstractmethod
    def gather(self, *, value, dst):
        """All-to-one communication.

        Every player sends a value to `dst`.

        Note
        ----
        This method is a collective operation that *must* be called
        by all players that are members of the communicator.

        Parameters
        ----------
        value: Any picklable :class:`object`, required
            Value to be sent to `dst`.
        dst: :class:`int`, required
            Rank of the player who will receive all of the values.

        Returns
        -------
        values: sequence of :class:`object` or None
            For the destination player, a sequence of `world_size` objects
            received from every player in rank order.  For all other players,
            `None`.
        """
        pass # pragma: no cover

    @abstractmethod
    def gatherv(self, *, src, value, dst):
        """Many-to-one communication.

        A subset of players each sends a value to `dst`.

        Note
        ----
        This method is a collective operation that *must* be called
        by all players that are members of the communicator.

        Parameters
        ----------
        src: sequence of :class:`int`, required
            Rank of each player sending a value.
        value: Any picklable :class:`object`, or :any:`None`, required
            Value to be sent to `dst`.
        dst: :class:`int`, required
            Rank of the player who will receive all of the values.

        Returns
        -------
        values: sequence of :class:`object` or None
            For the destination player, the sequence of values received from
            the `src` players in the same order as `src`.  For all other
            players, :any:`None`.
        """
        pass # pragma: no cover

    @abstractmethod
    def irecv(self, *, src, tag):
        """Non-blocking one-to-one communication.

        One player (the sender) sends an object to one player (the destination).

        Note
        ----
        Unlike collective operations, this method is only called by the receiver.
        It must be matched by a call to :meth:`send` by the sender.

        See Also
        --------
        recv
            Blocking one-to-one communication.

        Parameters
        ----------
        src: :class:`int`, required
            Rank of the sending player.
        tag: :class:`int` or :class:`~cicada.communicator.interface.Tag`, required
            User- or library-defined tag identifying the message type to match.

        Returns
        -------
        result: :class:`object`
            A special result object that can be used to wait for and access the
            value sent by the sender.  The result object will have a property
            `is_completed` which returns a boolean value indicating whether the
            result has been received; method `wait`, which will block
            indefinitely until the result is received; and property `value`
            which returns the received value or raises an exception if the
            value has not been received yet.
        """
        pass # pragma: no cover

    @abstractmethod
    def isend(self, *, value, dst, tag):
        """Non-blocking one-to-one communication.

        One player (the sender) sends an object to one player (the destination).

        Note
        ----
        Unlike collective operations, this method is only called by the sender.
        It must be matched by a call to :meth:`recv` by the destination.

        See Also
        --------
        send
            Blocking one-to-one communication.

        Parameters
        ----------
        value: Picklable :class:`object`, required
            Value to be sent.
        dst: :class:`int`, required
            Rank of the destination player.
        tag: :class:`int` or :class:`~cicada.communicator.interface.Tag`, required
            User- or library-defined tag identifying the message type.

        Returns
        -------
        result: :class:`object`
            A special result object that can be used to wait until the message
            has been sent.  The result object will have a property
            `is_completed` which returns a boolean value indicating whether the
            result has been sent; and a method `wait` which will block until
            the message is sent.
        """
        pass # pragma: no cover

    @property
    @abstractmethod
    def rank(self):
        """Rank of the local player.

        Returns
        -------
        rank: :class:`int`
            Player rank, in the range :math:`[0, \\text{world_size})`.
        """
        pass # pragma: no cover

    @property
    def ranks(self):
        """List of all ranks managed by this communicator.

        Returns
        -------
        ranks: sequence of :class:`int`
            The set of all ranks managed by this communicator.
        """
        return list(range(self.world_size))


    @abstractmethod
    def recv(self, *, src, tag):
        """Blocking one-to-one communication.

        One player (the sender) sends an object to one player (the destination).

        Note
        ----
        Unlike collective operations, this method is only called by the receiver.
        It must be matched by a call to :meth:`send` by the sender.

        See Also
        --------
        irecv
            Non-blocking one-to-one communication.

        Parameters
        ----------
        src: :class:`int`, required
            Rank of the sending player.
        tag: :class:`int` or :class:`~cicada.communicator.interface.Tag`, required
            User- or library-defined tag identifying the message type to match.

        Returns
        -------
        value: :class:`object`
            The value sent by the sender.
        """
        pass # pragma: no cover

    @abstractmethod
    def scatter(self, *, src, values):
        """One-to-all communication.

        One player (the sender) sends a different object to every player.

        Note
        ----
        This method is a collective operation that *must* be called
        by all players that are members of the communicator.

        Parameters
        ----------
        src: :class:`int`, required
            Rank of the sending player.
        values: sequence of picklable :class:`object`, or `None`, required
            Collection of objects to be sent, one per player, in rank order.

        Returns
        -------
        value: :class:`object`
            The object received by this player.
        """
        pass # pragma: no cover

    @abstractmethod
    def scatterv(self, *, src, values, dst):
        """One-to-many communication.

        One player (the sender) sends a different object to each in a subset of players.

        Note
        ----
        This method is a collective operation that *must* be called
        by all players that are members of the communicator.

        Parameters
        ----------
        src: :class:`int`, required
            Rank of the sending player.
        values: sequence of picklable :class:`object`, or `None`, required
            Collection of objects to be sent, one per recipient.
        dst: sequence of :class:`int`, required
            Rank of each player receiving an object, in the same order as `values`.

        Returns
        -------
        value: :class:`object` or None
            The object received by this player, or `None` if this player wasn't
            in the list of recipients.
        """
        pass # pragma: no cover

    @abstractmethod
    def send(self, value, dst, tag):
        """Blocking one-to-one communication.

        One player (the sender) sends an object to one player (the destination).

        Note
        ----
        Unlike collective operations, this method is only called by the sender.
        It must be matched by a call to :meth:`recv` by the destination.

        See Also
        --------
        isend
            Non-blocking one-to-one communication.

        Parameters
        ----------
        value: Picklable :class:`object`, required
            Value to be sent.
        dst: :class:`int`, required
            Rank of the destination player.
        tag: :class:`int` or :class:`~cicada.communicator.interface.Tag`, required
            User- or library-defined tag identifying the message type.
        """
        pass # pragma: no cover

    @property
    @abstractmethod
    def world_size(self):
        """Number of players sharing this communicator.

        Returns
        -------
        world_size: :class:`int`
            The number of players sharing this communicator.
        """
        pass # pragma: no cover


class Tag(enum.IntEnum):
    """Message tags used internally by the library.

    Callers can use these tags, or any other :class:`int`, when calling
    :meth:`Communicator.send`, :meth:`Communicator.recv`,
    :meth:`Communicator.isend`, and :meth:`Communicator.irecv`.  Note that
    negative integers are reserved for use by the library.
    """

    # Collective operations.
    ALLGATHER = -1
    BARRIER = -2
    BEACON = -3
    BROADCAST = -4
    GATHER = -5
    GATHERV = -6
    REVOKE = -7
    SCATTER = -8
    SCATTERV = -9
    SHRINK = -10

    # Logging operations.
    LOGSYNC = -20

    # Protocol-specific operations.
    PRZS = -30 # Pseudorandom Zero-Sharing.


def tagname(tag):
    """Return a human-readable name for a tag.

    Parameters
    ----------
    tag: :class:`int` or :class:`~cicada.communicator.interface.Tag`, required
    """
    try:
        tag = Tag(tag)
        return tag.name
    except:
        return str(tag)


