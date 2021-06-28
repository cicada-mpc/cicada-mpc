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

from statistics import mean, stdev
import logging
import numpy
import cicada.communicator
import cicada.encoder
import cicada.additive
from tqdm import tqdm
import sys

primeDict = {64:2**64-59, 62:2**62-57, 60:2**60-93, 58:2**58-27, 56:72057594037927931, 54:10420223883547487, 48: 149418408868787}
numPrimeBits = 64 #Pick a value from the preceding dictionary
numTruncBits =16
testVal = -2**23
expected = testVal/2**numTruncBits
fnameprefix = 'noenc1k-last'
logend = '-miltrunc.log'
plotend = '-miltrunc.png'
numRuns = int(sys.argv[1])
logging.basicConfig(level=logging.INFO)

@cicada.communicator.NNGCommunicator.run(world_size=3)
def main(communicator):
    log = cicada.Logger(logging.getLogger(), communicator)

    #Works pretty reliably with a 54 bit prime, gets unstable in a hurry with bigger than 54 bits, very reliably with 48 bits or smaller
    #Suspicions lie with things getting inappropriately cast as Numpy ints again.
    # default 64 bit prime: 18446744073709551557 = (2^64)-59 
    # 56 bit prime: 72057594037927931 = (2^56-5) or 52304857833066023 a safe prime
    # 54 bit prime: 10420223883547487
    # 48 bit prime: 149418408868787
    # 32 bit prime: 4034875883
    # small prime: 7919
    encoder = cicada.encoder.FixedFieldEncoder(primeDict[numPrimeBits], numTruncBits)     
    protocol = cicada.additive.AdditiveProtocol(communicator)
    errs = []
    errDict = {}
    maxErr = 0
    success = False
    numErrs = 0
    loopCount = 0
    try:
        for i in tqdm(range(numRuns), ascii=True):
            if i and (i % 100) == 0:
                communicator.barrier()

            loopCount = int(i)+1
            secret2trunc = protocol.secret(encoder=encoder, src=0, value=numpy.array(testVal))
            revealedsecret = protocol.reveal(secret2trunc)
#            log.info(f"Player {communicator.rank} revealed: {revealedsecret} expected: {testVal}")
#    print('top op: ', secretly32)
            secretTruncd,err = protocol.trunc_werr(operand = secret2trunc)
            revealedSecretTruncd = protocol.reveal(secretTruncd)
#            log.info(f"Player {communicator.rank} revealed: {revealedSecretTruncd} expected: {expected}")
            errs.append(err)
            if abs(err) > abs(maxErr):
                maxErr = err
            if err != 0 or revealedSecretTruncd != expected:
                numErrs += 1
            if err in errDict:
                errDict[err] += 1
            else:
                errDict[err] = 1
        with open(fnameprefix+logend, 'w') as fout:
            fout.write(f'Errors observed mean: {mean(errs)} stdev: {stdev(errs)}')
            fout.write(f'\n\nMax observed error: {maxErr}')
            fout.write(f'\n\nTotal number of error instances: {numErrs}')
            fout.write(f'\nNum Successful truncs: {loopCount}\n')
            print(f'Errors observed mean: {mean(errs)} stdev: {stdev(errs)}')
            print(f'Max observed error: {maxErr}')
            print(f'Total number of error instances: {numErrs}')
            print(f'Num Successful truncs: {loopCount}')
            print('##########')
            labels = []
            heights = []
            for k, v in errDict.items():
                fout.write(f'{k},{v}\n')
                labels.append(k)
                heights.append(v)
#            fig = plt.figure()
#            ax = fig.add_axes([0,0,1,1,])
#            ax.bar(labels, heights)
#            plt.savefig(fnameprefix+plotend)
        success = True

    finally:
        if not success:
            with open(fnameprefix+logend, 'w') as fout:
                fout.write(f'Errors observed mean: {mean(errs)} stdev: {stdev(errs)}')
                fout.write(f'\nMax observed error: {maxErr}')
                fout.write(f'\nTotal number of error instances: {numErrs}')
                fout.write(f'\nNum Successful truncs: {loopCount}\n')
                fout.write('##########\n')
                labels = []
                heights = []
                for k, v in errDict.items():
                    fout.write(f'{k},{v}\n')
                    labels.append(k)
                    heights.append(v)
#                fig = plt.figure()
#                ax = fig.add_axes([0,0,1,1,])
#                ax.bar(labels, heights)
#                plt.savefig(fnameprefix+plotend)


main()
