.. image:: ../artwork/cicada.png
    :width: 200px
    :align: right


Welcome!
========

Welcome to Cicada ... a set of tools for working with fault-tolerant secure
multiparty computation.  Notable Cicada features include:

**Written in Python for simplicity and ease of use.**

Cicada doesn't rely on weird DSLs or runtimes, making it easier to
learn, experiment, and integrate MPC computation into existing systems.

**Communication inspired by the widely used MPI standard.**

Cicada benefits from decades of research in HPC, and you can easily replace
Cicada's builtin TCP/IP communication layer to support your own networking stack.

**Supports fault tolerance at the application level.**

Cicada raises exceptions when errors occur, where most MPC runtimes just die.
Developers can use Cicada's builtin functionality to recover from errors when
they occur, and researchers can explore new fault-tolerance strategies and
algorithms.

**Highly refined API.**

Cicada was developed alongside our research in privacy preserving machine
learning, so code using Cicada is clear, concise, and explicit ... while
retaining the flexibility and generality to guide development of new algorithms
and protocols.

Sound interesting?  See the :ref:`tutorial` to get started!


Documentation
=============

.. toctree::
    :maxdepth: 2

    installation.rst
    tutorial.ipynb
    user-guide.rst
    commands.rst
    development.rst
    reference.rst
    compatibility.rst
    release-notes.rst
    support.rst

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`

