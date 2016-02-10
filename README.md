Atria MUD Server
================

[![Circle CI](https://circleci.com/gh/whutch/atria/tree/master.svg?style=shield)][build] [![codecov.io](https://codecov.io/github/whutch/atria/coverage.svg?branch=master)][coverage]

Atria is a pure-Python MUD server designed with modularity and ease of development in mind. It was originally created as an exercise, as I had always wanted to write a MUD from scratch, so I used as few third-party libraries as I was able (exceptions were made for Telnet handling, inter-process messaging, password hashing, and other such wheels that I didn't want to re-invent).


Current State
-------------

This isn't a viable MUD server yet. There's account creation, basic character creation, rooms, talking, and walking around, but that's about it. There are also no permission controls on admin commands yet, so anyone can do whatever they want (which is good because there is no concept of an admin yet).

So anyway, very under-construction at the moment.


License
-------

It's MIT licensed. Go crazy. See the [license file][license] for more details.


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

Atria requires a running [Redis][redis] server and the [Redis Python bindings][redis-py] for messages, and [bcrypt] for password hashing (and bcrypt in turn requires libffi). It also makes use of [miniboa-py3], a Python 3 port of [miniboa], which is a tiny, asynchronous Telnet server. Our modified copy of miniboa is included in `atria/libs`.

To install the libffi library on Debian/Ubuntu, run:
```
sudo apt-get install libffi-dev
```

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

You can email me questions and comments at <will@whutch.com>. You can also find me as Kazan on the [Mud Coders Slack group][slack] (the signup is on the right side of [this page][mudcoders]).


[bcrypt]: https://github.com/pyca/bcrypt
[build]: https://circleci.com/gh/whutch/atria/tree/master
[coverage]: https://codecov.io/github/whutch/atria?branch=master
[license]: https://github.com/whutch/atria/blob/master/LICENSE.txt
[miniboa]: https://code.google.com/p/miniboa
[miniboa-py3]: https://github.com/pR0Ps/miniboa-py3
[mudcoders]: http://mudcoders.com
[pytest]: https://pytest.org/latest
[python]: https://www.python.org
[redis]: http://redis.io
[redis-py]: https://pypi.python.org/pypi/redis
[redis-quick-start]: http://redis.io/topics/quickstart
[slack]: https://mudcoders.slack.com
[style]: https://github.com/whutch/atria/blob/master/STYLE.md
[virtualenv]: https://virtualenv.pypa.io
