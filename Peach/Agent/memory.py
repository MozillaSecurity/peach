# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
try:
    import sys
    import ctypes
    import win32pdhutil
    import win32api

    sys.path.append("..")
    sys.path.append("../..")

    from Peach.agent import Monitor

    PROCESS_VM_READ = 0x0010
    PROCESS_QUERY_INFORMATION = 0x0400

    DWORD = ctypes.c_ulong
    SIZE_T = ctypes.c_ulong

    MAX_PROCESSES = 1024
    MAX_PATH = 1024

    Psapi = ctypes.windll.Psapi
    Kernel32 = ctypes.windll.Kernel32

    class PROCESS_MEMORY_COUNTERS_EX(ctypes.Structure):
        _fields_ = [("cb", DWORD),
                    ("PageFaultCount", DWORD),
                    ("PeakWorkingSetSize", SIZE_T),
                    ("WorkingSetSize", SIZE_T),
                    ("QuotaPeakPagedPoolUsage", SIZE_T),
                    ("QuotaPagedPoolUsage", SIZE_T),
                    ("QuotaPeakNonPagedPoolUsage", SIZE_T),
                    ("QuotaNonPagedPoolUsage", SIZE_T),
                    ("PagefileUsage", SIZE_T),
                    ("PeakPagefileUsage", SIZE_T),
                    ("PrivateUsage", SIZE_T),
        ]

    class Memory(Monitor):
        """
        Agent that monitors the amount of memory a process is utilizing.  This is
        useful for detecting memory leaks within the fuzzing target
        """

        def __init__(self, args):
            """
            Constructor.  Arguments are supplied via the Peach XML
            file.

            @type	args: Dictionary
            @param	args: Dictionary of parameters
            """

            try:

                # Our name for this monitor
                self._name = "Memory Monitor"
                self._pid = None
                self._processName = None
                self._hProcess = None
                self._internalError = False
                self._memoryInfo = None
                self._threshold = None
                self._detectedFault = False
                self._stopOnFault = False

                # Report an error if no MemoryLimit and/or neither pid nor processName is defined

                while 1:

                    if args.has_key('StopOnFault'):
                        self._stopOnFault = str(args["StopOnFault"]).replace("'''", "")

                    if args.has_key('MemoryLimit'):
                        self._memoryLimit = int(args['MemoryLimit'].replace("'''", ""))
                        print("Memory: Memory Limit = %d" % self._memoryLimit)
                    else:
                        print("Memory: No memory limit specified")
                        self._internalError = True
                        break

                    if args.has_key('Pid'):
                        self._pid = int(args['Pid'].replace("'''", ""))
                        print("Memory: Pid = %d" % self._pid)

                    if args.has_key('ProcessName'):
                        self._processName = str(args['ProcessName']).replace("'''", "")
                        print("Memory: Process Name = %s" % self._processName)

                    if self._pid is None and self._processName is None:
                        print("Memory: No pid or process name provided")
                        self._internalError = True
                        break

                    break

            except:
                print("Memory: Caught Exception")
                raise

        def _OpenProcess(self, pid=None):

            if pid is not None:
                return Kernel32.OpenProcess(PROCESS_VM_READ | PROCESS_QUERY_INFORMATION, 0, pid)
            else:
                return None

        def _CloseProcess(self, handle=None):

            if handle is not None:
                Kernel32.CloseHandle(handle)

        def _GetProcessIdByName(self, name):
            """
            Try and get pid for a process by name.
            """

            try:
                win32pdhutil.GetPerformanceAttributes('Process', 'ID Process', name)
            except:
                sys.stdout.write("Memory: Unable to locate process [%s]\n" % name)
                raise

            pids = win32pdhutil.FindPerformanceAttributesByName(name)

            # If _my_ pid in there, remove it
            try:
                pids.remove(win32api.GetCurrentProcessId())
            except ValueError:
                pass

            return pids[0]

        def _GetProcessMemoryInfo(self, handle=None):

            if handle is None:
                return None

            psmemCounters = PROCESS_MEMORY_COUNTERS_EX()
            cb = DWORD(ctypes.sizeof(psmemCounters))
            b = Psapi.GetProcessMemoryInfo(handle, ctypes.byref(psmemCounters), cb)

            if not b:
                return None

            dict = {}

            for k, t in psmemCounters._fields_:
                dict[k] = getattr(psmemCounters, k)

            return dict

        def OnTestStarting(self):
            """
            Called right before start of test case or variation
            """

            # if only a process name was passed in, derive the pid from it
            if self._processName is not None:
                self._pid = self._GetProcessIdByName(self._processName)

                if self._pid is None:
                    print("Memory: OnTestStarting: Could not resolve pid")
                    self._internalError = True
                    return

            self._hProcess = self._OpenProcess(self._pid)

            if self._hProcess is None:
                print("Memory: Could not open target process")
                self._internalError = True
                return

            print("OnTestStarting: Process handle = %d" % self._hProcess)

            if self._hProcess is None:
                print("Memory: Could not open target process")
                self._internalError = True
                return

            self._memoryInfo = self._GetProcessMemoryInfo(self._hProcess)

            if self._memoryInfo is None:
                print("Memory: Could not acquire memory info")
                self._internalError = True
                return
            else:
                print("Memory Used = %d" % self._memoryInfo['PrivateUsage'])

                if self._memoryInfo['PrivateUsage'] > self._memoryLimit:
                    self._detectedFault = True

                    if self._stopOnFault == "True":
                        print("Memory: Stopping on fault")
                        self._internalError = True

        def OnTestFinished(self):
            """
            Called right after a test case or variation
            """
            self._CloseProcess(self._hProcess)
            self._hProcess = None

        def GetMonitorData(self):
            """
            Get any monitored data from a test case.
            """
            return {'MemoryUsed.txt': str(self._memoryInfo['PrivateUsage'])}

        def DetectedFault(self):
            """
            Check if a fault was detected.
            """
            return self._detectedFault

        def OnFault(self):
            """
            Called when a fault was detected.
            """
            pass

        def OnShutdown(self):
            """
            Called when Agent is shutting down, typically at end
            of a test run or when a Stop-Run occurs
            """
            self._CloseProcess(self._hProcess)

        def StopRun(self):
            """
            Return True to force test run to fail.  This
            should return True if an unrecoverable error
            occurs.
            """
            return self._internalError

    if __name__ == "__main__":
        d = {
            "MemoryLimit": "5000000",
            "ProcessName": "CrashableServer"
        }
        a = Memory(d)
        a.OnTestStarting()

        print(a.DetectedFault())
        a.OnTestFinished()
        a.OnTestStarting()

        print(a.DetectedFault())
        a.OnTestFinished()
except:
    pass
