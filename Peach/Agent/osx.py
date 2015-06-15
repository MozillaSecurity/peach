# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
import os
import sys
import re
import time
import signal

from Peach.agent import Monitor


class CrashReporter(Monitor):
    """
    Monitor crash reporter for log files.
    """

    def __init__(self, args):
        """
        Arguments are supplied via the Peach XML file.

        :param args: dict of parameters
        :type args: dict
        """
        Monitor.__init__(self, args)
        self._name = "CrashReporter"

        if args.has_key('ProcessName'):
            self.process_name = str(args['ProcessName']).replace("'''", "")
            self.process_name = os.path.basename(self.process_name)
        else:
            self.process_name = None

        if args.has_key('LogFolder'):
            self.log_folder = str(args['LogFolder']).replace("'''", "")
        else:
            self.logFolder = os.path.join(os.environ['HOME'], "Library/Logs/DiagnosticReports")

        if args.has_key('LookoutTime'):
            self.lookout_time = float(args['LookoutTime']).replace("''", "")
        else:
            self.lookout_time = None

        self.data = None
        self.starting_files = None

    def OnTestStarting(self):
        # The monitor folder does not exist on a fresh installed system.
        if not os.path.isdir(self.log_folder):
            os.mkdir(self.log_folder)
        self.starting_files = os.listdir(self.log_folder)

    def GetMonitorData(self):
        if not self.data:
            return None
        return {"CrashReport.txt": self.data}

    def DetectedFault(self):
        try:
            # Give crash reporter time to find the crash. Only explicit from
            # now on, since we have enough time during the re-launch of the
            # process. We do not need to wait 0.50 seconds on each testcase
            # to check for crashes if we monitor a single process.
            if self.lookout_time:
                time.sleep(self.lookout_time)
            self.data = None
            for f in os.listdir(self.log_folder):
                if f not in self.starting_files and \
                        f.endswith(".crash") and \
                        (self.process_name is None or f.find(self.process_name) > -1):
                    fd = open(os.path.join(self.log_folder, f), "r")
                    self.data = fd.read()
                    fd.close()
                    return True
            return False
        except:
            print(sys.exc_info())
        return False


class CrashWrangler(Monitor):
    """
    Use Apple Crash Wrangler to detect and sort crashes.
    """

    def __init__(self, args):
        """
        Arguments are supplied via the Peach XML file.

        :param args: dict of parameters
        :type args: dict
        """
        Monitor.__init__(self, args)

        if args.has_key('EnvironmentCommand'):
            self.EnvCommand = str(args['EnvironmentCommand']).replace("'''", "")
            try:
                self.EnvCommand = os.environ[self.EnvCommand]
            except KeyError:
                self.EnvCommand = None
        else:
            self.EnvCommand = None

        if args.has_key('EnvironmentArguments'):
            self.EnvArguments = str(args['EnvironmentArguments']).replace("'''", "")
            try:
                self.EnvArguments = os.environ[self.EnvArguments]
            except KeyError:
                self.EnvArguments = ""
        else:
            self.EnvArguments = ""

        if not self.EnvCommand:
            if args.has_key('Command'):
                self.Command = str(args['Command']).replace("'''", "")
            else:
                self.Command = None
        else:
            self.Command = self.EnvCommand

        if not self.EnvArguments:
            if args.has_key('Arguments'):
                self.Arguments = str(args['Arguments']).replace("'''", "")
            else:
                self.Arguments = ""
        else:
            self.Arguments = self.EnvArguments

        if args.has_key('StartOnCall'):
            self.StartOnCall = str(args['StartOnCall']).replace("'''", "")
        else:
            self.StartOnCall = None

        if args.has_key('UseDebugMalloc'):
            self.UseDebugMalloc = str(args['UseDebugMalloc']).replace("'''", "").lower() == 'true'
        else:
            self.UseDebugMalloc = False

        if args.has_key('EnvironmentExecHandler'):
            self.EnvExecHandler = str(args['EnvironmentExecHandler']).replace("'''", "")
            try:
                self.EnvExecHandler = os.environ[self.EnvExecHandler]
            except KeyError:
                self.EnvExecHandler = ""
        else:
            self.EnvExecHandler = ""

        if not self.EnvExecHandler:
            if args.has_key('ExecHandler'):
                self.ExecHandler = str(args['ExecHandler']).replace("'''", "")
            else:
                raise PeachException("Error, CrashWrangler monitor requires 'ExecHandler' parameter.")
        else:
            self.ExecHandler = self.EnvExecHandler

        if args.has_key('ExploitableReads') and str(args['ExploitableReads']).replace("'''", "").lower() == "false":
            self.ExploitableReads = False
        else:
            self.ExploitableReads = True

        if args.has_key("NoCpuKill"):
            self.NoCpuKill = True
        else:
            self.NoCpuKill = False

        if args.has_key('CwLogFile'):
            self.CwLogFile = str(args['CwLogFile']).replace("'''", "")
        else:
            self.CwLogFile = "cw.log"

        if args.has_key('CwLockFile'):
            self.CwLockFile = str(args['CwLockFile']).replace("'''", "")
        else:
            self.CwLockFile = "cw.lck"

        if args.has_key('CwPidFile'):
            self.CwPidFile = str(args['CwPidFile']).replace("'''", "")
        else:
            self.CwPidFile = "cw.pid"

        # Our name for this monitor
        self._name = "CrashWrangler"
        self.pid = None
        self.pid2 = None
        self.currentCount = 0
        self.restartFinger = 1000

    def OnTestStarting(self):
        if not self.StartOnCall:
            if not self._IsRunning():
                self._StartProcess()

    def OnTestFinished(self):
        if self.StartOnCall and self._IsRunning():
            self._StopProcess()

    def GetMonitorData(self):
        if os.path.exists(self.CwLogFile):
            fd = open(self.CwLogFile, "rb")
            data = fd.read()
            fd.close()
            bucket = "Unknown"
            if re.match(r".*:is_exploitable=\s*no\s*:.*", data):
                bucket = "NotExploitable"
            elif re.match(r".*:is_exploitable=\s*yes\s*:.*", data):
                bucket = "Exploitable"
            if data.find("exception=EXC_BAD_ACCESS:") > -1:
                bucket += "_BadAccess"
                if data.find(":access_type=read:") > -1:
                    bucket += "_Read"
                elif data.find(":access_type=write:") > -1:
                    bucket += "_Write"
                elif data.find(":access_type=exec:") > -1:
                    bucket += "_Exec"
                elif data.find(":access_type=recursion:") > -1:
                    bucket += "_Recursion"
                elif data.find(":access_type=unknown:") > -1:
                    bucket += "_Unknown"

            elif data.find("exception=EXC_BAD_INSTRUCTION:") > -1:
                bucket += "_BadInstruction"
            elif data.find("exception=EXC_ARITHMETIC:") > -1:
                bucket += "_Arithmetic"
            elif data.find("exception=EXC_CRASH:") > -1:
                bucket += "_Crash"
            # Locate crashing address to help bucket duplicates
            try:
                threadId = re.search(r"Crashed Thread:\s+(\d+)", data).group(1)
                threadPos = data.find("Thread " + threadId + " Crashed:")
                crashAddress = re.search(r"(0x[0-9a-fA-F]+)", data[threadPos:]).group(1)
                bucket += "_" + crashAddress
            except:
                print(sys.exc_info())
            try:
                os.unlink(self.CwLogFile)
                os.unlink(self.CwLockFile)
            except:
                pass
            if self.pid is not None:
                return {"CrashWrangler" + str(self.pid) + ".txt": data, "Bucket": bucket}
            else:
                return {"CrashWrangler.txt": data, "Bucket": bucket}
        return None

    def DetectedFault(self):
        try:
            # Give crash wrangler time to find the crash
            time.sleep(0.25)
            time.sleep(0.25)
            return os.path.exists(self.CwLogFile)
        except:
            print(sys.exc_info())
        return False

    def OnShutdown(self):
        self._StopProcess()

    def PublisherCall(self, method):
        if self.StartOnCall:
            if self.StartOnCall == method:
                self._StartProcess()
            elif self.StartOnCall + "_isrunning" == method:
                if self._IsRunning():
                    if not self.NoCpuKill:
                        cpu = None
                        try:
                            os.system("ps -o pcpu %d > .cpu" % self.pid2)
                            fd = open(".cpu", "rb")
                            data = fd.read()
                            fd.close()
                            os.unlink(".cpu")
                            cpu = re.search(r"\s*(\d+\.\d+)", data).group(1)
                            if cpu.startswith("0.") and not os.path.exists("cw.lck"):
                                time.sleep(1.5)
                                # Check and see if crashwrangler is going
                                if os.path.exists(self.CwLockFile):
                                    return True
                                print("CrashWrangler: PCPU is low (%s), stopping process" % cpu)
                                self._StopProcess()
                                return False
                        except:
                            print(sys.exc_info())
                    return True
                else:
                    return False
        return None

    def unlink(self, file):
        try:
            os.unlink(file)
        except:
            pass

    def _StartProcess(self):
        if self._IsRunning():
            return
        self.currentCount += 1
        # OS X can get very unstable during testing. This will hopefully
        # allow for longer fuzzing runs by killing off some processes
        # that seem to get "stuck".
        if self.currentCount % self.restartFinger == 0:
            os.system('killall -KILL Finder')
            os.system('killall -KILL Dock')
            os.system('killall -KILL SystemUIServer')
        # Clean up any files
        self.unlink(self.CwLockFile)
        self.unlink(self.CwLogFile)
        self.unlink(self.CwPidFile)
        # If no command is specified, assume we are running exc_handler some
        # other way.
        if self.Command is None:
            return
        args = ["/usr/bin/env",
                "CW_LOG_PATH=" + self.CwLogFile,
                "CW_PID_FILE=" + self.CwPidFile,
                "CW_LOCK_FILE=" + self.CwLockFile]
        if self.UseDebugMalloc:
            args.append("CW_USE_GMAL=1")
        if self.ExploitableReads:
            args.append("CW_EXPLOITABLE_READS=1")
        args.append(self.ExecHandler)
        args.append(self.Command)
        splitArgs = self.Arguments.split(" ")
        for i in range(len(splitArgs)):
            if i > 0 and splitArgs[i - 1][-1] == '\\':
                args[-1] = args[-1][:-1] + " " + splitArgs[i]
            else:
                args.append(splitArgs[i])
        print("CrashWrangler._StartProcess():" % args)
        self.pid = os.spawnv(os.P_NOWAIT, "/usr/bin/env", args)
        while not os.path.exists(self.CwPidFile):
            time.sleep(0.15)
        fd = open(self.CwPidFile, "rb")
        self.pid2 = int(fd.read())
        fd.close()
        self.unlink(self.CwPidFile)
        print("_StartProcess(): Pid2: %d" % self.pid2)


    def _StopProcess(self):
        if self.pid is not None:
            try:
                # Verify if process is still running
                (pid1, ret) = os.waitpid(self.pid, os.WNOHANG)
                if not (pid1 == 0 and ret == 0):
                    self.pid = None
                    return
                # Check for cw.lck before killing
                while os.path.exists("cw.lck"):
                    time.sleep(0.25)
                    (pid1, ret) = os.waitpid(self.pid, os.WNOHANG)
                    if not (pid1 == 0 and ret == 0):
                        self.pid = None
                        return
            except:
                return
            try:
                # Kill process with signal
                os.kill(self.pid2, signal.SIGTERM)
                time.sleep(0.25)
                os.kill(self.pid2, signal.SIGKILL)
            except:
                pass
            try:
                # Kill process with signal
                os.kill(self.pid, signal.SIGTERM)
                time.sleep(0.25)
                os.kill(self.pid, signal.SIGKILL)
            except:
                pass
            # Prevent Zombies!
            os.wait()
            self.pid = None


    def _IsRunning(self):
        if self.pid:
            try:
                (pid1, ret) = os.waitpid(self.pid, os.WNOHANG)
                if pid1 == 0 and ret == 0:
                    print("_IsRunning: True")
                    return True
            except:
                pass
        print("_IsRunning: False")
        return False


class Process(Monitor):
    """
    Start a process and kill it based on CPU usage.
    """

    def __init__(self, args):
        """
        Arguments are supplied via the Peach XML file.

        :param args: dict of parameters
        :type args: dict
        """
        Monitor.__init__(self, args)

        if args.has_key('Command'):
            self.Command = str(args['Command']).replace("'''", "")
        else:
            self.Command = None

        if args.has_key('Arguments'):
            self.Arguments = str(args['Arguments']).replace("'''", "")
        else:
            self.Arguments = ""

        if args.has_key('StartOnCall'):
            self.StartOnCall = str(args['StartOnCall']).replace("'''", "")
        else:
            self.StartOnCall = None

        if args.has_key("NoCpuKill"):
            self.NoCpuKill = True
        else:
            self.NoCpuKill = False

        self._name = "OsxProcess"
        self.pid = None
        self.currentCount = 0
        self.restartFinger = 1000

    def OnTestStarting(self):
        if not self.StartOnCall:
            if not self._IsRunning():
                self._StartProcess()

    def OnTestFinished(self):
        if self.StartOnCall and self._IsRunning():
            self._StopProcess()

    def OnShutdown(self):
        self._StopProcess()

    def PublisherCall(self, method):
        if self.StartOnCall:
            if self.StartOnCall == method:
                self._StartProcess()
            elif self.StartOnCall + "_isrunning" == method:
                if self._IsRunning():
                    if not self.NoCpuKill:
                        cpu = None
                        try:
                            os.system("ps -o pcpu %d > .cpu" % self.pid)
                            fd = open(".cpu", "rb")
                            data = fd.read()
                            fd.close()
                            self.unlink(".cpu")
                            cpu = re.search(r"\s*(\d+\.\d+)", data).group(1)
                            if cpu.startswith("0."):
                                time.sleep(1)
                                print("osx.Process: PCPU is low (%s), stopping process" % cpu)
                                self._StopProcess()
                                return False
                        except:
                            print(sys.exc_info())
                    return True
                else:
                    return False
        return None

    def unlink(self, file):
        try:
            os.unlink(file)
        except:
            pass

    def _StartProcess(self):
        if self._isRunning():
            return
        self.currentCount += 1
        # OS X can get very unstable during testing.  This will hopefully
        # allow for longer fuzzing runs by killing off some processes
        # that seem to get "stuck"
        if self.currentCount % self.restartFinger == 0:
            os.system('killall -KILL Finder')
            os.system('killall -KILL Dock')
            os.system('killall -KILL SystemUIServer')
        # If no command is specified, assume we are running
        # exc_handler some other way.
        if self.Command is None:
            return
        args = [self.Command]
        splitArgs = self.Arguments.split(" ")
        for i in range(len(splitArgs)):
            if i > 0 and splitArgs[i - 1][-1] == '\\':
                args[-1] = args[-1][:-1] + " " + splitArgs[i]
            else:
                args.append(splitArgs[i])
        print("osx.Process._StartProcess(): %s" % args)
        self.pid = os.spawnv(os.P_NOWAIT, self.Command, args)
        time.sleep(1.5)
        print("osx.Process: pid: %d" % self.pid)

    def _StopProcess(self):
        if self.pid is not None:
            try:
                # Verify if process is still running
                (pid1, ret) = os.waitpid(self.pid, os.WNOHANG)
                if not (pid1 == 0 and ret == 0):
                    self.pid = None
                    return
            except:
                return
            try:
                # Kill process with signal
                os.kill(self.pid, signal.SIGTERM)
                time.sleep(0.25)
                os.kill(self.pid, signal.SIGKILL)
            except:
                pass
            # Prevent Zombies!
            os.wait()
            self.pid = None

    def _IsRunning(self):
        if self.pid is not None:
            try:
                (pid1, ret) = os.waitpid(self.pid, os.WNOHANG)
                if pid1 == 0 and ret == 0:
                    print("osx.Process._IsRunning: True")
                    return True
            except:
                pass
        print("osx.Process._IsRunning: False")
        return False
