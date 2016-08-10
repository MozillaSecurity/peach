# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
import os
import re
import sys
import time
import json
import shlex
import signal
import threading
try:
    import Queue
except ImportError:
    import queue
from subprocess import Popen, STDOUT, PIPE, check_output

try:
    # Todo: Test monitors on Windows and check Python 3 compatibility with PyWin32
    import win32con
    import win32api
    import win32serviceutil
    # Todo: Find out which methods are used from this import and do it the right way.
    from win32process import *
except:
    if sys.platform == 'win32':
        print("Warning: PyWin32 extensions not found, disabling various process monitors.")

from Peach.agent import Monitor, MonitorDebug
from Peach.Engine.common import PeachException
from Peach.Utilities.common import *


class PageHeap(Monitor):
    """
    A monitor that will enable/disable pageheap on an executable.
    """

    def __init__(self, args):
        try:
            self._path = os.path.join(args['Path'].replace("'''", ""), "gflags.exe")
        except:
            self._path = os.path.join(self.LocateWinDbg(), 'gflags.exe')
        self._exe = os.path.basename(args['Executable'].replace("'''", ""))
        self._onParams = ['gflags.exe', '/p', '/full', '/enable', self._exe]
        self._offParams = ['gflags.exe', '/p', '/disable', self._exe]
        try:
            os.spawnv(os.P_WAIT, self._path, self._onParams)
        except:
            print("Error, PageHeap failed to launch:")
            print("\tself._path:", self._path)
            print("\tself._onParams", self._onParams)
            raise

    def LocateWinDbg(self):
        # NOTE: Update master copy in debugger.py if you change this.
        try:
            hkey = win32api.RegOpenKey(win32con.HKEY_CURRENT_USER, "Software\\Microsoft\\DebuggingTools")
            val, _ = win32api.RegQueryValueEx(hkey, "WinDbg")
            return val
        except:
            # Lets try a few common places before failing.
            pgPaths = [
                "c:\\",
                os.environ["SystemDrive"] + "\\",
                os.environ["ProgramFiles"],
            ]
            if "ProgramW6432" in os.environ:
                pgPaths.append(os.environ["ProgramW6432"])
            if "ProgramFiles(x86)" in os.environ:
                pgPaths.append(os.environ["ProgramFiles(x86)"])

            dbgPaths = [
                "Debuggers",
                "Debugger",
                "Debugging Tools for Windows",
                "Debugging Tools for Windows (x64)",
                "Debugging Tools for Windows (x86)",
            ]
            for p in pgPaths:
                for d in dbgPaths:
                    testPath = os.path.join(p, d)
                    if os.path.exists(testPath):
                        return testPath
        print("Unable to locate gflags.exe!")

    def OnShutdown(self):
        os.spawnv(os.P_WAIT, self._path, self._offParams)


class WindowsProcess(Monitor):
    """
    Process control agent. This agent is able to start, stop, and monitor if a process is running.
    If the process exits early a fault will be issued to the fuzzer.
    """

    def __init__(self, args):
        self.restartOnTest = False
        if args.has_key('RestartOnEachTest'):
            if args['RestartOnEachTest'].replace("'''", "").lower() == 'true':
                self.restartOnTest = True
        self.faultOnEarlyExit = True
        if args.has_key('FaultOnEarlyExit'):
            if args['FaultOnEarlyExit'].replace("'''", "").lower() != 'true':
                self.faultOnEarlyExit = False
        self.startOnCall = False
        if args.has_key('StartOnCall'):
            self.startOnCall = True
            self.startOnCallMethod = args['StartOnCall'].replace("'''", "").lower()
        self.waitForExitOnCall = False
        if args.has_key('WaitForExitOnCall'):
            self.waitForExitOnCall = True
            self.waitForExitOnCallMethod = args['WaitForExitOnCall'].replace("'''", "").lower()
        if not args.has_key('Command'):
            raise PeachException("Error, monitor Process requires a parameter named 'Command'")
        self.strangeExit = False
        self.command = args["Command"].replace("'''", "")
        self.args = None
        self.pid = None
        self.hProcess = None
        self.hThread = None
        self.dwProcessId = None
        self.dwThreadId = None

    def PublisherCall(self, method):
        method = method.lower()
        if self.startOnCall and self.startOnCallMethod == method:
            print("Process: startOnCall, starting process!")
            self._StopProcess()
            self._StartProcess()
        elif self.waitForExitOnCall and self.waitForExitOnCallMethod == method:
            print("Process: waitForExitOnCall, waiting on process exit")
            while True:
                if not self._IsProcessRunning:
                    print("Process: Process exitted")
                    return
                time.sleep(0.25)

    def _StopProcess(self):
        if self.hProcess is None:
            return
        if self._IsProcessRunning():
            TerminateProcess(self.hProcess, 0)
        self.hProcess = None
        self.hThread = None
        self.dwProcessId = None
        self.dwThreadId = None

    def _StartProcess(self):
        if self.hProcess is not None:
            self._StopProcess()
        hProcess, hThread, dwProcessId, dwThreadId = CreateProcess(None, self.command, None, None,
                                                                   0, 0, None, None, STARTUPINFO())
        self.hProcess = hProcess
        self.hThread = hThread
        self.dwProcessId = dwProcessId
        self.dwThreadId = dwThreadId

    def _IsProcessRunning(self):
        if self.hProcess is None:
            return False
        ret = GetExitCodeProcess(self.hProcess)
        if ret != win32con.STILL_ACTIVE:
            return False
        ret = GetExitCodeThread(self.hThread)
        if ret != win32con.STILL_ACTIVE:
            return False
        return True

    def OnTestStarting(self):
        self.strangeExit = False
        if not self.startOnCall and (self.restartOnTest or not self._IsProcessRunning()):
            self._StopProcess()
            self._StartProcess()
        elif self.startOnCall:
            self._StopProcess()

    def OnTestFinished(self):
        if not self._IsProcessRunning():
            self.strangeExit = True
        if self.restartOnTest:
            self._StopProcess()
        elif self.startOnCall:
            self._StopProcess()

    def GetMonitorData(self):
        if self.strangeExit:
            return {"WindowsProcess.txt": "Process exited early"}
        return None

    def DetectedFault(self):
        if self.faultOnEarlyExit:
            return not self._IsProcessRunning()
        else:
            return False

    def OnFault(self):
        self._StopProcess()

    def OnShutdown(self):
        self._StopProcess()


class Process(Monitor):
    """
    Process control agent. This agent is able to start, stop, and monitor if a process is running.
    If the process exits early a fault will be issued to the fuzzer.
    """

    def __init__(self, args):
        self.restartOnTest = False
        if args.has_key('RestartOnEachTest'):
            if args['RestartOnEachTest'].replace("'''", "").lower() == 'true':
                self.restartOnTest = True
        self.faultOnEarlyExit = True
        if args.has_key('FaultOnEarlyExit'):
            if args['FaultOnEarlyExit'].replace("'''", "").lower() != 'true':
                self.faultOnEarlyExit = False
        self.startOnCall = False
        if args.has_key('StartOnCall'):
            self.startOnCall = True
            self.startOnCallMethod = args['StartOnCall'].replace("'''", "").lower()
        self.waitForExitOnCall = False
        if args.has_key('WaitForExitOnCall'):
            self.waitForExitOnCall = True
            self.waitForExitOnCallMethod = args['WaitForExitOnCall'].replace("'''", "").lower()
        if not args.has_key('Command'):
            raise PeachException("Error, monitor Process requires a parameter named 'Command'")
        self.strangeExit = False
        self.command = args["Command"].replace("'''", "")
        self.args = self.command.split()
        self.pid = None
        self.process = None

    def PublisherCall(self, method):
        method = method.lower()
        if self.startOnCall and self.startOnCallMethod == method:
            print("Process: startOnCall, starting process!")
            self._StopProcess()
            self._StartProcess()
        elif self.waitForExitOnCall and self.waitForExitOnCallMethod == method:
            print("Process: waitForExitOnCall, waiting on process exit")
            while True:
                if not self._IsProcessRunning():
                    print("Process: Process exitted")
                    return
                time.sleep(0.25)

    def _StopProcess(self):
        print("Process._StopProcess")
        if not self.process:
            return
        if self._IsProcessRunning():
            try:
                os.kill(self.process.pid, signal.SIGTERM)
                os.kill(self.process.pid, signal.SIGKILL)
            except:
                pass
            self.process.wait()
        self.process = None

    def _StartProcess(self):
        print("Process._StartProcess")
        if self.process:
            self._StopProcess()
        self.process = Popen(self.args)

    def _IsProcessRunning(self):
        if self.process is None:
            print("Process._IsProcessRunning: False (self.process == None)")
            return False
        if self.process.poll() is not None:
            print("Process._IsProcessRunning: False (self.process.poll != None)")
            return False
        print("Process._IsProcessRunning: True")
        return True

    def OnTestStarting(self):
        self.strangeExit = False
        if not self.startOnCall and (self.restartOnTest or not self._IsProcessRunning()):
            print("Process.OnTestStarting: Stopping and starting process")
            self._StopProcess()
            self._StartProcess()
        elif self.startOnCall:
            print("Process.OnTestStarting: Stopping process")
            self._StopProcess()
        print("Exiting OnTestStarting...")

    def OnTestFinished(self):
        if not self._IsProcessRunning():
            self.strangeExit = True
        if self.restartOnTest:
            print("Process.OnTestFinished: Stopping process")
            self._StopProcess()
        elif self.startOnCall:
            print("Process.OnTestFinished: Stopping process")
            self._StopProcess()

    def GetMonitorData(self):
        if self.strangeExit:
            return {"Process.txt": "Process exited early"}
        return None

    def DetectedFault(self):
        if self.faultOnEarlyExit:
            return self.strangeExit
        else:
            return False

    def OnFault(self):
        self._StopProcess()

    def OnShutdown(self):
        self._StopProcess()


class WindowsService(Monitor):
    """
    Controls a windows service making sure it's started, optionally restarting, etc.
    """

    def __init__(self, args):
        if args.has_key('RestartOnEachTest'):
            if args['RestartOnEachTest'].lower() == 'true':
                self.restartOnTest = True
            else:
                self.restartOnTest = False
        else:
            self.restartOnTest = False
        if args.has_key('FaultOnEarlyExit'):
            if args['FaultOnEarlyExit'].lower() == 'true':
                self.faultOnEarlyExit = True
            else:
                self.faultOnEarlyExit = False
        else:
            self.faultOnEarlyExit = True
        self.strangeExit = False
        self.service = args["Service"].replace("'''", "")
        if args.has_key("Machine"):
            self.machine = args["Machine"].replace("'''", "")
        else:
            self.machine = None

    def _StopProcess(self):
        win32serviceutil.StopService(self.service, self.machine)
        while win32serviceutil.QueryServiceStatus(self.service, self.machine)[1] == 3:
            time.sleep(0.25)
        if win32serviceutil.QueryServiceStatus(self.service, self.machine)[1] != 1:
            raise Exception("WindowsService: Unable to stop service!")

    def _StartProcess(self):
        if self._IsProcessRunning():
            return
        win32serviceutil.StartService(self.service, self.machine)
        while win32serviceutil.QueryServiceStatus(self.service, self.machine)[1] == 2:
            time.sleep(0.25)
        if win32serviceutil.QueryServiceStatus(self.service, self.machine)[1] == 4:
            raise Exception("WindowsService: Unable to start service!")

    def _IsProcessRunning(self):
        if win32serviceutil.QueryServiceStatus(self.service, self.machine)[1] == 4:
            return True
        return False

    def OnTestStarting(self):
        self.strangeExit = False
        if self.restartOnTest or not self._IsProcessRunning():
            self._StopProcess()
            self._StartProcess()

    def OnTestFinished(self):
        if not self._IsProcessRunning():
            self.strangeExit = True
        if self.restartOnTest:
            self._StopProcess()

    def GetMonitorData(self):
        if self.strangeExit:
            return {"WindowsService.txt": "Process exited early"}
        return None

    def DetectedFault(self):
        #if self.faultOnEarlyExit:
        #	return not self._IsProcessRunning()
        #
        #else:
        #	return False
        return False

    def OnFault(self):
        self._StopProcess()

    def OnShutdown(self):
        pass


class ProcessKiller(Monitor):
    """Will watch for specific process and kill."""

    def __init__(self, args):
        self._name = "ProcessWatcher"
        if not args.has_key("ProcessNames"):
            raise Exception("ProcessWatcher requires a parameter named ProcessNames.")
        self._names = args["ProcessNames"].replace("'''", "").split(',')

    def OnTestStarting(self):
        pass

    def OnTestFinished(self):
        for name in self._names:
            os.popen('TASKKILL /IM ' + name + ' /F')
            time.sleep(.6)

    def DetectedFault(self):
        return False

    def OnShutdown(self):
        try:
            for name in self._names:
                os.popen('TASKKILL /IM ' + name + ' /F')
                time.sleep(.6)
        except:
            pass


class ProcessID(Monitor):
    """
    Monitors CrashReporter on MacOS, LinuxApport on Linux and the process id of a process.
    There are external monitors present for CrashReporter and LinuxApport but applying them
    means having a delay between each testcase because they will wait and observe a folder for a
    crash report after each test case. This monitor tries to observe the process id for a change
    and will only after observe a specific folder for a crash report. The monitor does not work
    with child processes like plugin processes.
    """

    def __init__(self, args):
        Monitor.__init__(self, args)
        self._name = "ProcessID"

        self.command = getStringAttribute(args, "Command")
        if not self.command:
            raise ValueError("Command not provided or empty in %s" % __file__)
        self.arguments = shlex.split(self.command) + shlex.split(getStringAttribute(args, "Arguments"))

        self.process_environment = getStringAttribute(args, "Environment")
        if self.process_environment:
            os.environ.update(dict([p.split("=") for p in self.process_environment.split("|")]))

        self.asan_options = getStringAttribute(args, "ASanOptions")
        if self.asan_options:
            os.environ["ASAN_OPTIONS"] = "%s" % self.asan_options

        self.asan_library_path = getStringAttribute(args, "ASanMacOSRuntime")
        if isMacOS and self.asan_library_path:
            os.environ["DYLD_LIBRARY_PATH"] = getStringAttribute(args, "ASanMacOSRuntime")

        self.asan_symbolizer = getStringAttribute(args, "ASanSymbolizer")
        if self.asan_symbolizer:
            os.environ["ASAN_SYMBOLIZER_PATH"] = self.asan_symbolizer
        self.heartbeat = getFloatAttribute(args, "Heartbeat", "0.0")
        self.monitor_console = getBooleanAttribute(args, "NoConsoleLogging")
        self.gdb_cmd_batch = getStringAttribute(args, "GDBCommands")
        self.print_subprocess_output = getBooleanAttribute(args, "PrintSubprocessOutput")
        self.lookout_time = getFloatAttribute(args, "LookoutTime", "5.0")

        self.system_report_path = getStringAttribute(args, 'LogFolder')
        if self.system_report_path and not os.path.isdir(self.system_report_path):
                raise ValueError("Provided path for LogFolder is invalid.")
        elif isMacOS():
            self.system_report_path = os.path.join(os.environ['HOME'], "Library/Logs/DiagnosticReports")
            if os.path.isdir(self.system_report_path):
                try:
                    os.makedirs(self.system_report_path)
                except (IOError, OSError) as e:
                    if e.errno != 17:
                        raise

        self.pid = self.process = None
        self.console_log = self.crash_trace = []
        self.failure = False
        self.first_run = True

    def OnTestStarting(self):
        if not self._IsRunning():
            self._StartProcess()

    def _StartProcess(self):
        print("Command: {}".format(self.arguments))
        self.process = Popen(self.arguments, stderr=STDOUT, stdout=PIPE,
                             env=os.environ, bufsize=1, close_fds=isPosix())
        self.pid = self.process.pid

        def enqueue_output(out, queue):
            for line in iter(out.readline, ""):
                queue.put(line)
            out.close()

        self.terminal_queue = Queue.Queue()
        self.terminal_producer = threading.Thread(target=enqueue_output, args=(self.process.stdout, self.terminal_queue))
        self.terminal_consumer = threading.Thread(target=self._grab_sanitizer_trace)
        self.terminal_producer.setDaemon(True)
        self.terminal_consumer.setDaemon(True)
        self.terminal_producer.start()
        self.terminal_consumer.start()

    def _IsRunning(self):
        if self.process is None:
            MonitorDebug(self._name, "IsRunning: False (self.process == None")
            return False
        if self.process.poll() is not None:
            MonitorDebug(self._name, "IsRunning: False (self.process.poll != None)")
            return False
        MonitorDebug(self._name, "IsRunning: True")
        return True

    def _grab_sanitizer_trace(self):
        """Run in the background and set self.failure to true once an ASan crash got detected."""
        inside_sanitizer_trace = False
        self.crash_trace = []
        while True:
            captured_line = self.terminal_queue.get()
            if self.print_subprocess_output:
                print(captured_line.strip("\n"))
            if self.monitor_console:
                self.console_log.append(captured_line)
            if not inside_sanitizer_trace:
                if captured_line.find("ERROR: AddressSanitizer") != -1 and captured_line.find("AddressSanitizer failed to allocate") == -1:
                    inside_sanitizer_trace = True
            if inside_sanitizer_trace and \
                    (captured_line.find("Stats: ") != -1 or
                     captured_line.find("ABORTING") != -1 or
                     captured_line.find("ERROR: Failed") != -1):
                inside_sanitizer_trace = False
                self.failure = True
                break
            if inside_sanitizer_trace:
                self.crash_trace.append(captured_line)
        if self.failure and self._IsRunning():
            self.process.terminate()
            self.process.kill()
            self.process = None

    def OnTestFinished(self):
        self.console_log = []
        if not self._IsRunning():
            self.failure = True
        time.sleep(self.heartbeat)

    def _from_core_dump(self, log_folder):
        core_filename = os.path.join(log_folder, 'core.%s' % str(self.pid))
        if os.path.exists(core_filename):
            gdb_args = ["gdb", "-n", "-batch", "-x", self.gdb_cmd_batch, self.command, core_filename]
            gdb_output = check_output(gdb_args, stdin=None, stderr=STDOUT, close_fds=isPosix())
            os.remove(core_filename)
            return gdb_output

    def _from_crash_reporter(self, log_folder):
        report = ""
        for fname in os.listdir(log_folder):
            if not fname.endswith(".crash"):
                continue
            with open(os.path.join(log_folder, fname)) as fd:
                content = fd.readlines()
                try:
                    crash_pid = int(re.findall("\[(\d+)\]", content[0])[0])
                except:
                    continue
                if crash_pid == self.pid:
                    report = "".join(content)
                    os.remove(os.path.join(log_folder, fname))
                    break
        return report

    def get_crash_report(self, log_folder):
        if not os.path.isdir(log_folder):
            return ""
        if isMacOS():
            return self._from_crash_reporter(log_folder)
        if isLinux():
            return self._from_core_dump(log_folder)

    def DetectedFault(self):
        return self.failure

    def GetMonitorData(self):
        time.sleep(self.lookout_time)
        sytem_crash_report = self.get_crash_report(self.system_report_path)
        bucket = {}

        if not len(self.crash_trace):
            if self.process.returncode < 0:
                crashSignals = [
                    # POSIX.1-1990 signals
                    signal.SIGILL,
                    signal.SIGABRT,
                    signal.SIGFPE,
                    signal.SIGSEGV,
                    # SUSv2 / POSIX.1-2001 signals
                    signal.SIGBUS,
                    signal.SIGSYS,
                    signal.SIGTRAP,
            ]
            for crashSignal in crashSignals:
                if process.returncode == -crashSignal:
                    bucket["auxdat.txt"] = "Process exited with signal: %d" % -process.returncode
        else:
            bucket["auxdat.txt"] = "".join(self.crash_trace)

        if sytem_crash_report:
            bucket["system_crash_report.txt"] = sytem_crash_report

        if self.console_log:
            bucket["stdout.txt"] = "".join(self.console_log[-1000:])

        if self.failure:
            meta = {
                "environ": os.environ.data,
                "command": self.arguments
            }
            bucket["meta.txt"] = json.dumps(dict(meta))
            bucket["Bucket"] = os.path.basename(self.command)
            return bucket

    def OnFault(self):
        self._StopProcess()

    def OnShutdown(self):
        self._StopProcess()

    def _StopProcess(self):
        self.failure = False
        if self._IsRunning():
            try:
                MonitorDebug(self._name, "calling terminate()")
                self.process.terminate()
                MonitorDebug(self._name, "calling kill()")
                self.process.kill()
            except Exception:
                print(sys.exc_info())
            self.process.wait()
        self.process = None


class ASanConsoleMonitor(Monitor):

    def __init__(self, args):
        Monitor.__init__(self, args)
        self._name = "ASanConsoleMonitor"

        self.command = getStringAttribute(args, "Command")
        if not self.command:
            raise ValueError("Command not provided or empty in %s" % __file__)
        self.arguments = shlex.split(self.command) + shlex.split(getStringAttribute(args, "Arguments"))

        self.process_environment = getStringAttribute(args, "Environment")
        if self.process_environment:
            os.environ.update(dict([p.split("=") for p in self.process_environment.split("|")]))

        self.asan_options = getStringAttribute(args, "ASanOptions")
        if self.asan_options:
            os.environ["ASAN_OPTIONS"] = "%s" % self.asan_options

        self.asan_library_path = getStringAttribute(args, "ASanMacOSRuntime")
        if isMacOS and self.asan_library_path:
            os.environ["DYLD_LIBRARY_PATH"] = getStringAttribute(args, "ASanMacOSRuntime")

        self.asan_symbolizer = getStringAttribute(args, "ASanSymbolizer")
        if self.asan_symbolizer:
            os.environ["ASAN_SYMBOLIZER_PATH"] = self.asan_symbolizer

        if "StartOnCall" in args:
            self.start_on_call = True
            self.OnCallMethod = getStringAttribute(args, 'StartOnCall')
        else:
            self.start_on_call = False

        self.asan_regex = "(ERROR: AddressSanitizer:.*[Stats:|ABORTING|ERROR: Failed])"
        self.stderr = []
        self.stdout = []
        self.sanlog = []
        self.process = None
        self.failure = False

    def OnTestStarting(self):
        if not self.start_on_call and not self._IsRunning():
            self._StopProcess()
            self._StartProcess()
        elif self.start_on_call:
            self._StopProcess()

    def PublisherCall(self, method):
        if self.start_on_call and self.OnCallMethod == method:
            MonitorDebug(self._name, "PublisherCall")
            self._StopProcess()
            self._StartProcess()

    def _IsRunning(self):
        if self.process is None:
            MonitorDebug(self._name, "IsRunning: False (self.process == None")
            return False
        if self.process.poll() is not None:
            MonitorDebug(self._name, "IsRunning: False (self.process.poll != None)")
            return False
        MonitorDebug(self._name, "IsRunning: True")
        return True

    def _StartProcess(self):
        MonitorDebug(self._name, "_StartProcess")
        self.failure = False
        self.sanlog = []
        self.stderr = []
        self.stdout = []

        print("Command: {}".format(self.arguments))
        self.process = Popen(self.arguments, stderr=PIPE, stdout=PIPE,
                             env=os.environ, bufsize=1, close_fds=isPosix())

        # Todo: Add timeout= for GUI applications.
        stdout, stderr = self.process.communicate()

        if stderr.find("ERROR: AddressSanitizer: ") != -1:
            if stderr.find("AddressSanitizer failed to allocate") == -1:
                self.failure = True
                self.sanlog = re.findall(self.asan_regex, stderr, re.DOTALL)[0]
                self.stdout = stdout
                self.stderr = stderr
        else:
            if self.process.returncode < 0:
                crashSignals = [
                    # POSIX.1-1990 signals
                    signal.SIGILL,
                    signal.SIGABRT,
                    signal.SIGFPE,
                    signal.SIGSEGV,
                    # SUSv2 / POSIX.1-2001 signals
                    signal.SIGBUS,
                    signal.SIGSYS,
                    signal.SIGTRAP,
            ]
            for crashSignal in crashSignals:
                if process.returncode == -crashSignal:
                    self.failure = True
                    self.sanlog = "Process exited with signal: %d" % -process.returncode
                    self.stdout = stdout
                    self.stderr = stderr

        if self.failure:
            self._StopProcess()

    def OnTestFinished(self):
        if self._IsRunning():
            self._StopProcess()

    def DetectedFault(self):
        return self.failure

    def GetMonitorData(self):
        #if not self.failure:
        #    return
        bucket = {}
        if self.sanlog:
            bucket["auxdat.txt"] = "".join(self.sanlog)
        if self.stdout:
            bucket["stdout.txt"] = "".join(self.stdout)
        if self.stderr:
            bucket["stderr.txt"] = "".join(self.stderr)
        meta = {
            "environ": os.environ.data,
            "command": self.arguments,
            "returncode": self.process.returncode
        }
        bucket["meta.txt"] = json.dumps(dict(meta))
        bucket["Bucket"] = os.path.basename(self.command)
        return bucket

    def OnFault(self):
        self._StopProcess()

    def OnShutdown(self):
        self._StopProcess()

    def _StopProcess(self):
        if not self.process:
            return
        if self._IsRunning():
            try:
                MonitorDebug(self._name, "calling terminate()")
                self.process.terminate()
                MonitorDebug(self._name, "calling kill()")
                self.process.kill()
            except Exception:
                print(sys.exc_info())
            self.process.wait()
        self.process = None
