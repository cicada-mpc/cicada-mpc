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
Cicada's TCP/IP communication layer with your own communication hardware or
protocols.

**Supports fault tolerance at the application level.**

Cicada raises exceptions when errors occur, instead of just dying. Researchers
can use Cicada's builtin functionality to recover from errors when they occur,
or explore new fault-tolerance strategies and algorithms.

**Highly refined API developed alongside research in privacy preserving machine learning.**

Code using existing Cicada functionality is clear, concise, and explicit ...
while retaining the flexibility to develop new algorithms and protocols.

Sound interesting?  See the :ref:`tutorial` to get started!



Documentation
=============

.. toctree::
    :maxdepth: 2

    tutorial.ipynb
    user-guide.rst
    reference.rst
    installation.rst
    dependencies.rst
    compatibility.rst
    contributing.rst
    release-notes.rst

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`

