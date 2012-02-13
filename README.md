``pydaemonize`` 0.1
===================

``pydaemonize`` is a library of utilities for writing system daemons in Python. It is a direct port of the Haskell library ``hdaemonize``. Its source code is available from GitHub at http://github.com/madhadron/pydaemonize.


License
-------

``pydaemonize`` is released under GNU General Public License version 3, or any later version. A copy is included in the source distribution as ``LICENSE.txt``.


Installation
------------

``pydaemonize`` is distributed via the Python Package Index (PyPI). To install it, run

    $ pip install pydaemonize

This will always be up to date with the ``master`` branch on GitHub. You can get the latest development source from the ``dev`` branch.


Quick Start
-----------

Subclass the ``Daemon`` class in ``pydaemonize``, and override the ``action`` method to implement your daemon's behavior. The simplest possible such daemon is

```python
import pydaemonize

class NopDaemon(pydaemonize.Daemon):
    def action(self):
        while True:
            pass

if __name__=='__main__':
   NoDaemon()
```

When you run this script, it goes through all the steps to become a daemon on the system, sets up some basic signal handling, and then loops forever until you send it ``SIGTERM`` or ``SIGKILL`` (hitting Ctrl-C won't work since it ignores ``SIGINT``).

Note that when writing daemons, you can't use ``stdin``, ``stdout``, or
``stderr``. They are set to ``/dev/null``. Any other file
descriptors are closed when you call ``serviced`` (or
``daemonize``). If you need to log data, use the ``syslog``
module. It is initialized for you by ``serviced``, so you can use
it by importing ``syslog`` in your code, then calling

```python
syslog.syslog(syslog.LOG_NOTICE, "message to send")
```

You can also use ``syslog.LOG_ERR`` if you are reporting errors. On
Linux, these messages go to ``/var/log/messages`` or
``/var/log/system.log``. On MacOS X, they go to
``/var/log/system.log``. You can specify options to be passed when
initializing ``syslog`` by passing a mask as argument ``syslogoptions`` when initializing a daemon.

To add signal handling, override the method ``onsignal``. Generally, you should handle the signals you are interested in for a daemon, and pass on all the others, as in

```python
import signal

class NopDaemon(pydaemonize.Daemon):
    ...
    def onsignal(self, sig, stackframe):
        if sig == signal.SIGHUP:
            # handle SIGHUP
        elif sig == signal.SIGTERM:
            # handle SIGTERM
        else:
            pass # Ignore all other signals
```

Note that when you start messing with signals, you will probably have to call ``os._exit`` instead of the usual ``exit`` function to exit your script. ``exit`` dispatches to ``SIGTERM``, but if you have added your own handler, you need to deal with actually exiting yourself. ``os._exit`` is guaranteed to exit no matter what.

You may also want your daemon to start as a superuser in order to
connect to various services, then drop privileges and run thereafter
as a normal user. The ``Daemon`` base class provides a method
``dropprivileges`` to do exactly that. You should pass it a username
and a groupname (either of which may be ``None`` or omitted). If the
user exists, it will try to change to it. Otherwise it tries to change
to a user with the same name as the daemon, and failing that to a user
called ``daemon``. Groups go through the same process. **Warning**:
``pydaemonize`` uses the ``pwd`` and ``grp`` modules to look up users
and groups, and these modules depend on ``/etc/passwd`` and
``/etc/groups``, respectively. If your system's authentication doesn't
go through these files for the users your daemon will use,
``pydaemonize`` will fail.

The ``__init__`` method of Daemon takes several options which may be useful:

  * ``detach``: (default: ``True``) Go through daemonization. For testing and debugging purposes you may want to have the daemon fully attached, in which case initialize the object with ``detach=False``.
  * ``name``: (default: the name of the script) The name of the daemon, used to provide a default user and group to try dropping privileges to, and as the label for messages in syslog.
  * ``pidfilepath``: (default: ``/var/run``) The path to write a PID file to. If there is already a copy of the daemon running, it will refuse to start a new one. You can pass ``pidfilepath=None`` to omit this step entirely.
  * ``syslogoptions``: (default: 0) A binary OR'd list of flags to syslog.

