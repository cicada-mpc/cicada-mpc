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
you want a local copy on your own computer, do the following:

First, you'll need the `pandoc <https://pandoc.org>`_ universal document
converter, which can't be installed with pip ... if you use `Conda <https://docs.conda.io/en/latest/>`_
(strongly recommended), you can install it with the following::

    $ conda install pandoc

Once you have pandoc, install Cicada along with all of the dependencies needed to build the docs::

    $ pip install cicada-mpc[doc]

Next, do the following to download a tarball to the current directory
containing all of the Cicada source code, which includes the documentation::

    $ pip download cicada-mpc --no-binary=:all: --no-deps

Now, you can extract the tarball contents and build the documentation (adjust the
following for the version you downloaded)::

    $ tar xzvf cicada-mpc-<version>.tar.gz
    $ cd cicada-mpc-<version>/docs
    $ make html

Once the documentation is built, you can view it by opening::

    cicada-mpc-<version>/docs/_build/html/index.html

in a web browser.
