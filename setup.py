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

from setuptools import setup, find_packages
import re

setup(
    name="cicada-mpc",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: Education",
        "Intended Audience :: Information Technology",
        "Intended Audience :: Science/Research",
        "Natural Language :: English",
        "Programming Language :: Python :: 3",
        "Topic :: Communications",
        "Topic :: Scientific/Engineering",
        "Topic :: Security :: Cryptography",
        "Topic :: Utilities",
    ],
    description="Flexible toolkit for fault tolerant secure multiparty computation.",
    install_requires=[
        "netifaces",
        "numpy",
        "pynetstring",
    ],
    long_description="""Cicada is a flexible toolkit for working with fault-tolerant secure multiparty computation.  See the Cicada documentation at http://cicada-mpc.readthedocs.io, and the Cicada sources at http://github.com/cicada-mpc/cicada-mpc.""",
    maintainer="Timothy M. Shead",
    maintainer_email="tshead@sandia.gov",
    packages=find_packages(),
    project_urls={
        "Chat": "https://github.com/cicada-mpc/cicada-mpc/discussions",
        "Coverage": "https://coveralls.io/r/cicada-mpc/cicada-mpc",
        "Documentation": "https://cicada-mpc.readthedocs.io",
        "Issue Tracker": "https://github.com/cicada-mpc/cicada-mpc/issues",
        "Source": "https://github.com/cicada-mpc/cicada-mpc",
    },
    scripts=[
        "bin/cicada",
        "bin/cicada-perf",
    ],
    version=re.search(
        r"^__version__ = ['\"]([^'\"]*)['\"]",
        open(
            "cicada/__init__.py",
            "r").read(),
        re.M).group(1),
)
