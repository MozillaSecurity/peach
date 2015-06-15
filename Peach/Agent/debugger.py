# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
import os
import gc
import re
import sys
import time
import struct
import signal
import pickle
import tempfile

import psutil

from Peach.agent import Monitor

try:
    import comtypes
    from ctypes import *
    from comtypes import HRESULT, COMError
    from comtypes.client import CreateObject, GetEvents, PumpEvents
    from comtypes.hresult import S_OK, E_FAIL, E_UNEXPECTED, E_INVALIDARG
    from comtypes.automation import IID
    import PyDbgEng
    from comtypes.gen import DbgEng
    import win32serviceutil
    import win32service
    import win32api, win32con, win32process, win32pdh
    from multiprocessing import *


    class _DbgEventHandler(PyDbgEng.IDebugOutputCallbacksSink, PyDbgEng.IDebugEventCallbacksSink):

        buff = ''
        TakeStackTrace = True

        def LocateWinDbg(self):
            """
            This method also exists in process.PageHeap!
            """

            try:

                hkey = win32api.RegOpenKey(win32con.HKEY_CURRENT_USER, "Software\\Microsoft\\DebuggingTools")

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

                return None

            val, type = win32api.RegQueryValueEx(hkey, "WinDbg")
            win32api.RegCloseKey(hkey)
            return val

        def Output(self, this, Mask, Text):
            self.buff += Text

        def LoadModule(self, unknown, imageFileHandle, baseOffset, moduleSize, moduleName, imageName, checkSum,
                       timeDateStamp=None):
            if self.pid is None:
                self.dbg.idebug_control.Execute(DbgEng.DEBUG_OUTCTL_THIS_CLIENT,
                                                c_char_p("|."),
                                                DbgEng.DEBUG_EXECUTE_ECHO)

                match = re.search(r"\.\s+\d+\s+id:\s+([0-9a-fA-F]+)\s+\w+\s+name:\s", self.buff)
                if match is not None:
                    self.pid = int(match.group(1), 16)

                    # Write out PID for main peach process
                    fd = open(self.TempfilePid, "wb+")
                    fd.write(str(self.pid))
                    fd.close()

        def GetInterestMask(self):
            return PyDbgEng.DbgEng.DEBUG_EVENT_EXCEPTION | PyDbgEng.DbgEng.DEBUG_FILTER_INITIAL_BREAKPOINT | \
                   PyDbgEng.DbgEng.DEBUG_EVENT_EXIT_PROCESS | PyDbgEng.DbgEng.DEBUG_EVENT_LOAD_MODULE

        def ExitProcess(self, dbg, ExitCode):
            print("_DbgEventHandler.ExitProcess: Target application has exitted")
            self.quit.set()
            return DEBUG_STATUS_NO_CHANGE

        def Exception(self, dbg, ExceptionCode, ExceptionFlags, ExceptionRecord,
                      ExceptionAddress, NumberParameters, ExceptionInformation0, ExceptionInformation1,
                      ExceptionInformation2, ExceptionInformation3, ExceptionInformation4,
                      ExceptionInformation5, ExceptionInformation6, ExceptionInformation7,
                      ExceptionInformation8, ExceptionInformation9, ExceptionInformation10,
                      ExceptionInformation11, ExceptionInformation12, ExceptionInformation13,
                      ExceptionInformation14, FirstChance):

            if self.IgnoreSecondChanceGardPage and ExceptionCode == 0x80000001:
                return DbgEng.DEBUG_STATUS_NO_CHANGE

            # Only capture dangerouse first chance exceptions
            if FirstChance:
                if self.IgnoreFirstChanceGardPage and ExceptionCode == 0x80000001:
                    # Ignore, sometimes used as anti-debugger
                    # by Adobe Flash.
                    return DbgEng.DEBUG_STATUS_NO_CHANGE

                # Guard page or illegal op
                elif ExceptionCode == 0x80000001 or ExceptionCode == 0xC000001D:
                    pass
                elif ExceptionCode == 0xC0000005:
                    # is av on eip?
                    if ExceptionInformation0 == 0 and ExceptionInformation1 == ExceptionAddress:
                        pass

                    # is write a/v?
                    elif ExceptionInformation0 == 1 and ExceptionInformation1 != 0:
                        pass

                    # is DEP?
                    elif ExceptionInformation0 == 0:
                        pass

                    else:
                        # Otherwise skip first chance
                        return DbgEng.DEBUG_STATUS_NO_CHANGE
                else:
                    # otherwise skip first chance
                    return DbgEng.DEBUG_STATUS_NO_CHANGE

            if self.handlingFault.is_set() or self.handledFault.is_set():
                # We are already handling, so skip
                #sys.stdout.write("_DbgEventHandler::Exception(): handlingFault set, skipping.\n")
                return DbgEng.DEBUG_STATUS_BREAK

            try:
                print("Exception: Found interesting exception")

                self.crashInfo = {}
                self.handlingFault.set()

                ## 1. Output registers
                print("Exception: 1. Output registers")

                dbg.idebug_control.Execute(DbgEng.DEBUG_OUTCTL_THIS_CLIENT,
                                           c_char_p("r"),
                                           DbgEng.DEBUG_EXECUTE_ECHO)
                dbg.idebug_control.Execute(DbgEng.DEBUG_OUTCTL_THIS_CLIENT,
                                           c_char_p("rF"),
                                           DbgEng.DEBUG_EXECUTE_ECHO)
                dbg.idebug_control.Execute(DbgEng.DEBUG_OUTCTL_THIS_CLIENT,
                                           c_char_p("rX"),
                                           DbgEng.DEBUG_EXECUTE_ECHO)
                self.buff += "\n\n"

                ## 2. Ouput stack trace
                if _DbgEventHandler.TakeStackTrace:
                    print("Exception: 2. Output stack trace")

                    dbg.idebug_control.Execute(DbgEng.DEBUG_OUTCTL_THIS_CLIENT,
                                               c_char_p("kb"),
                                               DbgEng.DEBUG_EXECUTE_ECHO)
                    self.buff += "\n\n"

                else:
                    _DbgEventHandler.TakeStackTrace = True
                    self.buff += "\n[Peach] Error, stack trace failed.\n\n"

                ## 3. Write dump file
                minidump = None

                ## 4. Bang-Exploitable
                print("Exception: 3. Bang-Exploitable")

                handle = None
                try:
                    p = None
                    if not (hasattr(sys, "frozen") and sys.frozen == "console_exe"):
                        p = __file__[:-24] + "tools\\bangexploitable\\"
                        if sys.version.find("AMD64") != -1:
                            p += "x64"
                        else:
                            p += "x86"

                    else:
                        p = os.path.dirname(os.path.abspath(sys.executable))

                    dbg.idebug_control.Execute(DbgEng.DEBUG_OUTCTL_THIS_CLIENT, c_char_p(".load %s\\msec.dll" % p),
                                               DbgEng.DEBUG_EXECUTE_ECHO)
                    dbg.idebug_control.Execute(DbgEng.DEBUG_OUTCTL_THIS_CLIENT, c_char_p("!exploitable -m"),
                                               DbgEng.DEBUG_EXECUTE_ECHO)
                    dbg.idebug_control.Execute(DbgEng.DEBUG_OUTCTL_THIS_CLIENT, c_char_p("!msec.exploitable -m"),
                                               DbgEng.DEBUG_EXECUTE_ECHO)

                except:
                    raise

                ## Now off to other things...
                print("Exception: Building crashInfo")

                if minidump:
                    self.crashInfo = {'StackTrace.txt': self.buff.replace(chr(0x0a), "\r\n"), 'Dump.dmp': minidump}
                else:
                    self.crashInfo = {'StackTrace.txt': self.buff.replace(chr(0x0a), "\r\n")}

                # Build bucket string
                try:
                    bucketId = re.compile("DEFAULT_BUCKET_ID:\s+([A-Za-z_]+)").search(self.buff).group(1)
                    exceptionAddress = re.compile("ExceptionAddress: ([^\s\b]+)").search(self.buff).group(1)
                    exceptionCode = re.compile("ExceptionCode: ([^\s\b]+)").search(self.buff).group(1)

                    exceptionType = "AV"
                    if re.compile("READ_ADDRESS").search(self.buff) is not None:
                        exceptionType = "ReadAV"
                    elif re.compile("WRITE_ADDRESS").search(self.buff) is not None:
                        exceptionType = "WriteAV"

                    bucket = "%s_at_%s" % (exceptionType, exceptionAddress)

                except:
                    # Sometimes !analyze -v fails
                    bucket = "Unknown"

                self.crashInfo["Bucket"] = bucket

                ## Do we have !exploitable?

                try:
                    majorHash = re.compile("^MAJOR_HASH:(0x.*)$", re.M).search(self.buff).group(1)
                    minorHash = re.compile("^MINOR_HASH:(0x.*)$", re.M).search(self.buff).group(1)
                    classification = re.compile("^CLASSIFICATION:(.*)$", re.M).search(self.buff).group(1)
                    shortDescription = re.compile("^SHORT_DESCRIPTION:(.*)$", re.M).search(self.buff).group(1)

                    if majorHash is not None and minorHash is not None:
                        bucket = "%s_%s_%s_%s" % (classification,
                                                  shortDescription,
                                                  majorHash,
                                                  minorHash)

                        self.crashInfo["Bucket"] = bucket

                except:
                    pass

                # Done

            except:
                sys.stdout.write(repr(sys.exc_info()) + "\n")
                raise

            self.buff = ""
            self.fault = True

            print("Exception: Writing to file")
            fd = open(self.Tempfile, "wb+")
            fd.write(pickle.dumps(self.crashInfo))
            fd.close()

            self.handledFault.set()
            return DbgEng.DEBUG_STATUS_BREAK


    def WindowsDebugEngineProcess_run(*args, **kwargs):

        started = kwargs['Started']
        handlingFault = kwargs['HandlingFault']
        handledFault = kwargs['HandledFault']
        CommandLine = kwargs.get('CommandLine', None)
        Service = kwargs.get('Service', None)
        ProcessName = kwargs.get('ProcessName', None)
        ProcessID = kwargs.get('ProcessID', None)
        KernelConnectionString = kwargs.get('KernelConnectionString', None)
        SymbolsPath = kwargs.get('SymbolsPath', None)
        IgnoreFirstChanceGardPage = kwargs.get('IgnoreFirstChanceGardPage', None)
        IgnoreSecondChanceGardPage = kwargs.get('IgnoreSecondChanceGardPage', None)
        quit = kwargs['Quit']
        Tempfile = kwargs['Tempfile']
        WinDbg = kwargs['WinDbg']
        TempfilePid = kwargs['TempfilePid']
        FaultOnEarlyExit = kwargs['FaultOnEarlyExit']

        dbg = None

        print("WindowsDebugEngineProcess_run")

        # Hack for comtypes early version
        comtypes._ole32.CoInitializeEx(None, comtypes.COINIT_APARTMENTTHREADED)

        try:
            _eventHandler = _DbgEventHandler()
            _eventHandler.pid = None
            _eventHandler.handlingFault = handlingFault
            _eventHandler.handledFault = handledFault
            _eventHandler.IgnoreFirstChanceGardPage = IgnoreFirstChanceGardPage
            _eventHandler.IgnoreSecondChanceGardPage = IgnoreSecondChanceGardPage
            _eventHandler.quit = quit
            _eventHandler.Tempfile = Tempfile
            _eventHandler.TempfilePid = TempfilePid
            _eventHandler.FaultOnEarlyExit = FaultOnEarlyExit

            if KernelConnectionString:
                dbg = PyDbgEng.KernelAttacher(connection_string=KernelConnectionString,
                                              event_callbacks_sink=_eventHandler,
                                              output_callbacks_sink=_eventHandler,
                                              symbols_path=SymbolsPath,
                                              dbg_eng_dll_path=WinDbg)

            elif CommandLine:
                dbg = PyDbgEng.ProcessCreator(command_line=CommandLine,
                                              follow_forks=True,
                                              event_callbacks_sink=_eventHandler,
                                              output_callbacks_sink=_eventHandler,
                                              symbols_path=SymbolsPath,
                                              dbg_eng_dll_path=WinDbg)

            elif ProcessName:

                pid = None
                for x in range(10):
                    print("WindowsDebugEngineThread: Attempting to locate process by name...")
                    pid = GetProcessIdByName(ProcessName)
                    if pid is not None:
                        break

                    time.sleep(0.25)

                if pid is None:
                    raise Exception("Error, unable to locate process '%s'" % ProcessName)

                dbg = PyDbgEng.ProcessAttacher(pid,
                                               event_callbacks_sink=_eventHandler,
                                               output_callbacks_sink=_eventHandler,
                                               symbols_path=SymbolsPath,
                                               dbg_eng_dll_path=WinDbg)

            elif ProcessID:

                print("Attaching by pid: %d" % ProcessID)
                pid = ProcessID
                dbg = PyDbgEng.ProcessAttacher(pid, event_callbacks_sink=_eventHandler,
                                               output_callbacks_sink=_eventHandler, symbols_path=SymbolsPath,
                                               dbg_eng_dll_path=WinDbg)

            elif Service:

                # Make sure service is running
                if win32serviceutil.QueryServiceStatus(Service)[1] != 4:
                    try:
                        # Some services auto-restart, if they do
                        # this call will fail.
                        win32serviceutil.StartService(Service)
                    except:
                        pass

                    while win32serviceutil.QueryServiceStatus(Service)[1] == 2:
                        time.sleep(0.25)

                    if win32serviceutil.QueryServiceStatus(Service)[1] != 4:
                        raise Exception("WindowsDebugEngine: Unable to start service!")

                # Determine PID of service
                scm = win32service.OpenSCManager(None, None, win32service.SC_MANAGER_ALL_ACCESS)
                hservice = win32service.OpenService(scm, Service, 0xF01FF)

                status = win32service.QueryServiceStatusEx(hservice)
                pid = status["ProcessId"]

                win32service.CloseServiceHandle(hservice)
                win32service.CloseServiceHandle(scm)

                dbg = PyDbgEng.ProcessAttacher(pid,
                                               event_callbacks_sink=_eventHandler,
                                               output_callbacks_sink=_eventHandler,
                                               symbols_path=SymbolsPath,
                                               dbg_eng_dll_path=WinDbg)

            else:
                raise Exception("Didn't find way to start debugger... bye bye!!")

            _eventHandler.dbg = dbg
            started.set()
            dbg.event_loop_with_quit_event(quit)

        finally:
            if dbg is not None:
                if dbg.idebug_client is not None:
                    dbg.idebug_client.EndSession(DbgEng.DEBUG_END_ACTIVE_TERMINATE)
                    dbg.idebug_client.Release()
                elif dbg.idebug_control is not None:
                    dbg.idebug_control.EndSession(DbgEng.DEBUG_END_ACTIVE_TERMINATE)
                    dbg.idebug_control.Release()

            dbg = None

            comtypes._ole32.CoUninitialize()


    def GetProcessIdByName(procname):
        """
        Try and get pid for a process by name.
        """

        ourPid = -1
        procname = procname.lower()

        try:
            ourPid = win32api.GetCurrentProcessId()

        except:
            pass

        pids = win32process.EnumProcesses()
        for pid in pids:
            if ourPid == pid:
                continue

            try:
                hPid = win32api.OpenProcess(win32con.PROCESS_QUERY_INFORMATION | win32con.PROCESS_VM_READ, 0, pid)

                try:
                    mids = win32process.EnumProcessModules(hPid)
                    for mid in mids:
                        name = str(win32process.GetModuleFileNameEx(hPid, mid))
                        if name.lower().find(procname) != -1:
                            return pid

                finally:
                    win32api.CloseHandle(hPid)
            except:
                pass

        return None

    class WindowsDebugEngine(Monitor):
        """
        Windows debugger agent.  This debugger agent is based on the windbg engine and
        supports the following features:

            * User mode debugging
            * Kernel mode debugging
            * x86 and x64
            * Symbols and symbol server

        """

        def __init__(self, args):
            Monitor.__init__(self, args)

            print("WindowsDebugEngine::__init__()")

            self.started = None
            # Set at start of exception handling
            self.handlingFault = None
            # Set when collection finished
            self.handledFault = None
            self.crashInfo = None
            self.fault = False
            self.thread = None
            self.tempfile = None
            self.WinDbg = None

            if args.has_key('CommandLine'):
                self.CommandLine = str(args['CommandLine']).replace("'''", "")
            else:
                self.CommandLine = None

            if args.has_key('Service'):
                self.Service = str(args['Service']).replace("'''", "")
            else:
                self.Service = None

            if args.has_key('ProcessName'):
                self.ProcessName = str(args['ProcessName']).replace("'''", "")
            else:
                self.ProcessName = None

            if args.has_key('ProcessID'):
                self.ProcessID = int(args['ProcessID'].replace("'''", ""))
            else:
                self.ProcessID = None

            if args.has_key('KernelConnectionString'):
                self.KernelConnectionString = str(args['KernelConnectionString']).replace("'''", "")
            else:
                self.KernelConnectionString = None

            if args.has_key('SymbolsPath'):
                self.SymbolsPath = str(args['SymbolsPath']).replace("'''", "")
            else:
                self.SymbolsPath = "SRV*http://msdl.microsoft.com/download/symbols"

            if args.has_key("StartOnCall"):
                self.StartOnCall = True
                self.OnCallMethod = str(args['StartOnCall']).replace("'''", "").lower()
            else:
                self.StartOnCall = False

            if args.has_key("WinDbg"):
                self.WinDbg = str(args['WinDbg']).replace("'''", "").lower()

            if args.has_key("IgnoreFirstChanceGardPage"):
                self.IgnoreFirstChanceGardPage = True
            else:
                self.IgnoreFirstChanceGardPage = False

            if args.has_key("IgnoreSecondChanceGardPage"):
                self.IgnoreSecondChanceGardPage = True
            else:
                self.IgnoreSecondChanceGardPage = False

            if args.has_key("NoCpuKill"):
                self.NoCpuKill = True
            else:
                self.NoCpuKill = False

            if args.has_key("FaultOnEarlyExit"):
                self.FaultOnEarlyExit = True
            else:
                self.FaultOnEarlyExit = False

            if self.Service is None and self.CommandLine is None and self.ProcessName is None \
                and self.KernelConnectionString is None and self.ProcessID is None:
                raise PeachException(
                    "Unable to create WindowsDebugEngine, missing Service, or CommandLine, or ProcessName, or ProcessID, or KernelConnectionString parameter.")

            self.handlingFault = None
            self.handledFault = None

        def _StartDebugger(self):

            try:
                if self.cpu_hq is not None:
                    win32pdh.RemoveCounter(self.cpu_counter_handle)
                    win32pdh.CloseQuery(self.cpu_hq)
                    self.cpu_hq = None
                    self.cpu_counter_handle = None
            except:
                pass

            # Clear all our event handlers
            self.started = Event()
            self.quit = Event()
            self.handlingFault = Event()
            self.handledFault = Event()
            self.crashInfo = None
            self.fault = False
            self.pid = None
            self.cpu_process = None
            self.cpu_path = None
            self.cpu_hq = None
            self.cpu_counter_handle = None

            (fd, self.tempfile) = tempfile.mkstemp()
            os.close(fd)
            (fd, self.tempfilepid) = tempfile.mkstemp()
            os.close(fd)

            try:
                os.unlink(self.tempfile)
            except:
                pass

            self.thread = Process(group=None, target=WindowsDebugEngineProcess_run, kwargs={
            'Started': self.started,
            'HandlingFault': self.handlingFault,
            'HandledFault': self.handledFault,
            'CommandLine': self.CommandLine,
            'Service': self.Service,
            'ProcessName': self.ProcessName,
            'ProcessID': self.ProcessID,
            'KernelConnectionString': self.KernelConnectionString,
            'SymbolsPath': self.SymbolsPath,
            'IgnoreFirstChanceGardPage': self.IgnoreFirstChanceGardPage,
            'IgnoreSecondChanceGardPage': self.IgnoreSecondChanceGardPage,
            'Quit': self.quit,
            'Tempfile': self.tempfile,
            'WinDbg': self.WinDbg,
            'TempfilePid': self.tempfilepid,
            'FaultOnEarlyExit': self.FaultOnEarlyExit
            })

            # Kick off our thread:
            self.thread.start()

            # Wait it...!
            self.started.wait()

            if not self.NoCpuKill:
                # Make sure we wait at least 1 second
                # for program to startup.  Needed with new
                # CPU killing k0de.
                time.sleep(1)

        def _StopDebugger(self, force=False):

            if force == False and self.handledFault is not None and (
                self.handlingFault.is_set() and not self.handledFault.is_set()):
                print("_StopDebugger(): Not killing process due to fault handling")
                return

            print("_StopDebugger() - force:", force)

            if self.thread is not None and self.thread.is_alive():
                self.quit.set()
                self.started.clear()

                self.thread.join(5)

                if force == False and self.handledFault is not None and (
                    self.handlingFault.is_set() and not self.handledFault.is_set()):
                    print("_StopDebugger(): Not killing process due to fault handling - 2")
                    return

                if self.thread.is_alive():

                    # 1. Terminate child process
                    if self.pid is not None:
                        psutil.Process(self.pid).terminate()

                    # 2. Terminate debugger process
                    self.thread.terminate()

                    # 3. Join process to avoid ZOMBIES!
                    self.thread.join()

                time.sleep(0.25) # Take a breath

            elif self.thread is not None:
                # quit could be set by event handler now
                self.thread.join()

            self.thread = None

        def _IsDebuggerAlive(self):
            return self.thread and self.thread.is_alive()

        def OnTestStarting(self):
            """
            Called right before start of test.
            """

            if not self.StartOnCall and not self._IsDebuggerAlive():
                self._StartDebugger()
            elif self.StartOnCall:
                self._StopDebugger()

        def PublisherCall(self, method):

            if not self.StartOnCall:
                return None

            if self.OnCallMethod == method.lower():
                self._StartDebugger()
                return True

            if self.OnCallMethod + "_isrunning" == method.lower():

                # Program has stopped if we are handling a fault.
                if self.handlingFault.is_set() or self.handledFault.is_set():
                    return False

                if not self.quit.is_set():
                    if self.pid is None:
                        fd = open(self.tempfilepid, "rb+")
                        pid = fd.read()
                        fd.close()

                        if len(pid) != 0:
                            self.pid = int(pid)

                            try:
                                os.unlink(self.tempfilepid)
                            except:
                                pass

                    if self.NoCpuKill == False and self.pid is not None:
                        try:
                            # Check and see if the CPU utilization is low
                            cpu = psutil.Process(self.pid).get_cpu_percent(interval=1.0)
                            if cpu is not None and cpu < 1.0:
                                cpu = psutil.Process(self.pid).get_cpu_percent(interval=1.0)
                                if cpu is not None and cpu < 1.0 and not self.quit.is_set():
                                    print("PublisherCall: Stopping debugger, CPU: %f" % cpu)
                                    self._StopDebugger()
                                    return False

                        except psutil.NoSuchProcess as e:
                            pass

                return not self.quit.is_set()

            return None

        def OnTestFinished(self):
            if not self.StartOnCall or not self._IsDebuggerAlive():
                return

            self._StopDebugger()

        def GetMonitorData(self):
            """
            Get any monitored data.
            """

            print("GetMonitorData(): Loading from file")
            fd = open(self.tempfile, "rb+")
            self.crashInfo = pickle.loads(fd.read())
            fd.close()

            try:
                os.unlink(self.tempfile)
            except:
                pass

            print("GetMonitorData(): Got it!")
            if self.crashInfo is not None:
                ret = self.crashInfo
                self.crashInfo = None
                return ret

            return None

        def RedoTest(self):
            """
            Returns True if the current iteration should be repeated
            """

            if self.handlingFault is None:
                return False

            if self.thread and self.thread.is_alive():
                time.sleep(0.15)

            if not self.handlingFault.is_set():
                return False

            print("RedoTest: Waiting for self.handledFault...")

            t = 60.0 * 3
            self.handledFault.wait(timeout=t)

            if not self.handledFault.is_set():
                print("RedoTest: Timmed out waiting for fault information")
                print("RedoTest: Killing debugger and target")
                self._StopDebugger(True)
                _DbgEventHandler.TakeStackTrace = False
                print("RedoTest: Attempting to re-run iteration")
                return True

            return False

        def DetectedFault(self):
            """
            Check if a fault was detected.
            """

            if self.FaultOnEarlyExit and (self.thread is None or not self.thread.is_alive()) and \
                    (self.handledFault is None or not self.handledFault.is_set()):
                print(">>>>>> RETURNING EARLY EXIT FAULT <<<<<<<<<")
                return True

            if self.handlingFault is None:
                print("DetectedFault: Agent was re-set, returning false")
                return False

            if self.thread and self.thread.is_alive():
                time.sleep(0.15)

            if not self.handlingFault.is_set():
                return False

            print(">>>>>> RETURNING FAULT <<<<<<<<<")

            return True

        def OnFault(self):
            """
            Called when a fault was detected.
            """
            self._StopDebugger()

        def OnShutdown(self):
            """
            Called when Agent is shutting down.
            """
            self._StopDebugger()

except:
    # Only complain on Windows platforms.
    #if sys.platform == 'win32':
    #	print "Warning: Windows debugger failed to load: ", sys.exc_info()
    pass

try:

    import vtrace, envi
    import threading

    class PeachNotifier(vtrace.Notifier):
        def __init__(self):
            pass

        def notify(self, event, trace):
            print("Got event: %d from pid %d, signal: %d" % (event, trace.getPid(), trace.getMeta("PendingSignal")))

            UnixDebugger.handlingFault.set()
            buff = ""

            addr = None

            # Stacktrace
            buff += "\nStacktrace:\n"
            buff += "   [   PC   ] [ Frame  ] [ Location ]\n"
            for frame in trace.getStackTrace():
                buff += "   0x%.8x 0x%.8x %s\n" % (frame[0], frame[1], self.bestName(trace, frame[0]))
                if addr is None:
                    addr = frame[0]

            # Registers
            buff += "\nRegisters:\n"
            regs = trace.getRegisters()
            rnames = regs.keys()
            rnames.sort()
            for r in rnames:
                buff += "   %s 0x%.8x\n" % (r, regs[r])

            # Dissassembly
            arch = trace.getMeta("Architecture")
            arch = envi.getArchModule(arch)

            mem = trace.readMemory(addr - 256, 512)
            addrStart = addr - 256
            offset = 0
            count = 0
            buff += "\nDisassembly:\n"
            ops = []
            while offset < 500 and count < 200:
                va = addrStart + offset
                op = arch.makeOpcode(mem[offset:])

                if va == addr:
                    for i in ops[-20:]:
                        buff += i

                    buff += ">>>0x%.8x: %s\n" % (va, arch.reprOpcode(op, va=va))
                    count = 190
                elif va < addr:
                    ops.append("   0x%.8x: %s\n" % (va, arch.reprOpcode(op, va=va)))
                else:
                    buff += "   0x%.8x: %s\n" % (va, arch.reprOpcode(op, va=va))

                offset += len(op)
                count += 1

            print(buff)

            UnixDebugger.lock.acquire()
            UnixDebugger.crashInfo = {'DebuggerOutput.txt': buff, 'Bucket': "AV_at_%d" % addr}
            UnixDebugger.fault = True
            UnixDebugger.lock.release()
            UnixDebugger.handledFault.set()


        def bestName(self, trace, address):
            """
            Return a string representing the best known name for
            the given address
            """
            if not address:
                return "NULL"

            match = trace.getSymByAddr(address)
            if match is not None:
                if int(match) == address:
                    return repr(match)
                else:
                    return "%s+%d" % (repr(match), address - int(match))

            map = trace.getMap(address)
            if map:
                return map[3]

            return "Who knows?!?!!?"

    class _TraceThread(threading.Thread):
        def __init__(self):
            threading.Thread.__init__(self)

        def run(self):
            self.trace = vtrace.getTrace()
            self.trace.registerNotifier(vtrace.NOTIFY_SIGNAL, PeachNotifier())
            self.trace.execute(self._command + " " + self._params)
            UnixDebugger.started.set()
            self.trace.run()


    class UnixDebugger(Monitor):
        """
        Unix GDB monitor.  This debugger monitor uses the gdb
        debugger via pygdb wrapper.  Tested under Linux and OS X.

            * Collect core files
            * User mode debugging
            * Capturing stack trace, registers, etc
            * Symbols is available
        """

        def __init__(self, args):

            UnixDebugger.quit = threading.Event()
            UnixDebugger.started = threading.Event()
            UnixDebugger.handlingFault = threading.Event()
            UnixDebugger.handledFault = threading.Event()
            UnixDebugger.lock = threading.Lock()
            UnixDebugger.crashInfo = None
            UnixDebugger.fault = False
            self.thread = None

            if args.has_key('Command'):
                self._command = str(args['Command']).replace("'''", "\"")
                self._params = str(args['Params']).replace("'''", "\"")
                self._pid = None

            elif args.has_key('ProcessName'):
                self._command = None
                self._params = None
                self._pid = self.GetProcessIdByName(str(args['ProcessName']).replace("'''", "\""))

            else:
                raise Exception("Unable to create UnixGdb!  Error in params!")

            if args.has_key("StartOnCall"):
                self.StartOnCall = True
                self.OnCallMethod = str(args['StartOnCall']).replace("'''", "").lower()

            else:
                self.StartOnCall = False

        def PublisherCall(self, method):

            if not self.StartOnCall:
                return

            if self.OnCallMethod == method.lower():
                self._StartDebugger()

        def _StartDebugger(self):
            UnixDebugger.quit.clear()
            UnixDebugger.started.clear()
            UnixDebugger.handlingFault.clear()
            UnixDebugger.handledFault.clear()
            UnixDebugger.fault = False
            UnixDebugger.crashInfo = None

            self.thread = _TraceThread()
            self.thread._command = self._command
            self.thread._params = self._params
            self.thread._pid = self._pid

            self.thread.start()
            UnixDebugger.started.wait()
            time.sleep(2)    # Let things spin up!

        def _StopDebugger(self):

            if self.thread is not None:
                if self.thread.isAlive():
                    UnixDebugger.quit.set()
                    UnixDebugger.started.clear()
                    self.thread.trace.kill()
                    self.thread.join()
                    time.sleep(0.25)    # Take a breath

                self.thread.trace.release() # FIX
                self.thread.trace.releaseMemory() # FIX fd

        def _IsDebuggerAlive(self):
            return self.thread is not None and self.thread.isAlive()

        def OnTestStarting(self):
            """
            Called right before start of test.
            """
            if not self.StartOnCall and not self._IsDebuggerAlive():
                self._StartDebugger()

            elif self.StartOnCall:
                self._StopDebugger()

        def OnTestFinished(self):
            if not self.StartOnCall or not self._IsDebuggerAlive():
                return

            self._StopDebugger()

        def GetMonitorData(self):
            """
            Get any monitored data.
            """
            UnixDebugger.lock.acquire()
            if UnixDebugger.crashInfo is not None:
                ret = UnixDebugger.crashInfo
                UnixDebugger.crashInfo = None
                UnixDebugger.lock.release()
                print("Returning crash data!")
                return ret

            UnixDebugger.lock.release()
            print("Not returning any crash data!")
            return None

        def DetectedFault(self):
            """
            Check if a fault was detected.
            """

            time.sleep(0.25)

            if not UnixDebugger.handlingFault.is_set():
                return False

            UnixDebugger.handledFault.wait()
            UnixDebugger.lock.acquire()

            if UnixDebugger.fault or not self.thread.isAlive():
                print(">>>>>> RETURNING FAULT <<<<<<<<<")
                UnixDebugger.fault = False
                UnixDebugger.lock.release()
                return True

            UnixDebugger.lock.release()
            return False

        def OnFault(self):
            """
            Called when a fault was detected.
            """
            self._StopDebugger()

        def OnShutdown(self):
            """
            Called when Agent is shutting down.
            """
            self._StopDebugger()


except:
    # Only complain on non-Windows platforms.
    #if not sys.platform in ['win32', 'darwin']:
    #	print "Warning: Unix debugger failed to load: ", sys.exc_info()
    pass
