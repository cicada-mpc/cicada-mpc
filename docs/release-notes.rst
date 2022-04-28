.. image:: ../artwork/cicada.png
    :width: 200px
    :align: right

.. _release-notes:

Release Notes
=============

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
