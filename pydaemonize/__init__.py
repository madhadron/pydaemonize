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
    *action*. For more sophisticated handling, see the ``serviced``
    function.
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

    # Block SIGHUP. Any additional signal handling should be installed
    # by the user.
    signal.signal(signal.SIGHUP,signal.SIG_IGN)
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

def fatal_error(error):
    syslog.syslog(syslog.LOG_ERR, error)
    exit(1)


def exit_cleanly():
    syslog.syslog(syslog.LOG_NOTICE, "Exiting.")
    exit(0)

def stop_daemon(name, pidfile_directory):
    if not(os.path.exists(pid_file(name, pidfile_directory))):
        print "Could not file PID file to stop. Is the process running?"
        return None
    pid = read_pid_file(name, pidfile_directory)
    if pid != None and pid_is_alive(pid):
        os.kill(pid, signal.SIGTERM)
        time.sleep(1)
        if pid_is_alive(pid):
            time.sleep(3)
            if pid_is_alive(pid):
                os.kill(pid, signal.SIGKILL)
    os.unlink(pid_file(name, pidfile_directory))
    return None

def start_daemon(action,
                 privileged_action,
                 name,
                 uid,
                 gid,
                 syslog_options,
                 pidfile_directory):
    try:
        syslog.openlog(name, syslog_options)
        syslog.syslog(syslog.LOG_NOTICE, 'Starting.')
        privileged_value = privileged_action()
        os.setgid(gid)
        os.setuid(uid)
        write_pid_file(name, pidfile_directory)
        action(privileged_value)
    except Exception, e:
        syslog.syslog(syslog.LOG_ERR, "Error thrown: %s" % str(e))
        syslog.closelog()
        os.unlink(pid_file(name, pidfile_directory))
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

def get_uid(user, name):
    if user == None:
        if user_exists(name):
            user = name
        elif user_exists('daemon'):
            user = 'daemon'
    else:
        if not(user_exists(user)):
            print "Could not switch to nonexistant user %s" % user
            exit(1)
    
    uid = pwd.getpwnam(user).pw_uid
    return uid

def get_gid(group, name):
    if group == None:
        if group_exists(name):
            group = name
        elif group_exists('daemon'):
            group = 'daemon'
    else:
        if not(group_exists(group)):
            print "Could not switch to nonexistant group %s" % group

    gid = grp.getgrnam(group).gr_gid
    return gid
    

def serviced(action,
             privileged_action=lambda: None,
             name=os.path.basename(sys.argv[0]),
             user=None,
             group=None,
             syslog_options=0,
             pidfile_directory='/var/run'):
    """Construct a SysV compatible daemon.


    """
    def go():
        start_daemon(action,
                     privileged_action, 
                     name,
                     get_uid(user, name),
                     get_gid(user, name),
                     syslog_options,
                     pidfile_directory)

    # SysV style start/stop/restart commands
    args = sys.argv[1:]
    if args == ["start"]:
        if os.path.exists(pid_file(name, pidfile_directory)):
            print "PID file exists. Process already running?"
            exit(1)
        daemonize(go)
        exit(0)
    elif args == ["stop"]:
        stop_daemon(name, pidfile_directory)
        exit(0)
    elif args == ["restart"]:
        stop_daemon(name, pidfile_directory)
        daemonize(go)
        exit(0)
    else:
        print "Usage:", name, "{start|stop|restart}"
        exit(0)

