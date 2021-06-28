.. image:: ../artwork/cicada.png
    :width: 200px
    :align: right


Welcome!
========

Welcome to Cicada ... a set of tools for running experiments in fault-tolerant
secure multiparty computation.  Notable Cicada features include:

**Written in Python for simplicity and ease of use.**

There are no weird DSLs or runtimes to learn and deploy, making it easier to
learn, experiment, and integrate MPC computation into existing systems.

**Uses a communication abstraction layer inspired by the widely used MPI standard.**

Cicada benefits from decades of research in HPC, and you can easily substitute
your own communication hardware or protocols.

**Supports fault tolerance at the application level.**

Cicada raises exceptions when errors occur, instead of just dying. Use the
builtin functionality to recover from errors when they occur, or explore new
fault-tolerance strategies and algorithms.

**Highly refined API developed in parallel with research in privacy preserving machine learning.**

Code using existing Cicada functionality is clear, concise, and explicit ...
while retaining the flexibility to explore new algorithms.

Sound interesting?  See the :ref:`tutorial` to get started!



Documentation
=============

.. toctree::
    :maxdepth: 2

    installation.rst
    dependencies.rst
    compatibility.rst
    contributing.rst
    tutorial.ipynb
    reference.rst

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`

