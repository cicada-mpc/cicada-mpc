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

import glob
import os
import pkgutil
import sys

from behave import *

import IPython
import nbformat


root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
docs_dir = os.path.join(root_dir, "docs")
package_dir = os.path.join(root_dir, "cicada")


@given(u'all public modules')
def step_impl(context):
    def walk_modules(package, path):
        modules = []
        modules.append(package)
        for loader, name, is_package in pkgutil.iter_modules([path]):
            modules += walk_modules(package + "." + name, os.path.join(path, name))
        return modules
    context.modules = sorted(walk_modules("cicada", package_dir))


@given(u'the reference documentation')
def step_impl(context):
    context.references = []
    for directory, subdirectories, filenames in os.walk(docs_dir):
        for filename in filenames:
            if os.path.splitext(filename)[1] not in [".rst"]:
                continue
            if not filename.startswith("cicada."):
                continue

            context.references.append(os.path.join(directory, filename))
    context.references = sorted(context.references)


@then(u'every module must have a section in the reference documentation')
def step_impl(context):
    for module in context.modules:
        if os.path.join(docs_dir, module + ".rst") not in context.references:
            raise AssertionError("No matching documentation found for the %s module." % module)


@then(u'every section in the reference documentation must match a module')
def step_impl(context):
    modules = [os.path.join(docs_dir, module + ".rst") for module in context.modules]
    for reference in context.references:
        if reference not in modules:
            raise AssertionError("No matching module found for %s." % reference)


@given(u'all documentation notebooks')
def step_impl(context):
    context.notebooks = [path for path in glob.glob("docs/**/*.ipynb", recursive=True) if "_build" not in path]


@then(u'every notebook code cell should have been executed.')
def step_impl(context):
    unexecuted_notebooks = set()

    for path in context.notebooks:
        notebook = nbformat.read(path, as_version=4)
        for cell in notebook.cells:
            if cell.cell_type == "code":
                if not cell["execution_count"]:
                    unexecuted_notebooks.add(path)

    if unexecuted_notebooks:
        raise AssertionError(f"Some notebooks contain unexecuted cells: {', '.join(sorted(unexecuted_notebooks))}")


@then(u'every notebook runs without error')
def step_impl(context):
    for notebook in context.notebooks:
        context.execute_steps(f"Then notebook {notebook} runs without error")


@then(u'notebook {notebook} runs without error')
def step_impl(context, notebook):
    notebook = os.path.abspath(notebook)
    notebook_dir = os.path.dirname(notebook)
    working_dir = os.getcwd()

    sys.path.append(notebook_dir)
    os.chdir(notebook_dir)

    exception = None
    try:
        with open(notebook) as stream:
            notebook = nbformat.read(stream, as_version=4)

        shell = IPython.core.interactiveshell.InteractiveShell.instance()
        nblocals = dict()

        for cell in notebook.cells:
            if cell.cell_type == "code":
                code = shell.input_transformer_manager.transform_cell(cell.source)
                exec(code, nblocals)
    except Exception as e:
        exception = e

    os.chdir(working_dir)
    sys.path.remove(notebook_dir)

    if exception is not None:
        raise exception
