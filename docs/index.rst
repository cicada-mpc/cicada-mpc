.. image:: ../artwork/cicada.png
    :width: 200px
    :align: right


Welcome!
========

Welcome to Cicada ... a set of tools for working with fault-tolerant secure
multiparty computation.  Notable Cicada features include:

**Written in Python for simplicity and ease of use.**

There are no weird DSLs or runtimes to learn and deploy, making it easier to
learn, experiment, and integrate MPC computation into existing systems.

**Uses a communication abstraction layer inspired by the widely used MPI standard.**

Cicada benefits from decades of research in HPC, and you can easily replace
Cicada's builtin TCP/IP communication layer to support your own networking stack.

**Supports fault tolerance at the application level.**

Cicada raises exceptions when errors occur, where most MPC libraries just die.
Developers can use Cicada's builtin functionality to recover from errors when
they occur, and researchers can explore new fault-tolerance strategies and
algorithms.

**Highly refined API developed alongside research in privacy preserving machine learning.**

Code using existing Cicada functionality is clear, concise, and explicit ...
while retaining the flexibility and generality to guide development of new
algorithms and protocols.

Sound interesting?  See the :ref:`tutorial` to get started!


Documentation
=============

.. toctree::
    :maxdepth: 2

    tutorial.ipynb
    user-guide.rst
    commands.rst
    reference.rst
    installation.rst
    dependencies.rst
    compatibility.rst
    contributing.rst
    release-notes.rst
    support.rst

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`

