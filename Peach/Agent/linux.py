# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
import sys
import time
import os

from Peach.agent import Monitor


class LinuxApport(Monitor):

    def __init__(self, args):
        if 'Executable' in args:
            self.programPath = str(args['ProgramPath']).replace("'''", "")
            self.processName = os.path.basename(self.programPath)
        else:
            self.processName = None

        if 'LogFolder' in args:
            self.logFolder = str(args['LogFolder']).replace("'''", "")
        else:
            self.logFolder = "/var/crash/"

        if 'Apport' in args:
            self.Apport = self.logFolder = str(args['Apport']).replace("'''", "")
        else:
            self.Apport = "/usr/share/apport/apport"

        self._name = "LinuxApport"

        self.data = None
        self.startingFiles = None

    def OnTestStarting(self):
        self.startingFiles = os.listdir(self.logFolder)

    def GetMonitorData(self):
        if not self.data:
            return None
        return {"LinuxApport.txt": self.data}

    def DetectedFault(self):
        try:
            time.sleep(0.25)
            time.sleep(0.25)
            self.data = None
            for f in os.listdir(self.logFolder):
                if f not in self.startingFiles and f.endswith(".crash") and \
                   (self.processName is None or f.find(self.processName) > -1):
                    fd = open(os.path.join(self.logFolder, f), "rb")
                    self.data = fd.read()
                    fd.close()
                    os.unlink(os.path.join(self.logFolder, f))
                    return True
            return False
        except:
            print(sys.exc_info())
        return False

    def StopRun(self):
        return False
