.. image:: ../artwork/cicada.png
    :width: 200px
    :align: right

.. _release-notes:

Release Notes
=============

Cicada 1.1.0 - October 9th, 2023
--------------------------------

* Moved the PRZS implementation into its own protocol object.
* Began running regression tests using Python 3.12.
* Minor documentation improvements.
* Restored missing regression tests, improved code coverage, and removed obsolete code.

Cicada 1.0.0 - September 15th, 2023
-----------------------------------

* Our first stable release!
* Split encoders into separate field arithmetic and encoding objects.
* share() and reveal() methods automatically apply a default encoding with optional caller override.
* API explicitly distinguishes between encoding-agnostic and encoding-specific operations.
* Consistent support for private/private, public/private, and private/public arithmetic, based on argument types instead of separate methods.
* Added configurable logging for message transcripts.
* Added "cicada generate-shares" command for pedagogy.

Cicada 0.8.1 - October 15th, 2022
---------------------------------

* Reorganized the documentation and added instructions for building the docs locally.

Cicada 0.8.0 - October 14th, 2022
---------------------------------

* Renamed ActiveProtocol -> ActiveProtocolSuite.
* Renamed AdditiveProtocol -> AdditiveProtocolSuite.
* Renamed ShamirProtocol -> ShamirProtocolSuite.
* Renamed ShamirBasicProtocol -> ShamirBasicProtocolSuite.
* Protocol suite encoders have been removed from the public API.
* Added multiply(), divide(), and reshare() methods to all protocol suites.
* Significantly improved FixedFieldEncoder.uniform() performance.
* Switched to a faster dot-product implementation for ShamirProtocolSuite.
* Added documentation on active security.
* ActiveProtocolSuite.verify() didn't work with scalar secrets.
* Calculator service supports unix domain sockets.
* Improved test coverage.
* Switched from setuptools to flit for builds.


Cicada 0.7.0 - August 9th, 2022
-------------------------------

* Added ActiveProtocol, our first protocol with a security model against active adversaries.
* Added private summation and private dot product operations to all protocol objects.
* Added TLS support to SocketCommunicator.split() and SocketCommunicator.shrink().
* Added SocketCommunicator.run_forever() for starting MPC services.
* Created cicada.calculator as an example of MPC-as-a-service.
* Regression tests use the calculator service, eliminating lots of repetitive test code.
* Rename Tags -> Tag for consistency, clarity.
* Rename all_gather() -> allgather() for consistency, clarity.
* Raise a better error if a send operation would block.
* NetstringSocket didn't handle sending large messages correctly.



Cicada 0.6.0 - June 17th, 2022
------------------------------

* SocketCommunicator.run() would sometimes hang returning results from large numbers of players.
* Sped-up regression tests significantly by removing unnecessary redundancy.
* Began formally testing Cicada with Python 3.8 and 3.10.
* Added user guide sections on Shamir sharing and fault recovery.
* Reorganized SocketCommunicator statistics, and added statistics organized by message type.
* Added the cicada-perf command for benchmarking communications.
* Added `indices` and `threshold` properties to ShamirBasicProtocol and ShamirProtocol.
* SocketCommunicator setup didn't always use the correct rank and name in log output.
* Fixed a problem with the way thresholds are constrained in ShamirProtocol.
* Explicitly specify process names for debugging with SocketCommunicator.run().
* Removed obsolete code.

Cicada 0.5.1 - May 4th, 2022
----------------------------

* A botched merge left some changes out of the 0.5.0 release.

Cicada 0.5.0 - April 28th, 2022
-------------------------------

* ShamirProtocol provides the same operations as AdditiveProtocol.
* New ShamirBasicProtocol provides a subset of operations, but with relaxed constraints on share degree.
* Reduced per-message SocketCommunicator overhead.
* SocketCommunicator.run, SocketCommunicator.shrink, and SocketCommunicator.split support Unix domain sockets.
* Rewrite the SocketCommunicator.shrink implementation for simplicity.
* SocketCommunicator can raise exceptions while sending.
* Rewrote the SocketCommunicator message queue for reduced resource consumption and greater flexibility.
* Point-to-point SocketCommunicator operations support user-defined message tags.
* Reduced the number of coordinating messages during logging.
* Many improvements in library logging output.
* Added a user guide article on logging.

Cicada 0.4.0 - March 21st, 2022
-------------------------------

* SocketCommunicator supports TLS encryption.
* SocketCommunicator supports Unix domain sockets.
* Moved SocketCommuniator initialization into a separate module.
* Fixed problems with AdditiveProtocol.private_public_power.
* Reduced default log output, and made log output more consistent.
* Raise an exception trying to use a communicator that's been freed.
* Removed the cicada.bind module.

Cicada 0.3.0 - February 1st, 2022
---------------------------------

* Improved code coverage from 80% to 95%.
* Greatly improved SocketCommunicator startup behavior.
* SocketCommunicator can choose random ports for players other than root.
* Made SocketCommunicator.override() more flexible.
* Fixed a bug in AdditiveProtocol.zigmoid().
* Eliminated warnings waiting for interactive user input.
* cicada.interactive.secret_input() just prompts for input.
* Created new `cicada` command to replace `cicada-exec`, which is deprecated.

Cicada 0.2.0 - January 25th, 2022
---------------------------------

* Replaced NNGCommunicator with SocketCommunicator, for vastly improved reliability.
* Added ReLU function.
* Added absolute value function.
* Added bit decomposition function.
* Added division function.
* Added equality comparison function.
* Added floor function.
* Added less-than-zero function.
* Added logical negation function.
* Added min and max functions.
* Added multiplicative inverse function.
* Added zigmoid function.
* Added many new documentation topics, including communication patterns, random seeds, timeouts, and working with multiple communicators.
* Switched to Github Actions for continuous integration.
* Improved code test coverage.

Cicada 0.1.0 - June 28th, 2021
------------------------------

* Initial Release.
