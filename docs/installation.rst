.. image:: ../artwork/cicada.png
  :width: 200px
  :align: right

.. _installation:

Installation
============

Cicada
------

To install the latest stable version of Cicada and its dependencies, use `pip`::

    $ pip install cicada-mpc

... once it completes, you'll be able to use all of Cicada's features.

Local Documentation
-------------------

We assume that you'll normally access this documentation online, but if
you want a local copy on your own computer, do the following instead:

First, install Cicada and its dependencies, plus all of the dependencies
required to build the docs::

    $ pip install cicada-mpc[doc]

Next, do the following to download a tarball containing
the Cicada source code, which includes the documentation::

    $ pip download cicada-mpc --no-binary=:all: --no-deps

The file will be downloaded to the current directory.  Now, you can extract its
contents and build the source (substitute the correct version number for the
file you downloaded)::

    $ tar xzvf cicada-mpc-<version>.tar.gz
    $ cd cicada-mpc-<version>/docs
    $ make html

Once the documentation is built, you can view it by opening::

    cicada-mpc-<version>/docs/_build/html/index.html

in a web browser.
