# Atria Coding Style

A uniform coding style is critical to a happy and productive collaboration among coders. Having a clear standard can greatly increase readability and maintainability, and reduces headaches when it comes time to merge. Please do your best to adhere to these specifications when contributing.


## General

All Python code should follow the [PEP-8][pep8] specifications, unless otherwise noted here.

Including (but not limited to):
 * 4 spaces per indentation level, no tabs.
 * Lines are limited to a width of 79 columns.
 * Two blank lines to separate module-level blocks, one line for class/function-level blocks.
 * Classes are CamelCase, functions and local variables are lower_case, and global variables (which should be constants) are UPPER_CASE. Never use mixedCase.
 * Comments should be in English, be complete sentences, and end in a period. A block of comments should have two spaces (or a new-line) after sentence-ending periods.

With a few exceptions:
 * Python modules should include an encoding declaration, even when using the Python 3 default UTF-8.
 * Modules within the `atria.core` package should use relative imports when importing other modules from `atria.core`.
 * Wild-card importing is only allowed for the `atria.core.const` module (`from .const import *`).

And additions:
 * Use double quotes for all strings, or single quotes for strings that contain double quotes.

A quick way to check if your code conforms with most of these standards is to run it through [flake8][flake8] (all contributions will be checked against this anyway as it is included in our test suite).


## Imports

The import block should contain up to three sections, in this order:
 * Standard library imports
 * Third-party imports
 * Local project imports

Each section should be separated by a single blank line. The whole block should be separated from the preceding header comments by a single blank line, and from the subsequent code by two blank lines.

Each section should be sorted alphabetically. If multiple objects are imported from a module, the list of objects should also be alphabetized.


## Docstrings

All public modules, classes, methods, and functions should have docstrings, and all docstrings should follow the [PEP-257][pep257] specifications, unless otherwise noted here. Private classes, methods, and functions (`_foo`, `__foo`, or `__foo__`) do not require docstrings, but it is encouraged where documentation would be helpful.

Overview:
 * The first line of all module and class docstrings should be a one-line statement of what that module or class is. (`"""A class that does some stuff."""`)
 * The first line of all function and method docstrings should be a one-line imperative statement that describes what it does. (`"""Do this and that."""`)
 * Multi-line docstrings should have the first line of docstring on the same line as the opening quotes, then a blank line, then any remaining comments, followed by another blank line before the closing quotes.
 * If it is a docstring for a class or a function/method that is broken up by blank lines into logical sections, the docstring should be surrounded by single blank lines.


[flake8]: https://pypi.python.org/pypi/flake8
[pep8]: https://www.python.org/dev/peps/pep-0008
[pep257]: https://www.python.org/dev/peps/pep-0257
