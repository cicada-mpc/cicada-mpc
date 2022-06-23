# Copyright 2021 National Technology & Engineering Solutions
# of Sandia, LLC (NTESS). Under the terms of Contract DE-NA0003525 with NTESS,
# the U.S. Government retains certain rights in this software.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.

import os
import sys
sys.path.insert(0, os.path.abspath(".."))


# -- Project information -----------------------------------------------------

project = "Cicada"
copyright = "2021, National Technology & Engineering Solutions of Sandia, LLC (NTESS)"
author = "Timothy M. Shead"

# The full version, including alpha/beta/rc tags
import cicada
release = cicada.__version__


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named "sphinx.ext.*") or your custom
# ones.

import sphinx_rtd_theme

extensions = [
#    "IPython.sphinxext.ipython_console_highlighting",
    "nbsphinx",
    "sphinxarg.ext",
    "sphinx.ext.autodoc",
    "sphinx.ext.intersphinx",
    "sphinx.ext.mathjax",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx_gallery.load_style",
    "sphinx_rtd_theme",
]

intersphinx_mapping = {
    "numpy": ("https://numpy.org/doc/stable", None),
    "python": ("https://docs.python.org/3", None),
    }

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# The master toctree document.
master_doc = "index"

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

nitpicky = True

# -- nbsphinx options --------------------------------------------------------

nbsphinx_execute = "never"

nbsphinx_thumbnails = {
    "user-guide/absolute": "_static/absolute.png",
    "user-guide/division": "_static/division.png",
    "user-guide/equality": "_static/equality.png",
    "user-guide/floor": "_static/floor.png",
    "user-guide/less-than": "_static/less-than.png",
    "user-guide/less-than-zero": "_static/less-than-zero.png",
    "user-guide/logical-not": "_static/logical-not.png",
    "user-guide/logical-xor": "_static/logical-xor.png",
    "user-guide/modulus": "_static/modulus.png",
    "user-guide/multiplicative-inverse": "_static/multiplicative-inverse.png",
    "user-guide/multiplication-and-truncation": "_static/multiplication.png",
    "user-guide/power": "_static/power.png",
    "user-guide/relu": "_static/relu.png",
    "user-guide/zigmoid": "_static/zigmoid.png",
    "user-guide/communication-patterns": "_static/communication-patterns_generic.png",
    "user-guide/timeouts": "_static/timeouts.png",
}

# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.

html_theme = "sphinx_rtd_theme"

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ["_static"]

def warn_undocumented_members(app, what, name, obj, options, lines):
    if what not in [] and len(lines) == 0:
        print("WARNING: %s is undocumented: %s" % (what, name))
        lines.append(".. Warning:: %s '%s' undocumented" % (what, name))

def setup(app):
    app.connect("autodoc-process-docstring", warn_undocumented_members);

tls_verify = False
