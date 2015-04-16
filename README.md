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


Contact & Support
-----------------

* Homepage: *(not yet)*
* Documentation: *(not hosted yet, but you can build it in `docs`)*
* Wiki: <https://github.com/whutch/atria/wiki>

You can also email me questions and comments at <will@whutch.com>.


[miniboa]: https://code.google.com/p/miniboa
[miniboa-py3]: https://github.com/pR0Ps/miniboa-py3
[python]: https://www.python.org
[redis]: http://redis.io
[redis-py]: https://pypi.python.org/pypi/redis
[redis-quick-start]: http://redis.io/topics/quickstart
[virtualenv]: https://virtualenv.pypa.io
