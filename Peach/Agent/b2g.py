# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
import os
import sys
import time
import subprocess

from Peach.Utilities import ADB, network
from Peach.agent import Monitor, MonitorDebug
try:
    from marionette import Marionette
except ImportError:
    sys.exit("Please install Marionette first.")
from Peach.Utilities.Gaia import gaia


class LaunchEmulator(Monitor):
    """
    This monitor will start the B2G emulator and point the FirefoxApp to our publisher.
    We also monitor the main B2G process and other crashes via DEBUG:I in adb logcat.
    """

    def __init__(self, args):
        Monitor.__init__(self, args)

        if args.has_key("URL"):
            self.publisherRequestPath = str(args["URL"]).replace("'''", "")
        else:
            raise Exception("No publisher URL provided.")

        if args.has_key("EmulatorScript"):
            self.emulatorStartScript = str(args["EmulatorScript"]).replace("'''", "")
        else:
            raise Exception("No script provided to run the emulator.")

        if args.has_key("AppName"):
            self.appName = str(args["AppName"]).replace("'''", "")
        else:
            self.appName = "browser"

        if args.has_key("ScriptTimeout"):
            self.scriptTimeout = int(args["ScriptTimeout"]).replace("''", "")
        else:
            self.scriptTimeout = 600000

        if args.has_key("PortADB"):
            self.forwardedPortADB = int(args["PortADB"])
        else:
            self.forwardedPortADB = 2828

        self._name = "MarionetteEmulator"
        self.monitoringProcessId = -1
        self.monitoredProcessName = "/system/b2g/b2g"
        self.publisherHost = "10.0.2.2"
        self.publisherPort = network.runHTTPDThread()
        self.publisherURL = "http://%s:%d/%s" % (self.publisherHost, self.publisherPort, self.publisherRequestPath)
        self.isEmulatorInitialized = False
        self.isMonitorInitialized = False
        self.adb = ADB.AccessDebugBridge(isEmulator=True)
        self.emulatorProcess = None
        self.crashSuccess = False
        self.adbLogcat = self.adb.runCmd(["logcat"])
        self.debugLogData = str()

    def OnTestStarting(self):
        if not self._IsRunning():
            self._StartProcess()

    def _StartProcess(self):
        if not self.isEmulatorInitialized:
            print("Starting Emulator ...")
            self.emulatorProcess = subprocess.Popen(
                [self.emulatorStartScript], cwd=os.path.dirname(self.emulatorStartScript), shell=True)

            # adb shell setprop net.dns1 10.0.2.3

            self._isBootFinished()
            self.monitoringProcessId = self.adb.getPID(self.monitoredProcessName)

            print("Forwarding TCP port %d ..." % self.forwardedPortADB)
            self.adb.command(["forward", "tcp:%d" % self.forwardedPortADB, "tcp:%d" % self.forwardedPortADB])

            self.isEmulatorInitialized = True

        time.sleep(20)

        if self.crashSuccess:
            print("Restarting %s ..." % self.monitoredProcessName)
            self.adb.killProcess(self.monitoredProcessName, True)
            time.sleep(40)
            self.monitoringProcessId = self.adb.getPID(self.monitoredProcessName)
            self.crashSuccess = False
            self.debugLogData = str()
            self.adb.checkCmd(["logcat", "-c"])

        print("Starting Marionette session ...")
        marionette = Marionette('localhost', self.forwardedPortADB)
        print(marionette.status())
        marionette.start_session()
        marionette.set_script_timeout(self.scriptTimeout)
        marionette.switch_to_frame()

        lock = gaia.LockScreen(marionette)
        lock.unlock()

        apps = gaia.GaiaApps(marionette)
        print(apps.runningApps())

        print("Launching Browser application")
        apps.launch(self.appName, switch_to_frame=True)

        print("Navigating to %s ..." % self.publisherURL)
        marionette.execute_script("return window.wrappedJSObject.Browser.navigate('%s')" % self.publisherURL)

        self.isMonitorInitialized = True

    def _isBootFinished(self):
        stdout = self.adbLogcat.stdout.readline()
        while stdout:
            if stdout.find("Get idle time: time since reset") >= 0:
                return 0
            stdout = self.adbLogcat.stdout.readline()
        return -1

    def _getB2GPid(self):
        pid = -1
        while pid == -1:
            pid = self.adb.getPID(self.monitoredProcessName)
        return pid

    def _detectPidChange(self):
        processIds = self.adb.getPID(self.monitoredProcessName)
        return processIds

    def _IsRunning(self):
        if not self.isMonitorInitialized or self.crashSuccess:
            return False
        # We get might get the pid directly but we need to wait till the process
        # is finished with loading for futher actions. See _isBootFinished()
        pid = self._getB2GPid()
        if self.monitoringProcessId != pid:
            MonitorDebug(self._name, "pid of %s changed from %d to %d" %
                                     (self.monitoredProcessName, self.monitoringProcessId, pid))
            return False
        MonitorDebug(self._name, "pid of %s is %d" % (self.monitoredProcessName, pid))

        debugLog = self.adb.runCmd(["logcat", "-d", "-s", "DEBUG:I", "-v", "threadtime"])
        self.debugLogData = debugLog.stdout.read()
        if "Build fingerprint" in self.debugLogData:
            return False
        else:
            debugLog.kill()

        return True

    def OnTestFinished(self):
        if not self._IsRunning():
            self.crashSuccess = True

    def DetectedFault(self):
        if self.crashSuccess:
            return True
        return False

    def GetMonitorData(self):
        if not self.crashSuccess:
            return {}

        id = self.monitoredProcessName.replace("/", "-").strip("-")

        bucket = {
            "Bucket": id,
            "process.txt": "Process %s (%d) aborted." % (id, self.monitoringProcessId),
            "device.txt": self.adb.makeDeviceReport()
        }
        if self.debugLogData:
            bucket["debugLogData.txt"] = self.debugLogData

        return bucket


class LaunchDevice(LaunchEmulator):

    def __init__(self, args):
        Monitor.__init__(self, args)

        if args.has_key("URL"):
            self.publisherRequestPath = str(args["URL"]).replace("'''", "")
        else:
            raise Exception("No publisher URL provided.")

        if args.has_key("AppName"):
            self.appName = str(args["AppName"]).replace("'''", "")
        else:
            self.appName = "browser"

        if args.has_key("ScriptTimeout"):
            self.scriptTimeout = int(args["ScriptTimeout"]).replace("''", "")
        else:
            self.scriptTimeout = 600000

        if args.has_key("PublisherHost"):
            self.publisherHost = str(args["PublisherHost"]).replace("''", "")
        else:
            self.publisherHost = "192.168.178.20"

        if args.has_key("PortADB"):
            self.forwardedPortADB = int(args["PortADB"])
        else:
            self.forwardedPortADB = 2828

        self._name = "MarionetteDevice"
        self.monitoringProcessId = -1
        self.monitoredProcessName = "b2g"
        self.publisherPort = network.runHTTPDThread()
        self.publisherURL = "http://%s:%d/%s" % (self.publisherHost, self.publisherPort, self.publisherRequestPath)
        self.isDeviceInitialized = False
        self.isMonitorInitialized = False
        self.adb = ADB.AccessDebugBridge(isEmulator=False)

        self.crashSuccess = False
        self.adbLogcat = self.adb.runCmd(["logcat"])
        self.debugLogData = str()

    def _StartProcess(self):
        if not self.isDeviceInitialized:
            print("Starting ...")
            self.monitoringProcessId = self.adb.getPID(self.monitoredProcessName)
            print("Forwarding TCP port %d ..." % self.forwardedPortADB)
            self.adb.command(["forward", "tcp:%d" % self.forwardedPortADB, "tcp:%d" % self.forwardedPortADB])
            self.isDeviceInitialized = True

        print("Sleeping ...")
        time.sleep(20)

        if self.crashSuccess:
            print("Restarting %s" % self.monitoredProcessName)
            self.adb.killProcess(self.monitoredProcessName, True)
            time.sleep(40)
            self.monitoringProcessId = self.adb.getPID(self.monitoredProcessName)
            self.crashSuccess = False
            self.debugLogData = str()
            self.adb.checkCmd(["logcat", "-c"])

        print("Starting Marionette session")
        marionette = Marionette('localhost', self.forwardedPortADB)
        print(marionette.status())
        marionette.start_session()
        marionette.set_script_timeout(self.scriptTimeout)
        marionette.switch_to_frame()

        lock = gaia.LockScreen(marionette)
        assert(lock.unlock())

        apps = gaia.GaiaApps(marionette)
        print(apps.runningApps())

        print("Launching Browser application")
        apps.launch(self.appName, switch_to_frame=True)

        print("Navigating to %s ..." % self.publisherURL)
        marionette.execute_script("return window.wrappedJSObject.Browser.navigate('%s')" % self.publisherURL)

        self.isMonitorInitialized = True

    def _isBootFinished(self):
        stdout = self.adbLogcat.stdout.readline()
        while stdout:
            if stdout.find("Get idle time: time since reset") >= 0:
                return 0
            stdout = self.adbLogcat.stdout.readline()
        return -1

    def _getB2GPid(self):
        pid = -1
        while pid == -1:
            pid = self.adb.getPID(self.monitoredProcessName)
        return pid

    def _detectPidChange(self):
        processIds = self.adb.getPID(self.monitoredProcessName)
        return processIds

    def _IsRunning(self):
        if not self.isMonitorInitialized or self.crashSuccess:
            return False
        pid = self._getB2GPid()
        if self.monitoringProcessId != pid:
            MonitorDebug(self._name, "pid of %s changed from %d to %d" %
                                     (self.monitoredProcessName, self.monitoringProcessId, pid))
            return False
        MonitorDebug(self._name, "pid of %s is %d" % (self.monitoredProcessName, pid))

        debugLog = self.adb.runCmd(["logcat", "-d", "-s", "DEBUG:I", "-v", "threadtime"])
        self.debugLogData = debugLog.stdout.read()
        if "Build fingerprint" in self.debugLogData:
            return False
        else:
            debugLog.kill()

        return True

    def GetMonitorData(self):
        if not self.crashSuccess:
            return {}

        id = self.monitoredProcessName.replace("/", "-").strip("-")

        bucket = {
            "Bucket": id,
            "process.txt": "Process %s (%d) aborted." % (id, self.monitoringProcessId),
            "device.txt": self.adb.makeDeviceReport()
        }
        if self.debugLogData:
            bucket["debugLogData.txt"] = self.debugLogData

        return bucket
