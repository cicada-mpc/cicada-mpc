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

import numpy

import cicada.additive
import cicada.communicator

from cicada.additive import AdditiveArrayShare

logging.basicConfig(level=logging.INFO)

@cicada.communicator.NNGCommunicator.run(world_size=3)
def main(communicator):
    log = cicada.Logger(logging.getLogger(), communicator)
    self = cicada.additive.AdditiveProtocol(communicator)

    fieldbits = self.encoder.fieldbits

    secret = numpy.array(0b10110101, numpy.object)
    log.info(f"Player {communicator.rank} secret: {secret:b}")

    share = self.share(src=0, secret=secret, shape=())

    bits = 4
    shift_left = numpy.array(2 ** bits, dtype=numpy.object)
    shift_right = numpy.array(pow(2 ** bits, self.encoder.modulus - 2, self.encoder.modulus), dtype=numpy.object)

    for element in share.storage.flat:
        element = AdditiveArrayShare(numpy.array(element, dtype=numpy.object))

        log.info(f"Player {communicator.rank} element:         {element.storage:0{fieldbits}b}")

        _, truncation_mask = self.random_bitwise_secret(bits=bits)
        log.info(f"Player {communicator.rank} truncation_mask: {self.reveal(truncation_mask):0{fieldbits}b}")

        _, remaining_mask = self.random_bitwise_secret(bits=fieldbits-bits)
        remaining_mask.storage = self.encoder.untruncated_multiply(shift_left, remaining_mask.storage)
        log.info(f"Player {communicator.rank} remaining_mask:  {self.reveal(remaining_mask):0{fieldbits}b}")

        mask = self.add(remaining_mask, truncation_mask)
        log.info(f"Player {communicator.rank} mask:            {self.reveal(mask):0{fieldbits}b}")

        masked_element = self.add(mask, element)
        masked_element = self.reveal(masked_element)
        log.info(f"Player {communicator.rank} masked_element:  {masked_element:0{fieldbits}b}")

        masked_truncation_bits = numpy.array(masked_element % 2**bits, dtype=numpy.object)
        log.info(f"Player {communicator.rank} mask_trunc_bits: {masked_truncation_bits:0{fieldbits}b}")

        truncation_bits = self.public_private_subtract(masked_truncation_bits, truncation_mask)
        log.info(f"Player {communicator.rank} truncation_bits: {self.reveal(truncation_bits):0{fieldbits}b}")

        element = self.subtract(element, truncation_bits)
        log.info(f"Player {communicator.rank} element:         {self.reveal(element):0{fieldbits}b}")

        element.storage = self.encoder.untruncated_multiply(element.storage, shift_right)
        log.info(f"Player {communicator.rank} element:         {self.reveal(element):0{fieldbits}b}")

main()

