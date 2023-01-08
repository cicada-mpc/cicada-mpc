.. image:: ../artwork/cicada.png
  :width: 200px
  :align: right

.. _development:

Development
===========

Getting Started
---------------

If you haven't already, you'll want to get familiar with the Cicada repository
at https://github.com/cicada-mpc/cicada-mpc ... there, you'll find the Cicada
source code, issue tracker, discussions, and wiki.

You'll need to install `pandoc <https://pandoc.org>`_,
which can't be installed via pip.  If you use `Conda <https://docs.conda.io/en/latest/>`_
(which we strongly recommend), you can install it as follows::

    $ conda install pandoc

Next, you'll need to install all of the extra dependencies needed for Cicada development::

    $ pip install cicada-mpc[all]

Then, you'll be ready to obtain Cicada's source code and install it using
"editable mode".  Editable mode is a feature provided by `pip` that links the
Cicada source code into the install directory instead of copying it ... that
way you can edit the source code in your git sandbox, and you don't have to
keep re-installing it to test your changes::

    $ git clone https://github.com/cicada-mpc/cicada-mpc.git
    $ cd cicada-mpc
    $ pip install --editable .

Versioning
----------

Cicada version numbers follow the `Semantic Versioning <http://semver.org>`_ standard.

Coding Style
------------

The Cicada source code follows the `PEP-8 Style Guide for Python Code <http://legacy.python.org/dev/peps/pep-0008>`_.

Running Regression Tests
------------------------

To run the Cicada test suite, simply run `regression.py` from the
top-level source directory::

    $ cd cicada-mpc
    $ python regression.py

The tests will run, providing feedback on successes / failures.

Test Coverage
-------------

When you run the test suite with `regression.py`, it also automatically
generates code coverage statistics.  To see the coverage results, open
`cicada-mpc/.cover/index.html` in a web browser.

Building the Documentation
--------------------------

To build the documentation, run::

    $ cd cicada-mpc/docs
    $ make html

Once the documentation is built, you can view it by opening::

    cicada-mpc/docs/_build/html/index.html

in a web browser.
