"""pydaemonize - Utilities for writing system daemons in Python."""

# Copyright 2011 Frederick J. Ross.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os
import sys
import pwd
import grp
import time
import syslog
import signal
import resource


def continue_as_forked_child():
    if os.fork() != 0:
        exit(0)


def close_all_fds():
    """Close all open file descriptors on the current process.

    This is an important step in creating daemons, since it means the
    daemon won't lock any files.
    """
    rlimit = resource.getrlimit(resource.RLIMIT_NOFILE)[1]
    if rlimit == resource.RLIM_INFINITY:
        max_fd = 1024
    else:
        max_fd = rlimit
    for fd in xrange(max_fd):
        try:
            os.close(fd)
        except OSError:
            pass


class Daemon(object):
    """Base class for daemons.

    Your class should override any signal handlers you need, named
    onSIGNAME (e.g., onSIGTERM, onSIGHUP). Signal handlers take two
    arguments: the signal received and the stackframe. You should also
    override the action method. If the daemon needs to drop
    privileges, call self.dropprivileges.
    """
    def __init__(self, detach=True, name=None, syslogoptions=0,
                 pidfilepath='/var/run'):
        self.name = name or os.path.basename(sys.argv[0])
        syslog.openlog(self.name, syslogoptions)
        signal.signal(signal.SIGTERM, lambda signal, stackframe: self.onsignal(signal, stackframe))
        signal.signal(signal.SIGINT, lambda signal, stackframe: self.onsignal(signal, stackframe))
        signal.signal(signal.SIGPIPE, lambda signal, stackframe: self.onsignal(signal, stackframe))
        signal.signal(signal.SIGHUP, lambda signal, stackframe: self.onsignal(signal, stackframe))
        signal.signal(signal.SIGALRM, lambda signal, stackframe: self.onsignal(signal, stackframe))
        signal.signal(signal.SIGUSR1, lambda signal, stackframe: self.onsignal(signal, stackframe))
        signal.signal(signal.SIGUSR2, lambda signal, stackframe: self.onsignal(signal, stackframe))
        signal.signal(signal.SIGCHLD, lambda signal, stackframe: self.onsignal(signal, stackframe))
        if pidfilepath and os.path.exists(pid_file(self.name, pidfilepath)):
            print "PID file exists. Process already running?"
            os._exit(1)
        if pidfilepath:
            oldpid = read_pid_file(self.name, pidfilepath)
            if oldpid:
                if oldpid and pid_is_alive(oldpid):
                    raise OSError("Daemon already running at PID %d" % oldpid)
            write_pid_file(self.name, pidfilepath)
        if detach:
            daemonize(lambda: self.action())
        else:
            self.action()
    def dropprivileges(self, newuser=None, newgroup=None):
        """Drop root privileges and become a normal user.

        *newuser* and *newgroup* are strings specifying the user and
        group to switch to. If the specified user does not exist,
        ``dropprivilieges`` tries to change to a user of the same name
        as the daemon, or, failing that, to a user named ``daemon``.
        Groups go through the same process of elimination.
        """
        uid = get_uid(newuser) or get_uid(self.name) or get_uid('daemon')
        gid = get_gid(newgroup) or get_gid(self.name) or get_gid('daemon')
        os.setgid(gid)
        os.setuid(uid)
    def onsignal(self, sig, stackframe):
        """Generic signal handler. Override in your subclasses.

        You can match the value in *sig* against
        ``signal.SIGTERM``, etc. to dispatch for individual signals.
        """
        if sig == signal.SIGTERM:
            syslog.syslog(syslog.LOG_INFO, 'Received SIGTERM. Exiting.')
            os._exit(1)
        else:
            pass
    def action(self):
        """Behavior of daemon after detaching. Should be overridden.

        If you need to drop privileges, call::

            self.dropprivileges(username, groupname)

        in the body of your overriding version of this method.
        Remember that this function may be interrupted by signal
        handlers at any point with no warning, so if you want to do
        something here on SIGTERM, you will need to set up a signaling
        mechanism within the object, such as will a
        ``threading.Event`` object.
        """
        pass


def daemonize(action):
    """Run the function *action* as a daemon.

    Turning a process into a daemon involves a fixed set of operations
    on unix systems, described in section 13.3 of Stevens and Rago,
    "Advanced Programming in the Unix Environment."  Since they are
    fixed, they can be written as a single function, ``daemonize``,
    which takes a function representing the daemon's actual behavior.

    Briefly, ``daemonize`` sets the file creation mask to 0, forks
    twice, changed the working directory to ``/``, closes all open
    file descriptors, sets stdin, stdout, and stderr to ``/dev/null``,
    blocks 'sigHUP', and runs *action*.

    The most trivial daemon would be::
 
        def infinite_loop():
            while True:
                pass

        if __name__ == '__main__':
            daemonize(infinite_loop)
 
    which does nothing until killed.

    ``daemonize`` makes no attempt to do clever error handling,
    restarting, or signal handling. All that is to be handled by
    *action*.
    """
    os.umask(0) # Set the file creation mask
    continue_as_forked_child()
    os.setsid() # Start a new session so we aren't attached to the terminal
    continue_as_forked_child()
    os.chdir("/") # Don't block any filesystems
    close_all_fds()
    # Open /dev/null as stdin, stdout, and stderr
    os.open(os.devnull,os.O_RDWR) # Opens fd 0 since all others are closed
    os.dup2(0, 1) # stdout is fd 1
    os.dup2(0, 2) # stderr is fd 2
    action()


def pid_file(daemon_name, pidfile_directory):
    if pidfile_directory == None:
        pidfile_directory = "/var/run"
    return os.path.join(pidfile_directory, daemon_name + ".pid")

def read_pid_file(daemon_name, pidfile_directory):
    f = pid_file(daemon_name, pidfile_directory)
    if os.path.exists(f):
        with open(f, 'r') as h:
            return int(h.read())
    else:
        return None

def write_pid_file(daemon_name, pidfile_directory):
    with open(pid_file(daemon_name, pidfile_directory), 'w') as h:
        h.write(str(os.getpid()))

def pid_is_alive(pid):
    try:
        os.kill(pid, 0)
        return True
    except OSError, o:
        if o.errno == 3:
            return False
        else:
            raise

def user_exists(user):
    try:
        pwd.getpwnam(user)
        return True
    except KeyError:
        return False

def group_exists(user):
    try:
        grp.getgrnam(user)
        return True
    except KeyError:
        return False

def username_to_uid(username):
    uid = pwd.getpwnam(user).pw_uid
    return uid    

def get_uid(user):
    if user == None:
        return None
    elif user_exists(user):
        return username_to_uid(user)
    else:
        return None

def group_to_gid(group):
    gid = grp.getgrnam(group).gr_gid
    return gid


def get_gid(group):
    if group == None:
        return None
    elif group_exists(group):
        return group_to_gid(group)
    else:
        return None
    


