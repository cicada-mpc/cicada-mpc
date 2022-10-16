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

Documentation
-------------

We assume that you'll normally access this documentation online, but if
you want a local copy on your own computer, just do the following:

First, install Cicada, along with all of the dependencies needed to build
the docs::

    $ pip install cicada-mpc[doc]

Next, do the following to download a tarball to the current directory containing
all of the Cicada source code, including the documentation::

    $ pip download cicada-mpc --no-binary=:all: --no-deps

Now, you can extract the tarball contents and build the source (note that your
version number will likely be different)::

    $ tar xzvf cicada-mpc-0.8.0.tar.gz
    $ cd cicada-mpc-0.8.0/docs
    $ make html

Once the documentation is built, you can view it by opening
`cicada-mpc-0.8.0/docs/_build/html/index.html` in a web browser.
