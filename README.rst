cwmud
=====
An extendable, modular MUD server.

|version| |license| |pyversions| |build| |coverage|

Clockwork is a pure-Python MUD server designed with modularity and ease of development in mind.


Current State
-------------

This isn't a viable MUD server yet. There's account creation, basic character creation, rooms, talking, and walking around, but that's about it. There are also no permission controls on admin commands yet, so anyone can do whatever they want (which is good because there is no concept of an admin yet).

The ``reload`` command was broken with the recent changes to client/protocol serving (the server reloads, but any connected clients will get dumped into a limbo state of disconnected I/O), but it should be fixed in the next minor version.

So anyway, very under-construction at the moment.


License
-------

Clockwork uses the MIT license. See the `license file`_ for more details.


Installation
------------

First, it is *highly* recommended that you set up a `virtualenv`_ to run Clockwork in::

    $ cd mymud
    $ virtualenv -p python3 --no-site-packages .venv
    $ source .venv/bin/activate

Then, Clockwork can be installed through pip::

    $ pip install cwmud

*Note: If not using virtualenv (you should!), you will need to run this command with elevated privileges (sudo).*


Dependencies
------------

Clockwork runs on `Python`_ 3.4 and is as yet untested on any later versions. There are currently no plans to support earlier versions.

Clockwork requires a running `Redis`_ server and the `redis-py`_ bindings package for messages, and `bcrypt`_ for password hashing (and bcrypt in turn requires libffi). It also makes use of `miniboa-py3`_, a Python 3 port of `miniboa`_, which is a tiny, asynchronous Telnet server. Our modified copy of miniboa is included in ``cwmud/libs``.

To install the libffi library on Debian/Ubuntu, run::

    $ sudo apt-get install libffi-dev

See the `Redis Quick Start`_ guide for details on installing and configuring Redis.


Configuration
-------------

All the post-installation configuration settings are stored in ``cwmud/settings.py``.

Some key settings you'll probably want to change:

    ``DEFAULT_HOST``: The IP to bind the listener to, default is ``"localhost"`` (127.0.0.1), change to ``"0.0.0.0"`` to allow external connections.

    ``DEFAULT_PORT``: The port to listen for new Telnet connections on, default is ``4000``.

    ``LOG_PATH``: The path for the server log, defaults to ``"./logs/mud.log"`` (rotates daily at midnight, which are also settings that can be changed).

    ``DATA_DIR``: The path to a folder where local data should be loaded from and saved to (serialized objects, flat text files, etc.), defaults to ``"./data"``.

These (and other) options can also be set on a per-run basis using command-line options (see below).


Usage
-----

To start the Clockwork server, simply run::

    $ python -m cwmud


For a full list of uses and options, see the help output by running::

    $ python -m cwmud --help


After booting, the server will be ready to accept Telnet connections on whatever address and port you specified in ``cwmud/settings.py`` (default is localhost and port 4000).


Testing
-------

Clockwork includes a suite of unit tests in `pytest`_ format. To run the test suite you will first need to install pytest and the plugins we use (coverage, flake8, timeout). To install all of the test suite dependencies, run::

    $ pip install -r tests/requirements.txt

*Note: If not using virtualenv (you should!), you will need to run this command with elevated privileges (sudo).*


After pytest is installed, you can run the test suite via our Makefile::

    $ make tests

If you don't have ``make`` available (a make.bat file will be in the works for Windows users), you can call pytest directly like so::

    $ py.test --flake8 cwmud tests


Development
-----------

* Git repository: https://github.com/whutch/cwmud
* Project planning: https://github.com/whutch/cwmud/projects
* Issue tracker: https://github.com/whutch/cwmud/issues

Please read the `style guide`_ for coding conventions and style guidelines before submitting any pull requests or committing changes.


Contact & Support
-----------------

* Homepage: *(not yet)*
* Documentation: *(not hosted yet, but you can build it in* ``docs`` *)*
* Wiki: https://github.com/whutch/cwmud/wiki

You can email me questions and comments at will@whutch.com. You can also find me as Kazan on the `Mud Coders Slack group`_ (you can find the sign-up page on the `Mud Coders Guild blog`_).

.. |build| image:: https://circleci.com/gh/whutch/cwmud/tree/master.svg?style=shield
    :target: https://circleci.com/gh/whutch/cwmud/tree/master
    :alt: Latest build via CircleCI
.. |coverage| image:: https://codecov.io/github/whutch/cwmud/coverage.svg?branch=master
    :target: https://codecov.io/github/whutch/cwmud?branch=master
    :alt: Latest code coverage via Codecov
.. |license| image:: https://img.shields.io/pypi/l/cwmud.svg
    :target: https://github.com/whutch/cwmud/blob/master/LICENSE.txt
    :alt: MIT license
.. |pyversions| image:: https://img.shields.io/pypi/pyversions/cwmud.svg
    :target: http://pypi.python.org/pypi/cwmud/
    :alt: Supported Python versions
.. |version| image:: https://img.shields.io/pypi/v/cwmud.svg
    :target: https://pypi.python.org/pypi/cwmud
    :alt: Latest version on PyPI

.. _bcrypt: https://github.com/pyca/bcrypt
.. _license file: https://github.com/whutch/cwmud/blob/master/LICENSE.txt
.. _miniboa: https://code.google.com/p/miniboa
.. _miniboa-py3: https://github.com/pR0Ps/miniboa-py3
.. _Mud Coders Guild blog: http://mudcoders.com
.. _Mud Coders Slack group: https://mudcoders.slack.com
.. _pytest: https://pytest.org/latest
.. _Python: https://www.python.org
.. _Redis: http://redis.io
.. _Redis Quick Start: http://redis.io/topics/quickstart
.. _redis-py: https://pypi.python.org/pypi/redis
.. _style guide: https://github.com/whutch/cwmud/blob/master/STYLE.md
.. _virtualenv: https://virtualenv.pypa.io
