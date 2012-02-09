"""
pydaemonize/inotify.py - Generic inotify daemon.
"""

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
import syslog
import pyinotify
from __init__ import serviced

for flag, val in pyinotify.EventsCodes.ALL_FLAGS.iteritems():
    globals()[flag] = val

def daemon(paths, callback, init=lambda: None, mask=pyinotify.ALL_EVENTS,
           name=os.path.basename(sys.argv[0]), user=None, group=None, syslog_options=0, 
           pidfile_directory='/var/run', exitevent=None):
    if isinstance(paths, basestring):
        paths = [paths]
    else:
        paths = paths

    def daemon_behavior(state):
        class Handler(pyinotify.ProcessEvent):
            def process_IN_UNMOUNT(self, event):
                syslog.syslog(syslog.LOG_NOTICE, "Backing filesystem of %s was unmounted. Exiting." % event.path)
                exit(0)
            def process_default(self, event):
                callback(state, event)

        wm = pyinotify.WatchManager()
        notifier = pyinotify.Notifier(wm, Handler())
        for p in paths:
            wm.add_watch(p, mask, rec=True)

        while exitevent==None or not(exitevent.is_set()):
            notifier.process_events()
            while notifier.check_events():
                notifier.read_events()
                notifier.process_events()
            time.sleep(0.01)

    serviced(daemon_behavior,
             privileged_action=init,
             name=name,
             user=user,
             group=group,
             syslog_options=syslog_options,
             pidfile_directory=pidfile_directory)
             

