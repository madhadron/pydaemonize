``pydaemonize`` 0.1
===================

``pydaemonize`` is a library of utilities for writing system daemons in Python. It is a direct port of the Haskell library ``hdaemonize``. Its source code is available from GitHub at http://github.com/madhadron/pydaemonize.


License
-------

``pydaemonize`` is released under GNU General Public License version 3, or any later version. A copy is included in the source distribution as ``LICENSE.txt``.


Installation
------------

``pydaemonize`` is distributed via the Python Package Index (PyPI). To install it, run::

    $ pip install pydaemonize

This will always be up to date with the ``master`` branch on GitHub. You can get the latest development source from the ``dev`` branch.


Quick Start
-----------

Write a function that implements your daemon's behavior. It should not rely on any files being open. Import ``syslog`` and use ``syslog.syslog`` to write messages to the system log rather than trying to write to ``stdout`` or ``stderr``. The simplest possible such function is::

    def nop(_):
        while True:
            pass

``nop`` takes one argument. Don't worry about why for now. To build this into a daemon, add the two lines::

    import pydaemonize
    pydaemonize.serviced(nop)

Say you put ``nop`` and these two lines in ``mydaemon.py``. Here are examples of its use:::

    $ sudo python mydaemon.py
    Usage: mydaemon.py {start|stop|restart}
    $ sudo python mydaemon.py stop
    Could not file PID file to stop. Is the process running?
    $ sudo python mydaemon.py start
    $ sudo python mydaemon.py start
    PID file exists. Process already running?
    $ sudo python mydaemon.py restart
    $ sudo python mydaemon.py stop

``start`` runs the daemon if there is no other copy of the daemon already running. It checks for other copies by looking for a file called ``/var/run/mydaemon.py.pid``. If that file exists, it fails, warning you that the daemon is probably already running. Otherwise it writes its own PID to that file.

``stop`` looks in ``/var/run/mydaemon.py.pid`` to find the PID of the daemon, then uses that to shut it down. The daemon is given 4 seconds to shut down cleanly, and then is forcefully killed (so ``stop`` should never hang for more than 4 seconds for you).

``restart`` executes ``stop`` followed by ``start``.


Writing your own services
-------------------------

``pydaemonize`` provides two functions: ``daemonize`` and ``serviced``. ``daemonize`` does the bare minimum to make a process run as a daemon.  ``serviced`` adds Unix conventions to the daemon to make it more usable. In most cases you will want to use ``serviced``.

.. function:: daemonize(action)

   Run function *action* after doing the bare minimum to become a
   daemon. *action* should take no arguments and should run for as
   long as the daemon should run. It implements the daemon's entire
   behavior.

   The simplest possible *action* is to do nothing forever. The full
   code implementing such a daemon is::

       def nop():
           while True:
               pass

       import pydaemonize
       pydaemonize.daemonize(nop)


.. function:: serviced(action, 
                       privileged_action=lambda: None,
                       name=os.path.basename(sys.argv[0]),
                       user=None,
                       group=None,
                       syslog_options=0,
                       pidfile_directory='/var/run')

   First, don't panic. There are many more arguments to ``serviced``
   than to ``daemonize``, but they all have sane defaults. All that
   must be specified is a function *action*, which takes one argument,
   and implements the behavior of the daemon. The simplest possible
   use of ``serviced``, a daemon which does nothing forever, is just::

       def nop(_):
           while True:
               pass

       import pydaemonize
       pydaemonize.serviced(nop)

   This is different from the example for ``daemonize`` in that
   ``nop`` takes an argument. ``serviced`` is supposed to be run as
   ``root``, then will shed those privileges and become a normal user
   before execution *action*. Yet you will often need to do something
   as ``root`` before dropping privileges, and provide some data or
   connections which are only available as ``root``, such as binding
   ports. To make that possible, pass a function as
   *privileged_action*. It will be run as ``root``, and its return
   value passed to *action* after the daemon drops privileges. For example,::

       def bind_port():
           port = # do stuff to bind a privileged port
           return port

       def http_server(port):
           # do stuff on port as a normal user

       import pydaemonize
       pydaemonize.serviced(http_server,
                            privileged_action=bind_port)

   By default, ``pydaemonize`` tries to change user and group to the
   name of the daemon's executable or script, so if you put your code
   in ``myserver.py``, it would try to change users to ``myserver.py``
   (which probably doesn't exist). If either the user or the group
   doesn't exist, then it tries to change to ``daemon``. You can
   override either or both of the user or group by passing the desired
   names as the arguments *user* and *group*. **Warning**:
   ``pydaemonize`` uses the ``pwd`` and ``grp`` modules to look up
   users and groups, and these modules depend on ``/etc/passwd`` and
   ``/etc/groups``, respectively. If your system's authentication
   doesn't go through these files for the users your daemon will use,
   ``pydaemonize`` will fail.

   You can also change the name of the daemon directly instead of
   letting it default to the executable or script name. Just pass a
   string as the *name* argument. That name will show up in ``syslog``
   messages, and will be used as the user and group to try to drop
   privileges to.

   When writing daemons, you can't use ``stdin``, ``stdout``, or
   ``stderr``. They are set to ``/dev/null``. Any other file
   descriptors are closed when you call ``serviced`` (or
   ``daemonize``). If you need to log data, use the ``syslog``
   module. It is initialized for you by ``serviced``, so you can use
   it by importing ``syslog`` in your code, then calling::

       ``syslog.syslog(syslog.LOG_NOTICE, "message to send")``

   You can also use ``syslog.LOG_ERR`` if you are reporting errors. On
   Linux, these messages go to ``/var/log/messages`` or
   ``/var/log/system.log``. On MacOS X, they go to
   ``/var/log/system.log``. You can specify options to be passed when
   initializing ``syslog`` by passing a mask to ``syslog_options``.

   ``serviced`` checks that only a single copy of the daemon is
   running. It does so in the usual Unix manner of looking for a file
   in a standard location, named the name of the daemon with ``.pid``
   attached (by default the script or executable name, unless the
   *name* argument is specified). So a daemon created with no *name*
   argument and with its code run from ``mydaemon.py`` will look for
   the file ``/var/run/mydaemon.py.pid``. You can also specify another
   directory that it should such for ``mydaemon.py.pid`` by passing
   that directory as the *pidfile_directory* argument.

