# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
import subprocess
import time
import os
import re


class AccessDebugBridge(object):
    def __init__(self, adbPath="adb", deviceSerial=None, isEmulator=False):
        self.adbPath = adbPath
        self.deviceSerial = deviceSerial
        self.isEmulator = isEmulator

    def verifyADB(self):
        if self.adbPath != 'adb':
            if not os.access(self.adbPath, os.X_OK):
                raise Exception("invalid ADB path, or ADB not executable: %s", self.adbPath)
        try:
            self.checkCmd(["version"])
        except os.error as err:
            raise Exception(
                "unable to execute ADB (%s): ensure Android SDK is installed and ADB is in your $PATH" % err)
        except subprocess.CalledProcessError:
            raise Exception("unable to execute ADB: ensure Android SDK is installed and ADB is in your $PATH")

    def verifyDevice(self):
        if self.deviceSerial:
            deviceStatus = None
            proc = subprocess.Popen([self.adbPath, "devices"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            for line in proc.stdout:
                m = re.match('(.+)?\s+(.+)$', line)
                if m:
                    if self.deviceSerial == m.group(1):
                        deviceStatus = m.group(2)
            if deviceStatus is None:
                raise Exception("device not found: %s" % self.deviceSerial)
            elif deviceStatus != "device":
                raise Exception("bad status for device %s: %s" % (self.deviceSerial, deviceStatus))
        try:
            self.checkCmd(["shell", "echo"])
        except subprocess.CalledProcessError:
            raise Exception("unable to connect to device: is it plugged in?")

    def runCmd(self, args):
        finalArgs = [self.adbPath]
        if self.deviceSerial:
            finalArgs.extend(['-s', self.deviceSerial])
        finalArgs.extend(args)
        return subprocess.Popen(finalArgs, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

    def checkCmd(self, args, timeout=None):
        finalArgs = [self.adbPath]
        if self.deviceSerial:
            finalArgs.extend(['-s', self.deviceSerial])
        finalArgs.extend(args)
        if timeout:
            timeout = int(timeout)
            proc = subprocess.Popen(finalArgs)
            start_time = time.time()
            ret_code = proc.poll()
            while ((time.time() - start_time) <= timeout) and ret_code is None:
                time.sleep(1)
                ret_code = proc.poll()
            if ret_code is None:
                proc.kill()
                raise Exception("Timeout exceeded for checkCmd call")
            return ret_code
        return subprocess.check_call(finalArgs)

    def getProcessList(self):
        p = self.runCmd(["shell", "ps"])
        p.stdout.readline()
        proc = p.stdout.readline()
        ret = []
        while proc:
            els = proc.split()
            ret.append(list([els[1], els[len(els) - 1], els[0]]))
            proc = p.stdout.readline()
        return ret

    def killProcess(self, appname, forceKill=False):
        procs = self.getProcessList()
        didKillProcess = False
        for (pid, name, user) in procs:
            if name == appname:
                args = ["shell", "kill"]
                if forceKill:
                    args.append("-9")
                args.append(pid)
                p = self.runCmd(args)
                p.communicate()
                if p.returncode == 0:
                    didKillProcess = True
        return didKillProcess

    def reboot(self, wait=False):
        ret = self.runCmd(["reboot"]).stdout.read()
        if not wait:
            return ret
        return self.checkCmd(["wait-for-device"])

    def getCurrentTime(self):
        timestr = self.runCmd(["shell", "date", "+%s"]).stdout.read().strip()
        if not timestr or not timestr.isdigit():
            return None
        return str(int(timestr) * 1000)

    def getDeviceInformation(self, directive="all"):
        ret = {}
        if directive == "id" or directive == "all":
            ret["id"] = self.runCmd(["get-serialno"]).stdout.read()
        if directive == "os" or directive == "all":
            ret["os"] = self.runCmd(["shell", "getprop", "ro.build.display.id"]).stdout.read()
        if directive == "uptime" or directive == "all":
            utime = self.runCmd(["shell", "uptime"]).stdout.read()
            if utime:
                utime = utime[9:]
                hours = utime[0:utime.find(":")]
                utime = utime[utime[1:].find(":") + 2:]
                minutes = utime[0:utime.find(":")]
                utime = utime[utime[1:].find(":") + 2:]
                seconds = utime[0:utime.find(",")]
                ret["uptime"] = ["0 days " + hours + " hours " + minutes + " minutes " + seconds + " seconds"]
        if directive == "process" or directive == "all":
            ret["process"] = self.runCmd(["shell", "ps"]).stdout.read()
        if directive == "systime" or directive == "all":
            ret["systime"] = self.runCmd(["shell", "date"]).stdout.read()
        if directive == "version" or directive == "all":
            ret["version"] = self.runCmd(["shell", "cat", "/proc/version"]).stdout.read()
        if directive == "cpuinfo" or directive == "all":
            ret["cpuinfo"] = self.runCmd(["shell", "cat", "/proc/cpuinfo"]).stdout.read()
        if directive == "meminfo" or directive == "all":
            ret["meminfo"] = self.runCmd(["shell", "cat", "/proc/meminfo"]).stdout.read()
        if directive == "procrank" or directive == "all" and not self.isEmulator:
            ret["procrank"] = self.runCmd(["shell", "procrank"]).stdout.read()
        if directive == "pstree" or directive == "all" and not self.isEmulator:
            ret["pstree"] = self.runCmd(["shell", "pstree"]).stdout.read()
        if directive == "bugreport" or directive == "all":
            ret["bugreport"] = self.runCmd(["shell", "bugreport"]).stdout.read()
        return ret

    def makeDeviceReport(self):
        dev = self.getDeviceInformation()
        hr = '\n# ' + '-' * 80 + '\n\n'
        txt = ""
        if dev.has_key('version'):
            txt += dev.get('version')
            txt += hr
        if dev.has_key('cpuinfo'):
            txt += dev.get('cpuinfo')
            txt += hr
        if dev.has_key('meminfo'):
            txt += dev.get('meminfo')
            txt += hr
        if dev.has_key('procrank'):
            txt += dev.get('procrank')
        return txt

    def makeBugReport(self):
        return self.getDeviceInformation("bugreport")

    def getPID(self, procName):
        if self.isEmulator:
            try:
                return int(filter(lambda x: x[1] == procName, self.getProcessList())[0][0])
            except IndexError:
                return -1
        else:
            return int(self.runCmd(['shell', 'pidof', procName]).stdout.read())

    def getPIDs(self, procName):
        try:
            processes = filter(lambda x: x[1] == procName, self.getProcessList())
            return [int(proc[0]) for proc in processes]
        except IndexError:
            return -1

    def shell(self, command):
        commandList = ["shell"]
        for eachCommand in command:
            commandList.append(eachCommand)
        return self.command(commandList)

    def command(self, command):
        commandList = ["adb"]
        for eachCommand in command:
            commandList.append(eachCommand)
        return subprocess.check_output(commandList).strip("\r\n")
