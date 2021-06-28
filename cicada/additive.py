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

"""Functionality for creating, manipulating, and revealing additive-shared secrets."""

import logging
from math import ceil

import numpy

from cicada.communicator.interface import Communicator
import cicada.encoder

class AdditiveArrayShare(object):
    """Stores the local share of an additive-shared secret array.

    Parameters
    ----------
    storage: :class:`numpy.ndarray`, required
        Local additive share of a secret array, which *must* have been encoded
        using :class:`cicada.encoder.fixedfield.FixedFieldEncoder`.
    """
    def __init__(self, storage):
        self.storage = storage


    def __repr__(self):
        return f"cicada.additive.AdditiveArrayShare(storage={self._storage})" # pragma: no cover


    def __getitem__(self, index):
        return AdditiveArrayShare(numpy.array(self.storage[index], dtype=self.storage.dtype))


    @property
    def storage(self):
        """Local share of an additive-shared secret array.

        Returns
        -------
        storage: :class:`numpy.ndarray`
            The local additive share of the secret array.  The share is encoded
            using an instance of
            :class:`cicada.encoder.fixedfield.FixedFieldEncoder` which is owned
            by an instance of :class:`AdditiveProtocol`, and **must** be used
            for any modifications to the share value.
        """
        return self._storage


    @storage.setter
    def storage(self, storage):
        if not isinstance(storage, numpy.ndarray):
            raise ValueError(f"Expected storage to be an instance of numpy.ndarray, got {type(storage)} instead.") # pragma: no cover
        self._storage = storage


class AdditiveProtocol(object):
    """MPC protocol that uses a communicator to share and manipulate additive-shared secrets.

    Note
    ----
    Creating the protocol is a collective operation that *must*
    be called by all players that are members of `communicator`.

    Parameters
    ----------
    communicator: :class:`cicada.communicator.interface.Communicator`, required
        The communicator that this protocol will use for communication.
    seed: :class:`int`, optional
        Seed used to initialize random number generators.  For privacy, this
        value should be different for each player.  By default, the seed will
        be chosen at random, and is guaranteed to be different even on forked
        processes.  If you specify `seed` yourself, the actual seed used will
        be the sum of this value and the value of `seed_offset`.
    seed_offset: :class:`int`, optional
        Value added to the value of `seed`.  This value defaults to the player's
        rank.
    modulus: :class:`int`, optional
        Field size for storing encoded values.  Defaults to the largest prime
        less than 2^64 (2**64-59).
    precision: :class:`int`, optional
        The number of bits for storing fractions in encoded values.  Defaults
        to 16.
    """
    def __init__(self, communicator, seed=None, seed_offset=None, modulus=18446744073709551557, precision=16):
        if not isinstance(communicator, Communicator):
            raise ValueError("A Cicada communicator is required.") # pragma: no cover

        # Setup a pseudo-random sharing of zero, using code drawn from
        # https://github.com/facebookresearch/CrypTen/blob/master/crypten/__init__.py

        # Generate random seeds for Generators
        # NOTE: Chosen seed can be any number, but we choose a random 64-bit
        # integer here so other players cannot guess its value.

        # We sometimes get here from a forked process, which causes all players
        # to have the same RNG state. Reset the seed to make sure RNG streams
        # are different for all the players. We use numpy's random generator
        # here since initializing it without a seed will produce different
        # seeds even from forked processes.
        if seed is None:
            seed = numpy.random.default_rng(seed=None).integers(low=0, high=2**63-1, endpoint=True)
        else:
            if seed_offset is None:
                seed_offset = communicator.rank
            seed += seed_offset

        # Send random seed to next party, receive random seed from prev party
        if communicator.world_size >= 2:  # Otherwise sending seeds will segfault.
            next_rank = (communicator.rank + 1) % communicator.world_size
            prev_rank = (communicator.rank - 1) % communicator.world_size

            request = communicator.isend(value=seed, dst=next_rank)
            result = communicator.irecv(src=prev_rank)

            request.wait()
            result.wait()

            prev_seed = result.value
        else:
            prev_seed = seed

        # Setup random number generators
        self._g0 = numpy.random.default_rng(seed=seed)
        self._g1 = numpy.random.default_rng(seed=prev_seed)

        self._communicator = communicator
        self._encoder = cicada.encoder.FixedFieldEncoder(modulus=modulus, precision=precision)


    def _assert_binary_compatible(self, lhs, rhs, lhslabel, rhslabel):
        self._assert_unary_compatible(lhs, lhslabel)
        self._assert_unary_compatible(rhs, rhslabel)
        if lhs.storage.shape != rhs.storage.shape:
            raise ValueError(f"{lhslabel} and {rhslabel} must be the same shape, got {lhs.shape} and {rhs.shape} instead.")


    def _assert_unary_compatible(self, share, label):
        if not isinstance(share, AdditiveArrayShare):
            raise ValueError(f"{label} must be an instance of AdditiveArrayShare, got {type(share)} instead.")


    def add(self, lhs, rhs):
        """Return the elementwise sum of two secret shared arrays.

        The result is the secret shared elementwise sum of the operands.  If
        revealed, the result will need to be decoded to obtain the actual sum.

        Note
        ----
        This is a collective operation that *must* be called
        by all players that are members of :attr:`communicator`.

        Parameters
        ----------
        lhs: :class:`AdditiveArrayShare`, required
            Secret shared value to be added.
        rhs: :class:`AdditiveArrayShare`, required
            Secret shared value to be added.

        Returns
        -------
        value: :class:`AdditiveArrayShare`
            Secret-shared sum of `lhs` and `rhs`.
        """
        self._assert_binary_compatible(lhs, rhs, "lhs", "rhs")
        return AdditiveArrayShare(self.encoder.add(lhs.storage, rhs.storage))


    @property
    def communicator(self):
        """Return the :class:`cicada.communicator.interface.Communicator` used by this protocol."""
        return self._communicator


    @property
    def encoder(self):
        """Return the :class:`cicada.encoder.fixedfield.FixedFieldEncoder` used by this protocol."""
        return self._encoder


    def less_than(self, lhs, rhs):
        """Return an elementwise less-than comparison between secret shared arrays.

        The result is the secret shared elementwise comparison `lhs` < `rhs`.
        When revealed, the result will contain the values `0` or `1`, which do
        not need to be decoded.

        Note
        ----
        This is a collective operation that *must* be called
        by all players that are members of :attr:`communicator`.

        Parameters
        ----------
        lhs: :class:`AdditiveArrayShare`, required
            Secret shared value to be compared.
        rhs: :class:`AdditiveArrayShare`, required
            Secret shared value to be compared.

        Returns
        -------
        result: :class:`AdditiveArrayShare`
            Secret-shared result of computing `lhs` < `rhs` elementwise.
        """
        self._assert_binary_compatible(lhs, rhs, "lhs", "rhs")
        one = numpy.array(1, dtype=self.encoder.dtype)
        two = numpy.array(2, dtype=self.encoder.dtype)
        result = []
        for looplhs, looprhs in zip(lhs.storage.flat, rhs.storage.flat):
            looplhs = AdditiveArrayShare(numpy.array(looplhs, dtype=self.encoder.dtype))
            looprhs = AdditiveArrayShare(numpy.array(looprhs, dtype=self.encoder.dtype))
            twolooplhs = AdditiveArrayShare(self.encoder.untruncated_multiply(two, looplhs.storage))
            twolooprhs = AdditiveArrayShare(self.encoder.untruncated_multiply(two, looprhs.storage))
            diff = self.subtract(looplhs, looprhs)
            twodiff = AdditiveArrayShare(self.encoder.untruncated_multiply(two, diff.storage))
            w = self.public_private_subtract(one, self._lsb(operand=twolooplhs))
            x = self.public_private_subtract(one, self._lsb(operand=twolooprhs))
            y = self.public_private_subtract(one, self._lsb(operand=twodiff))
            wxorx = self.logical_xor(w,x)
            notwxorx = self.public_private_subtract(one, wxorx)
            xwxorx = self.untruncated_multiply(x, wxorx)
            noty = self.public_private_subtract(one, y)
            notwxorxnoty = self.untruncated_multiply(notwxorx, noty)
            result.append(self.add(xwxorx, notwxorxnoty))
        return AdditiveArrayShare(numpy.array([x.storage for x in result], dtype=self.encoder.dtype).reshape(lhs.storage.shape))#, order="C"))


    def logical_or(self, lhs, rhs):
        """Return an elementwise logical OR of two secret shared arrays.

        The operands *must* contain the *field* values `0` or `1`.  The result
        will be the secret shared elementwise logical OR of `lhs` and `rhs`.
        When revealed, the result will contain the values `0` or `1`, which do
        not need to be decoded.

        Note
        ----
        This is a collective operation that *must* be called
        by all players that are members of :attr:`communicator`.

        Parameters
        ----------
        lhs: :class:`AdditiveArrayShare`, required
            Secret shared array to be OR'd.
        rhs: :class:`AdditiveArrayShare`, required
            Secret shared array to be OR'd.

        Returns
        -------
        value: :class:`AdditiveArrayShare`
            The secret elementwise logical OR of `lhs` and `rhs`.
        """
        self._assert_binary_compatible(lhs, rhs, "lhs", "rhs")

        total = self.encoder.add(lhs.storage, rhs.storage)
        product = self.untruncated_multiply(lhs, rhs)
        return AdditiveArrayShare(self.encoder.subtract(total, product.storage))


    def logical_xor(self, lhs, rhs):
        """Return an elementwise logical exclusive OR of two secret shared arrays.

        The operands *must* contain the *field* values `0` or `1`.  The result
        will be the secret shared elementwise logical XOR of `lhs` and `rhs`.
        When revealed, the result will contain the values `0` or `1`, which do
        not need to be decoded.

        Note
        ----
        This is a collective operation that *must* be called
        by all players that are members of :attr:`communicator`.

        Parameters
        ----------
        lhs: :class:`AdditiveArrayShare`, required
            Secret shared array to be exclusive OR'd.
        rhs: :class:`AdditiveArrayShare`, required
            Secret shared array to be exclusive OR'd.

        Returns
        -------
        value: :class:`AdditiveArrayShare`
            The secret elementwise logical exclusive OR of `lhs` and `rhs`.
        """
        self._assert_binary_compatible(lhs, rhs, "lhs", "rhs")

        total = self.encoder.add(lhs.storage, rhs.storage)
        product = self.untruncated_multiply(lhs, rhs)
        twice_product = self.encoder.untruncated_multiply(numpy.array(2, dtype=self.encoder.dtype), product.storage)
        return AdditiveArrayShare(self.encoder.subtract(total, twice_product))


    def _lsb(self, operand):
        """Return the elementwise least significant bits of a secret shared array.

        When revealed, the result will contain the values `0` or `1`, which do
        not need to be decoded.

        Note
        ----
        This is a collective operation that *must* be called
        by all players that are members of :attr:`communicator`.

        Parameters
        ----------
        operand: :class:`AdditiveArrayShare`, required
            Secret shared array from which the least significant bits will be extracted

        Returns
        -------
        lsb: :class:`AdditiveArrayShare`
            Additive shared array containing the elementwise least significant
            bits of `operand`.
        """
        one = numpy.array(1, dtype=self.encoder.dtype)
        lop = operand
        tmpBW, tmp = self.random_bitwise_secret(bits=self.encoder._fieldbits)
        maskedlop = self.add(lhs=lop, rhs=tmp)
        c = int(self.reveal(maskedlop))
        comp_result = self._public_bitwise_less_than(lhspub=c, rhs=tmpBW)
        if c%2:
            c0xr0 = self.public_private_subtract(lhs=one, rhs=AdditiveArrayShare(storage=numpy.array(tmpBW.storage[-1], dtype=self.encoder.dtype)))
        else:
            c0xr0 = AdditiveArrayShare(storage=numpy.array(tmpBW.storage[-1], dtype=self.encoder.dtype))
        result = self.untruncated_multiply(lhs=comp_result, rhs=c0xr0)
        result = AdditiveArrayShare(storage=self.encoder.untruncated_multiply(lhs=numpy.array(2, dtype=object), rhs=result.storage))
        result = self.subtract(lhs=c0xr0, rhs=result)
        result = self.add(lhs=comp_result, rhs=result)
        return result


    def _public_bitwise_less_than(self,*, lhspub, rhs):
        """Comparison Operator

        Parameters
        ----------
        lhs: :class:`Int`, required 
            a publically known integer and one of the two objects to be compared 
        rhs: :class:`AdditiveArrayShare`, required 
            a bit decomposed shared secret and the other of the two objects to be compared 

        Returns
        -------
        an additive shared array containing the result of the comparison: 1 if lhspub < rhs and 0 otherwise
        """
        if rhs.storage.shape[0] != rhs.storage.size:
            raise ValueError('rhs is not of the expected shape - it should be a flat array of bits')
        bitwidth = rhs.storage.size
        lhsbits = [int(x) for x in bin(lhspub)[2:]]
        one = numpy.array(1, dtype=object)
        if len(lhsbits) < rhs.storage.size:
            lhsbits = [0 for x in range(rhs.storage.size-len(lhsbits))] + lhsbits
        xord = []
        for i, bit in enumerate(numpy.nditer(rhs.storage, ['refs_ok'])):
            rhsbit=AdditiveArrayShare(storage=numpy.array(bit, dtype=self.encoder.dtype))
            if lhsbits[i]:
                xord.append(self.public_private_subtract(lhs=one, rhs=rhsbit))
            else:
                xord.append(rhsbit)
        preord = [xord[0]] 
        for i in range(1,bitwidth):
            preord.append(self.logical_or(lhs=preord[i-1], rhs=xord[i]))
        msbdiff = [preord[0]]
        for i in range(1,bitwidth):
            msbdiff.append(self.subtract(lhs=preord[i], rhs=preord[i-1]))
        rhs_bit_at_msb_diff = []
        for i, bit in enumerate(numpy.nditer(rhs.storage, ['refs_ok'])):
            rhsbit=AdditiveArrayShare(storage=numpy.array(bit, dtype=self.encoder.dtype))
            rhs_bit_at_msb_diff.append(self.untruncated_multiply(rhsbit, msbdiff[i]))
        result = rhs_bit_at_msb_diff[0]
        for i in range(1,bitwidth):
            result = self.add(lhs=result, rhs=rhs_bit_at_msb_diff[i])
        return result

    def public_private_add(self, lhs, rhs):
        """Return the elementwise sum of public and secret shared arrays.

        All players *must* supply the same value of `lhs` when calling this
        method.  The result will be the secret shared elementwise sum of the
        public (known to all players) `lhs` array and the private (secret
        shared) `rhs` array.  If revealed, the result will need to be decoded
        to obtain the actual sum.

        Note
        ----
        This is a collective operation that *must* be called
        by all players that are members of :attr:`communicator`.

        Parameters
        ----------
        lhs: :class:`numpy.ndarray`, required
            Public value to be added, which must have been encoded
            with this protocol's :attr:`encoder`.
        rhs: :class:`AdditiveArrayShare`, required
            Secret shared value to be added.

        Returns
        -------
        value: :class:`AdditiveArrayShare`
            The secret shared sum of `lhs` and `rhs`.
        """
        self._assert_unary_compatible(rhs, "rhs")

        if self.communicator.rank == 0:
            return AdditiveArrayShare(self.encoder.add(lhs, rhs.storage))
        return rhs


    def public_private_subtract(self, lhs, rhs):
        """Return the elementwise difference between public and secret shared arrays.

        All players *must* supply the same value of `lhs` when calling this
        method.  The result will be the secret shared elementwise difference
        between the public (known to all players) `lhs` array and the private
        (secret shared) `rhs` array.  If revealed, the result will need to be
        decoded to obtain the actual difference.

        Note
        ----
        This is a collective operation that *must* be called
        by all players that are members of :attr:`communicator`.

        Parameters
        ----------
        lhs: :class:`numpy.ndarray`, required
            Public value, which must have been encoded with this protocol's
            :attr:`encoder`.
        rhs: :class:`AdditiveArrayShare`, required
            Secret shared value to be subtracted.

        Returns
        -------
        value: :class:`AdditiveArrayShare`
            The secret shared difference `lhs` - `rhs`.
        """
        self._assert_unary_compatible(rhs, "rhs")

        if self._communicator.rank == 0:
            return AdditiveArrayShare(self.encoder.subtract(lhs, rhs.storage))

        return AdditiveArrayShare(self.encoder.negative(rhs.storage))


    def random_bitwise_secret(self, *, bits, src=None, generator=None):
        """Return a vector of randomly generated bits.

        This method is secure against non-colluding semi-honest adversaries.  A
        subset of players (by default: all) generate and secret share vectors
        of pseudo-random bits which are then xored together elementwise.
        Communication and computation costs increase with the number of bits
        and the number of players, while security increases with the number of
        players.

        Parameters
        ----------
        bits: :class:`int`, required
            Number of bits to generate.
        src: sequence of :class:`int`, optional
            Players that will contribute to random bit generation.  By default,
            all players contribute.
        generator: :class:`numpy.random.Generator`, optional
            A psuedorandom number generator for sampling.  By default,
            `numpy.random.default_rng()` will be used.

        Returns
        -------
        bits: :class:`AdditiveArrayShare`
            A share of the randomly-generated bits that make-up the secret.
        secret: :class:`AdditiveArrayShare`
            A share of the value defined by `bits` (in big-endian order).
        """
        bits = int(bits)
        if bits < 1:
            raise ValueError(f"bits must be a positive integer, got {bits} instead.") # pragma: no cover

        if src is None:
            src = self.communicator.ranks
        if not src:
            raise ValueError(f"src must include at least one player, got {src} instead.") # pragma: no cover

        if generator is None:
            generator = numpy.random.default_rng()

        # Each participating player generates a vector of random bits.
        if self.communicator.rank in src:
            local_bits = generator.choice(2, size=bits).astype(self.encoder.dtype)
        else:
            local_bits = None

        # Each participating player secret shares their bit vectors.
        player_bit_shares = []
        for rank in src:
            player_bit_shares.append(self.share(src=rank, secret=local_bits, shape=(bits,)))

        # Generate the final bit vector by xor-ing everything together elementwise.
        bit_share = player_bit_shares[0]
        for player_bit_share in player_bit_shares[1:]:
            bit_share = self.logical_xor(bit_share, player_bit_share)

        # Shift and combine the resulting bits in big-endian order to produce a random value.
        shift = numpy.power(2, numpy.arange(bits, dtype=self.encoder.dtype)[::-1])
        shifted = self.encoder.untruncated_multiply(shift, bit_share.storage)
        secret_share = AdditiveArrayShare(numpy.array(numpy.sum(shifted), dtype=self.encoder.dtype))

        return bit_share, secret_share


    def reveal(self, share, dst=None):
        """Reveals a secret shared value to a subset of players.

        Note
        ----
        In most cases the revealed secret needs to be decoded with this
        protocol's :attr:`encoder` to reveal the actual value.

        This is a collective operation that *must* be called by all players
        that are members of :attr:`communicator`, whether they are receiving
        the revealed secret or not.

        Parameters
        ----------
        share: :class:`AdditiveArrayShare`, required
            The local share of the secret to be revealed.
        dst: sequence of :class:`int`, optional
            List of players who will receive the revealed secret.  If :any:`None`
            (the default), the secret will be revealed to all players.

        Returns
        -------
        value: :class:`numpy.ndarray` or :any:`None`
            Encoded representation of the revealed secret, if this player is a
            member of `dst`, or :any:`None`.
        """
        if not isinstance(share, AdditiveArrayShare):
            raise ValueError("share must be an instance of AdditiveArrayShare.") # pragma: no cover

        # Identify who will be receiving shares.
        if dst is None:
            dst = self.communicator.ranks

        # Send data to the other players.
        secret = None
        for recipient in dst:
            received_shares = self.communicator.gather(value=share.storage, dst=recipient)

            # If we're a recipient, recover the secret.
            if self.communicator.rank == recipient:
                secret = received_shares[0].copy()
                for received_share in received_shares[1:]:
                    self.encoder.inplace_add(secret, received_share)

        return secret


    def share(self, *, src, secret, shape):
        """Convert a private array to an additive secret share.

        Note
        ----
        This is a collective operation that *must* be called
        by all players that are members of :attr:`communicator`.

        Parameters
        ----------
        src: integer, required
            The player providing the private array to be secret shared.
        secret: :class:`numpy.ndarray` or :any:`None`, required
            The secret array to be shared, which must be encoded with this
            object's :attr:`encoder`.  This value is ignored for all players
            except `src`.
        shape: :class:`tuple`, required
            The shape of the secret.  Note that the shape must be consistently
            specified by all players.

        Returns
        -------
        share: :class:`AdditiveArrayShare`
            The local share of the secret shared array.
        """
        if not isinstance(shape, tuple):
            shape = (shape,)

        if self.communicator.rank == src:
            if not isinstance(secret, numpy.ndarray):
                raise ValueError("secret must be an instance of numpy.ndarray.") # pragma: no cover
            if secret.dtype != self.encoder.dtype:
                raise ValueError("secret must be encoded by this protocol's encoder.") # pragma: no cover
            if secret.shape != shape:
                raise ValueError(f"secret.shape must match shape parameter.  Expected {secret.shape}, got {shape} instead.") # pragma: no cover

        # Generate a pseudo-random zero sharing ...
        przs = self.encoder.uniform(size=shape, generator=self._g0)
        self.encoder.inplace_subtract(przs, self.encoder.uniform(size=shape, generator=self._g1))

        # Add the private secret to the PRZS
        if self.communicator.rank == src:
            self.encoder.inplace_add(przs, secret)

        # Package the result.
        return AdditiveArrayShare(przs)


    def subtract(self, lhs, rhs):
        """Subtract a secret shared value from a secret shared value.

        Note
        ----
        This is a collective operation that *must* be called
        by all players that are members of :attr:`communicator`.

        Parameters
        ----------
        lhs: :class:`AdditiveArrayShare`, required
            Shared value.
        rhs: :class:`AdditiveArrayShare`, required
            Shared value to be subtracted.

        Returns
        -------
        value: :class:`AdditiveArrayShare`
            The difference `lhs` - `rhs`.
        """
        self._assert_binary_compatible(lhs, rhs, "lhs", "rhs")
        return AdditiveArrayShare(self.encoder.subtract(lhs.storage, rhs.storage))


    def truncate(self, operand, *, bits=None, src=None, generator=None):
        """Remove the `bits` least significant bits from each element in a secret shared array.

        Note
        ----
        The operand *must* be encoded with FixedFieldEncoder

        Parameters
        ----------
        operand: :class:`AdditiveArrayShare`, required
            Shared secret to be truncated.
        bits: :class:`int`, optional
            Number of bits to truncate - defaults to the precision of the encoder.
        src: sequence of :class:`int`, optional
            Players who will participate in generating random bits as part of
            the truncation process.  More players increases security but
            decreases performance.  Defaults to all players.
        generator: :class:`numpy.random.Generator`, optional
            A psuedorandom number generator for sampling.  By default,
            `numpy.random.default_rng()` will be used.

        Returns
        -------
        array: :class:`AdditiveArrayShare`
            Share of the truncated secret.
        """
        if not isinstance(operand, AdditiveArrayShare):
            raise ValueError(f"Expected operand to be an instance of AdditiveArrayShare, got {type(operand)} instead.") # pragma: no cover

        if bits is None:
            bits = self.encoder.precision

        fieldbits = self.encoder.fieldbits

        shift_left = numpy.array(2 ** bits, dtype=self.encoder.dtype)
        # Multiplicative inverse of shift_left.
        shift_right = numpy.array(pow(2 ** bits, self.encoder.modulus-2, self.encoder.modulus), dtype=self.encoder.dtype)

        elements = []
        for element in operand.storage.flat: # Iterates in "C" order.
            element = AdditiveArrayShare(numpy.array(element, dtype=self.encoder.dtype))

            # Generate random bits that will mask the region to be truncated.
            _, truncation_mask = self.random_bitwise_secret(bits=bits, src=src, generator=generator)

            # Generate random bits that will mask everything outside the region to be truncated.
            _, remaining_mask = self.random_bitwise_secret(bits=fieldbits-bits, src=src, generator=generator)
            remaining_mask.storage = self.encoder.untruncated_multiply(remaining_mask.storage, shift_left)

            # Combine the two masks.
            mask = self.add(remaining_mask, truncation_mask)

            # Mask the array element.
            masked_element = self.add(mask, element)

            # Reveal the element to all players (because it's masked, no player learns the underlying secret).
            masked_element = int(self.reveal(masked_element))

            # Retain just the bits within the region to be truncated, which need to be removed.
            masked_truncation_bits = numpy.array(masked_element % shift_left, dtype=self.encoder.dtype)

            # Remove the mask, leaving just the bits to be removed from the
            # truncation region.  Because the result of the subtraction is
            # secret shared, the secret still isn't revealed.
            truncation_bits = self.public_private_subtract(masked_truncation_bits, truncation_mask)

            # Remove the bits in the truncation region from the element.  The result can be safely truncated.
            element = self.subtract(element, truncation_bits)

            # Truncate the element by shifting right to get rid of the (now cleared) bits in the truncation region.
            elements.append(self.encoder.untruncated_multiply(element.storage, shift_right))

        return AdditiveArrayShare(numpy.array(elements, dtype=self.encoder.dtype).reshape(operand.storage.shape, order="C"))


    def _truncate_vectorized(self, operand, *, bits=None, src=None, generator=None):
        """Remove the `bits` least significant bits from each element in a secret shared array.

        Note
        ----
        The operand *must* be encoded with FixedFieldEncoder

        Parameters
        ----------
        operand: :class:`AdditiveArrayShare`, required
            Shared secret to be truncated.
        bits: :class:`int`, optional
            Number of bits to truncate - defaults to the precision of the encoder.
        src: sequence of :class:`int`, optional
            Players who will participate in generating random bits as part of
            the truncation process.  More players increases security but
            decreases performance.  Defaults to all players.
        generator: :class:`numpy.random.Generator`, optional
            A psuedorandom number generator for sampling.  By default,
            `numpy.random.default_rng()` will be used.

        Returns
        -------
        array: :class:`AdditiveArrayShare`
            Share of the truncated secret.
        """
        if not isinstance(operand, AdditiveArrayShare):
            raise ValueError(f"Expected operand to be an instance of AdditiveArrayShare, got {type(operand)} instead.") # pragma: no cover

        if bits is None:
            bits = self.encoder.precision

        fieldbits = self.encoder.fieldbits

        shift_left = numpy.array(2 ** bits, dtype=self.encoder.dtype)
        # Multiplicative inverse of shift_left.
        shift_right = numpy.array(pow(2 ** bits, self.encoder.modulus-2, self.encoder.modulus), dtype=self.encoder.dtype)

        results = []
        # Generate random bits that will mask the region to be truncated.
        _, truncation_masks = zip(*[self.random_bitwise_secret(bits=bits, src=src, generator=generator) for x in range(operand.storage.size)])
        truncation_masks = AdditiveArrayShare(numpy.array(truncation_masks, dtype=self.encoder.dtype))
        # Generate random bits that will mask everything outside the region to be truncated.
        _, remaining_masks = zip(*[self.random_bitwise_secret(bits=bits, src=src, generator=generator) for x in range(operand.storage.size)])
        remaining_masks = AdditiveArrayShare(numpy.array(remaining_masks, dtype=self.encoder.dtype))
        remaining_masks.storage = self.encoder.untruncated_multiply(remaining_masks.storage, shift_left)
        # Combine the two masks.
        mask = self.add(remaining_mask, truncation_mask)
        # Mask the array element.
        masked_element = self.add(mask, operand)
        # Reveal the element to all players (because it's masked, no player learns the underlying secret).
        masked_element = int(self.reveal(masked_element))
        # Retain just the bits within the region to be truncated, which need to be removed.
        masked_truncation_bits = numpy.array(masked_element % shift_left, dtype=self.encoder.dtype)
        # Remove the mask, leaving just the bits to be removed from the
        # truncation region.  Because the result of the subtraction is
        # secret shared, the secret still isn't revealed.
        truncation_bits = self.public_private_subtract(masked_truncation_bits, truncation_masks)
        # Remove the bits in the truncation region from the element.  The result can be safely truncated.
        result = self.subtract(operand, truncation_bits)
        # Truncate the element by shifting right to get rid of the (now cleared) bits in the truncation region.
        result = self.encoder.untruncated_multiply(result.storage, shift_right)
        return result


    def untruncated_multiply(self, lhs, rhs):
        """Element-wise multiplication of two shared arrays.

        The operands are assumed to be vectors or matrices and their product is
        computed on an elementwise basis. Multiplication with shared secrets and
        public scalars is implemented in the encoder.

        Note
        ----
        This is a collective operation that *must* be called
        by all players that are members of :attr:`communicator`.

        This method can shared+shared values.

        Parameters
        ----------
        lhs: :class:`AdditiveArrayShare`, required
            secret value to be multiplied.
        rhs: :class:`AdditiveArrayShare`, required
            secret value to be multiplied.

        Returns
        -------
        value: :class:`AdditiveArrayShare`
            The secret elementwise product of `lhs` and `rhs`.
        """
        self._assert_binary_compatible(lhs, rhs, "lhs", "rhs")

        # To multiply using additive shares X and Y, we need to compute the
        # following polynomial:
        #
        #    (X0 + X1 + ... Xn-1)(Y0 + Y1 + ... Yn-1)
        #
        # To do so, we carefully share the terms of the polynomial with the
        # other players while ensuring that no one player receives every share
        # of either secret.  Each player multiplies and sums the terms that
        # they have on hand, producing an additive share of the result.

        rank = self.communicator.rank
        world_size = self.communicator.world_size
        count = ceil((world_size - 1) / 2)
        x = lhs.storage
        y = rhs.storage
        X = [] # Storage for shares received from other players.
        Y = [] # Storage for shares received from other players.

        # Distribute terms to the other players.
        for src in self.communicator.ranks:
            # Identify which players will receive terms.
            if world_size % 2 == 0 and src >= count:
                dst = numpy.arange(src + 1, src + 1 + count - 1) % world_size
            else:
                dst = numpy.arange(src + 1, src + 1 + count) % world_size

            # Send terms to the other players.
            values = [x] * len(dst) if src == rank else None
            share = self.communicator.scatterv(src=src, dst=dst, values=values)
            if rank in dst:
                X.append(share)
            values = [y] * len(dst) if src == rank else None
            share = self.communicator.scatterv(src=src, dst=dst, values=values)
            if rank in dst:
                Y.append(share)

        # Multiply the polynomial terms that we have on-hand.
        result = x * y
        for other_x, other_y in zip(X, Y):
            result += x * other_y + other_x * y

        return AdditiveArrayShare(numpy.array(result % self.encoder.modulus, dtype=self.encoder.dtype))
