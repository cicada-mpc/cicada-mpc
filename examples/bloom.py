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
import pprint

import numpy

import cicada.communicator
import cicada.encoder
import cicada.additive
import hmac
import hashlib
from time import time

logging.basicConfig(level=logging.INFO)

def main(communicator):
    B = 2000 #bloom filter size
    k = 14 # number of hash functions
    n = 100 # of elements in the filter
    log = cicada.Logger(logging.getLogger(), communicator)
    protocol = cicada.additive.AdditiveProtocolSuite(communicator)

    keys = [x for x in range(k)]
    hashes = []
    bf = [0 for x in range(B)]
    items = [i for i in range(n)]

    #build bloom filter
    t0=time()
    for i in items:
        for k in keys:
            bf[hash((k,i)) %B]=1
    
    log.info(f'time to construct in the clear: {time()-t0}s', src=0)
    #log.info(bf, src=0)

    #confirm bloom filter correctness
    t0=time()
    acc_list = [0 for x in range(n)]
    for i,e in enumerate(items):
        for k in keys:
            if bf[hash((k,e))%B]==1:
                acc_list[i] += 1
    log.info(f'time to make 100 centralized/clear queries: {time()-t0}s', src=0)
    log.info(f'acc for items in bf: {acc_list}', src=0)
            
    acc = 0
    for k in keys:
        if bf[hash((k,107))%B]==1:
            acc += 1
    log.info(f'acc for item not in bf: {acc}', src=0)


    one_share = protocol.share(src=0, secret=numpy.array(1, dtype=object), shape=())
    shared_bf = [protocol.share(src=0, secret=numpy.array(0, dtype=object), shape=()) for x in range(B)]
    #creating shared bloom filter 
    t0=time()
    for i in items:
        for k in keys:
            bf_index = hash((k,i)) %B
            shared_bf[bf_index]=protocol.logical_or(one_share, shared_bf[bf_index])
    log.info(f'time to construct: {time()-t0}s', src=0)
    #querying the shared bloom filter for all the items it should contain by the leaky method
    t0=time()
    shared_acc_list = [protocol.share(src=0, secret=numpy.array(0, dtype=object), shape=()) for x in range(n)]
    for i,e in enumerate(items):
        for k in keys:
            bf_index = hash((k,e)) %B
            shared_acc_list[i] = protocol.add(shared_acc_list[i], shared_bf[bf_index])
    revealed_acc_list_sums = [int(protocol.reveal(shared_acc_list[i])) for i in range(n)]
    hundred_time = time()-t0
    log.info(f'time to make 100 leaky queries: {hundred_time}s, average time per leaky query: {hundred_time/100}s', src=0)
    log.info(f'acc for items in bf: {revealed_acc_list_sums}', src=0)

    t0=time()
    shared_acc = protocol.share(src=0, secret=numpy.array(0, dtype=object), shape=())
    for k in keys:
        bf_index = hash((k,107)) %B
        shared_acc = protocol.add(shared_acc, shared_bf[bf_index])
    revealed_acc = int(protocol.reveal(shared_acc))
    log.info(f'time to make 1 leaky query: {time()-t0}s', src=0)
    log.info(f'shared acc for item not in bf leaky query: {revealed_acc}', src=0)
    #querying the shared bloom filter for all the items it should contain by the leaky method
    t0=time()
    shared_prod_list = [protocol.share(src=0, secret=numpy.array(1, dtype=object), shape=()) for x in range(n)]
    for i,e in enumerate(items):
        for k in keys:
            bf_index = hash((k,e)) %B
            shared_prod_list[i] = protocol.untruncated_multiply(shared_prod_list[i], shared_bf[bf_index])
    revealed_prod_list = [int(protocol.reveal(shared_prod_list[i])) for i in range(n)]
    hundred_time = time()-t0
    log.info(f'time to make 100 less leaky queries: {hundred_time}s, average time per less leaky query: {hundred_time/100}s', src=0)
    log.info(f'acc for items in bf: {revealed_prod_list}', src=0)
    t0=time()
    shared_acc = protocol.share(src=0, secret=numpy.array(1, dtype=object), shape=())
    for k in keys:
        bf_index = hash((k,107)) %B
        shared_acc = protocol.untruncated_multiply(shared_acc, shared_bf[bf_index])
    revealed_acc = int(protocol.reveal(shared_acc))
    log.info(f'time to make 1 less leaky query: {time()-t0}s', src=0)
    log.info(f'shared acc for item not in bf less leaky method: {revealed_acc}', src=0)

cicada.communicator.SocketCommunicator.run(world_size=3, fn=main)

