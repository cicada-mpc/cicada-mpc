.. image:: ../artwork/cicada.png
  :width: 200px
  :align: right

.. _dependencies:

Dependencies
============

Minimum Requirements
--------------------

To use Cicada you will need the following:

* Python >= 3.7 - http://python.org
* netifaces - Network interface retrieval API - https://github.com/al45tair/netifaces
* numpy - The popular scientific computing framework - https://numpy.org
* pynetstring - A module for encoding and decoding netstrings - https://github.com/rj79/pynetstring
* shamir - Fast, secure, pure python implementation of Shamir's secret sharing algorithm - https://github.com/kurtbrose/shamir

If you install Cicada using setup.py or pip, these dependencies will be
automatically installed for you.


Source Installation
-------------------

If you're installing Cicada from source, you'll need setuptools to run the
Cicada setup.py script:

* setuptools - https://packaging.python.org/tutorials/installing-packages

Regression Testing
------------------

The following are required to run Cicada's regression tests and view
code coverage:

* behave - BDD test framework - https://behave.readthedocs.io
* coverage - code coverage module - http://nedbatchelder.com/code/coverage

Generating Documentation
------------------------

And you'll need to following to generate this documentation:

* Sphinx - documentation builder - http://sphinx-doc.org
* Sphinx readthedocs theme - https://github.com/snide/sphinx_rtd_theme
* nbsphinx - Jupyter notebook tools for Sphinx - https://nbsphinx.readthedocs.io
* Sphinx-Gallery - creates a gallery of examples from scripts - https://sphinx-gallery.github.io
