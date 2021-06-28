.. image:: ../artwork/cicada.png
  :width: 200px
  :align: right

Contributing
============

Getting Started
---------------

If you haven't already, you'll want to get familiar with the Cicada repository
at https://github.com/sandialabs/cicada ... there, you'll find the Cicada
sources, issue tracker, and wiki.

Next, you'll need to install Cicada's :ref:`dependencies`.  Then, you'll be
ready to get Cicada's source code and use setuptools to install it. To do
this, you'll almost certainly want to use "develop mode".  Develop mode is a a
feature provided by setuptools that links the Cicada source code into the
install directory instead of copying it ... that way you can edit the source
code in your git sandbox, and you don't have to re-install it to test your
changes::

    $ git clone https://github.com/sandialabs/cicada.git
    $ cd cicada
    $ python setup.py develop

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

    $ cd cicada
    $ python regression.py

The tests will run, providing feedback on successes / failures.

Test Coverage
-------------

When you run the test suite with `regression.py`, it also automatically
generates code coverage statistics.  To see the coverage results, open
`cicada/.cover/index.html` in a web browser.

Building the Documentation
--------------------------

To build the documentation, run::

    $ cd cicada/docs
    $ make html

Once the documentation is built, you can view it by opening
`cicada/docs/_build/html/index.html` in a web browser.
