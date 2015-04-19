Atria MUD Server
================

Atria is a pure-Python MUD server designed with modularity and ease of development in mind. It was originally created as an exercise, as I had always wanted to write a MUD from scratch, and as such does not make use of many third-party libraries (just [miniboa][miniboa-py3] for Telnet protocol handling and [redis-py] for inter-process messaging, neither of which are wheels that I wanted to reinvent).


Installation
------------

There isn't a proper package set up yet, so for now Atria is best installed by cloning the git repo:
```
git clone https://github.com/whutch/atria.git mymud
```

It's also *highly* recommended that you set up a [virtualenv] to run Atria in:
```
cd mymud
virtualenv -p python3 --no-site-packages .venv
source .venv/bin/activate
```


Dependencies
------------

Atria runs on [Python 3.4][python] and is as yet untested on any later versions. There are currently no plans to support earlier versions.

Atria requires a running [Redis][redis] server for messages, as well as the [Redis Python bindings][redis-py]. It also makes use of [miniboa-py3], a Python 3 port of [miniboa], which is a tiny, asynchronous Telnet server. Our modified copy of miniboa is included in `atria/libs`.

To install the Python package dependencies, run:
```
pip install -r requirements.txt
```
*Note: If not using virtualenv (you should!), you will need to run this command with elevated privileges (sudo).*

See the [Redis Quick Start guide][redis-quick-start] for details on installing and configuring Redis.


Configuration
-------------

All the post-installation configuration settings are stored in `atria/settings.py`.

Some key settings you'll probably want to change:
 * `BIND_ADDRESS`: The IP to bind the listener to, default is 127.0.0.1, change to 0.0.0.0 to allow external connections.
 * `BIND_PORT`: The port to listen for new connections on, default is 4000.
 * `LOG_PATH`: The path for the server log, defaults to `(project root)/logs/mud.log` (rotates daily at midnight, which are also settings that can be changed).
 * `DATA_DIR`: The path to a folder where local data should be loaded from and saved to (serialized objects, flat text files, etc.), defaults to `(project root)/data`.


Usage
-----

To start the Atria server, simply run:
```
python -m atria
```

After booting, the server will be ready to accept Telnet connections on whatever address and port you specified in `atria/settings.py` (default is localhost and port 4000).


Testing
-------

Atria includes a suite of unit tests in [pytest] format. To run the test suite you will first need to install pytest and the plugins we use (coverage, flake8, timeout). To install all the test suite dependencies, run:
```
pip install -r tests/requirements.txt
```
*Note: If not using virtualenv (you should!), you will need to run this command with elevated privileges (sudo).*

After pytest is installed, you can run the test suite via our Makefile:
```
make tests
```

If you don't have `make` available (a make.bat file will be in the works for Windows users), you can call pytest directly like so:
```
py.test --flake8 atria tests
```


Development
-----------

* Git repository: <https://github.com/whutch/atria>
* Issue tracker: <https://github.com/whutch/atria/issues>

Please read the [style guide][style] for coding conventions and style guidelines before submitting any pull requests or committing changes.


Contact & Support
-----------------

* Homepage: *(not yet)*
* Documentation: *(not hosted yet, but you can build it in `docs`)*
* Wiki: <https://github.com/whutch/atria/wiki>

You can also email me questions and comments at <will@whutch.com>.


[miniboa]: https://code.google.com/p/miniboa
[miniboa-py3]: https://github.com/pR0Ps/miniboa-py3
[pytest]: https://pytest.org/latest
[python]: https://www.python.org
[redis]: http://redis.io
[redis-py]: https://pypi.python.org/pypi/redis
[redis-quick-start]: http://redis.io/topics/quickstart
[style]: https://github.com/whutch/atria/blob/master/STYLE.md
[virtualenv]: https://virtualenv.pypa.io
