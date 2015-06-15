# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
import os
import sys
import time

from Peach.Engine.engine import Engine
from Peach.publisher import Publisher


class Command(Publisher):
    """
    Run a command line program passing generated data as
    parameters.
    """

    def call(self, method, args):
        """
        Call method on COM object.

        @type	method: string
        @param	method: Command to execute
        @type	args: array of objects
        @param	args: Arguments to pass
        """

        realArgs = [method]
        for a in args:
            realArgs.append(a)

        return os.spawnv(os.P_WAIT, method, realArgs)


class Launcher(Publisher):
    """
    Launch a program.
    """

    def __init__(self, command, args="", waitTime=3):
        """
        @type	command: string
        @param	command: Command to run
        @type	args: string
        @type	args: Comma separated list of arguments
        @type	waitTime: integer
        @param	waitTime: Time in seconds to wait before killing process
        """
        Publisher.__init__(self)
        self.command = command
        self.args = args.split(",")
        self.waitTime = float(waitTime)

    def call(self, method, args):
        # windows or unix?
        if sys.platform == 'win32':
            return self.callWindows()

        return self.callUnix()

    def callUnix(self):
        """
        Launch program to consume file
        """

        # Launch via spawn

        realArgs = [self.command]
        for a in self.args:
            realArgs.append(a)

        pid = os.spawnv(os.P_NOWAIT, self.command, realArgs)

        for i in range(0, int(self.waitTime / 0.15)):
            (pid1, ret) = os.waitpid(pid, os.WNOHANG)
            if not (pid1 == 0 and ret == 0):
                break

            time.sleep(0.15)

        try:
            import signal

            os.kill(pid, signal.SIGTERM)
            time.sleep(0.25)
            (pid1, ret) = os.waitpid(pid, os.WNOHANG)
            if not (pid1 == 0 and ret == 0):
                return

            os.kill(pid, signal.SIGKILL)
        except:
            print(sys.exc_info())

    def callWindows(self):
        """
        Launch program to consume file
        """

        # Launch via spawn

        realArgs = ["cmd.exe", "/c", self.command]
        for a in self.args:
            realArgs.append(a)

        phandle = os.spawnv(os.P_NOWAIT, os.path.join(os.getenv('SystemRoot'), 'system32', 'cmd.exe'), realArgs)

        # Give it some time before we KILL!
        for i in range(int(self.waitTime / 0.25)):
            if win32process.GetExitCodeProcess(phandle) != win32con.STILL_ACTIVE:
                # Process exited already
                break

            time.sleep(0.25)

        try:
            pid = ctypes.windll.kernel32.GetProcessId(ctypes.c_ulong(phandle))
            if pid > 0:
                for cid in self.FindChildrenOf(pid):

                    chandle = win32api.OpenProcess(1, 0, cid)
                    win32process.TerminateProcess(chandle, 0)

                    try:
                        win32api.CloseHandle(chandle)
                    except:
                        pass

            win32process.TerminateProcess(phandle, 0)

            try:
                win32api.CloseHandle(phandle)
            except:
                pass

        except:
            pass

    def FindChildrenOf(self, parentid):

        childPids = []

        object = "Process"
        items, instances = win32pdh.EnumObjectItems(None, None, object, win32pdh.PERF_DETAIL_WIZARD)

        instance_dict = {}
        for instance in instances:
            if instance in instance_dict:
                instance_dict[instance] += 1
            else:
                instance_dict[instance] = 0

        for instance, max_instances in instance_dict.items():
            for inum in range(max_instances + 1):
                hq = win32pdh.OpenQuery()
                try:
                    hcs = []

                    path = win32pdh.MakeCounterPath((None, object, instance, None, inum, "ID Process"))
                    hcs.append(win32pdh.AddCounter(hq, path))

                    path = win32pdh.MakeCounterPath((None, object, instance, None, inum, "Creating Process ID"))
                    hcs.append(win32pdh.AddCounter(hq, path))

                    try:
                        # If the process goes away unexpectedly this call will fail
                        win32pdh.CollectQueryData(hq)

                        type, pid = win32pdh.GetFormattedCounterValue(hcs[0], win32pdh.PDH_FMT_LONG)
                        type, ppid = win32pdh.GetFormattedCounterValue(hcs[1], win32pdh.PDH_FMT_LONG)

                        if int(ppid) == parentid:
                            childPids.append(int(pid))
                    except:
                        pass

                finally:
                    win32pdh.CloseQuery(hq)

        return childPids


from ctypes import *
import time

PUL = POINTER(c_ulong)


class KeyBdInput(Structure):
    _fields_ = [("wVk", c_ushort),
                ("wScan", c_ushort),
                ("dwFlags", c_ulong),
                ("time", c_ulong),
                ("dwExtraInfo", PUL)]


class HardwareInput(Structure):
    _fields_ = [("uMsg", c_ulong),
                ("wParamL", c_short),
                ("wParamH", c_ushort)]


class MouseInput(Structure):
    _fields_ = [("dx", c_long),
                ("dy", c_long),
                ("mouseData", c_ulong),
                ("dwFlags", c_ulong),
                ("time", c_ulong),
                ("dwExtraInfo", PUL)]


class Input_I(Union):
    _fields_ = [("ki", KeyBdInput),
                ("mi", MouseInput),
                ("hi", HardwareInput)]


class Input(Structure):
    _fields_ = [("type", c_ulong),
                ("ii", Input_I)]


class SendProgramRefresh(Publisher):
    """
    Send target process F5
    """

    def __init__(self):
        """
        """

        Publisher.__init__(self)

    def call(self, method, args):
        self.windowName = method
        if sys.platform != 'win32':
            raise Exception("This publisher is windows only")

        win32gui.EnumWindows(SendProgramRefresh.enumCallback, self)

    @staticmethod
    def enumCallback(hwnd, self):
        title = win32gui.GetWindowText(hwnd)

        if title.find(self.windowName) > -1:
            try:
                win32gui.SetActiveWindow(hwnd)
                win32gui.SetForegroundWindow(hwnd)

                FInputs = Input * 1
                extra = c_ulong(0)
                ii_ = Input_I()
                ii_.ki = KeyBdInput(win32con.VK_F5, 0x3f, 0, 0, pointer(extra))
                x = FInputs(( 1, ii_ ))
                windll.user32.SendInput(1, pointer(x), sizeof(x[0]))

            except:
                pass

        return True


class DebuggerLauncher(Publisher):
    """
    Launch a program via Debugger
    """

    def __init__(self, waitTime=3):
        Publisher.__init__(self)
        self.waitTime = float(waitTime)

    def call(self, method, args):

        Engine.context.agent.OnPublisherCall(method)

        methodRunning = method + "_isrunning"
        for i in range(int(self.waitTime / 0.25)):
            ret = Engine.context.agent.OnPublisherCall(methodRunning)
            if not ret:
                # Process exited already
                break

            time.sleep(0.25)


class DebuggerLauncherNoWait(Publisher):
    """
    Launch a program via Debugger
    """

    def __init__(self, waitTime=3):
        Publisher.__init__(self)
        self.waitTime = float(waitTime)

    def call(self, method, args):
        Engine.context.agent.OnPublisherCall(method)


try:
    import win32gui, win32con, win32process, win32event, win32api
    import sys, time, os, signal, subprocess, ctypes

    TH32CS_SNAPPROCESS = 0x00000002

    class PROCESSENTRY32(ctypes.Structure):
        _fields_ = [("dwSize", ctypes.c_ulong),
                    ("cntUsage", ctypes.c_ulong),
                    ("th32ProcessID", ctypes.c_ulong),
                    ("th32DefaultHeapID", ctypes.c_ulong),
                    ("th32ModuleID", ctypes.c_ulong),
                    ("cntThreads", ctypes.c_ulong),
                    ("th32ParentProcessID", ctypes.c_ulong),
                    ("pcPriClassBase", ctypes.c_ulong),
                    ("dwFlags", ctypes.c_ulong),
                    ("szExeFile", ctypes.c_char * 260)]

    class LauncherGui(Publisher):
        """
        Writes a file to disk and then launches a program.  After
        some defined amount of time we will try and close the GUI
        application by sending WM_CLOSE than kill it.

        To use, first use this publisher like the FileWriter
        stream publisher.  Close, than call a program (or two).
        """

        def __init__(self, commandLine, windowname, waitTime=3):
            """
            @type	filename: string
            @param	filename: Filename to write to
            @type   windowname: string
            @param  windowname: Partial window name to locate and kill
            """
            Publisher.__init__(self)
            self.commandLine = commandLine
            self._windowName = windowname
            self.waitTime = float(waitTime)

            if sys.platform != 'win32':
                raise PeachException("Error, publisher LauncherGui not supported on non-Windows platforms.")

        def call(self, method, args):
            """
            Launch program to consume file

            @type	method: string
            @param	method: Command to execute
            @type	args: array of objects
            @param	args: Arguments to pass
            """

            hProcess, hThread, dwProcessId, dwThreadId = win32process.CreateProcess(
                None, self.commandLine, None, None, 0,
                win32con.NORMAL_PRIORITY_CLASS, None, None, None)

            while win32process.GetExitCodeProcess(hProcess) == win32con.STILL_ACTIVE:
                time.sleep(0.25)

            self.closeApp(hProcess, self._windowName)

        @staticmethod
        def enumCallback(hwnd, windowName):
            """
            Will get called by win32gui.EnumWindows, once for each
            top level application window.
            """

            try:
                # Get window title
                title = win32gui.GetWindowText(hwnd)

                # Is this our guy?
                if title.find(windowName) == -1:
                    win32gui.EnumChildWindows(hwnd, FileWriterLauncherGui.enumChildCallback, windowName)
                    return

                # Send WM_CLOSE message
                win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
            except:
                pass

        @staticmethod
        def enumChildCallback(hwnd, windowName):
            """
            Will get called by win32gui.EnumWindows, once for each
            top level application window.
            """

            try:

                # Get window title
                title = win32gui.GetWindowText(hwnd)

                # Is this our guy?
                if title.find(windowName) == -1:
                    return

                # Send WM_CLOSE message
                win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)

            except:
                pass
            #print sys.exc_info()

        def genChildProcesses(self, proc):
            parentPid = proc.pid

            for p in self.genProcesses():
                if p.th32ParentProcessID == parentPid:
                    yield p.th32ProcessID

        def genProcesses(self):

            CreateToolhelp32Snapshot = ctypes.windll.kernel32.CreateToolhelp32Snapshot
            Process32First = ctypes.windll.kernel32.Process32First
            Process32Next = ctypes.windll.kernel32.Process32Next
            CloseHandle = ctypes.windll.kernel32.CloseHandle

            hProcessSnap = CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
            pe32 = PROCESSENTRY32()
            pe32.dwSize = ctypes.sizeof(PROCESSENTRY32)
            if Process32First(hProcessSnap, ctypes.byref(pe32)) == win32con.FALSE:
                print("Failed getting first process.")
                return

            while True:
                yield pe32
                if Process32Next(hProcessSnap, ctypes.byref(pe32)) == win32con.FALSE:
                    break

            CloseHandle(hProcessSnap)

        def closeApp(self, hProcess, title):
            """
            Close Application by window title
            """

            try:
                win32gui.EnumWindows(FileWriterLauncherGui.enumCallback, title)

                if proc is not None:
                    win32event.WaitForSingleObject(hProcess, 5 * 1000)
                    win32api.CloseHandle(hProcess)

                    for pid in self.genChildProcesses(proc):
                        try:
                            handle = win32api.OpenProcess(1, False, pid)
                            win32process.TerminateProcess(handle, -1)
                            win32api.CloseHandle(handle)
                        except:
                            pass

            except:
                pass


    class DebuggerLauncherGui(Publisher):
        """
        Writes a file to disk and then launches a program.  After
        some defined amount of time we will try and close the GUI
        application by sending WM_CLOSE than kill it.

        To use, first use this publisher like the FileWriter
        stream publisher.  Close, than call a program (or two).
        """

        def __init__(self, windowname, waitTime=3):
            Publisher.__init__(self)
            self.waitTime = float(waitTime)
            self._windowName = windowname

            if sys.platform != 'win32':
                raise PeachException("Error, publisher DebuggerLauncherGui not supported on non-Windows platforms.")

        def call(self, method, args):

            Engine.context.agent.OnPublisherCall(method)

            methodRunning = method + "_isrunning"
            for i in range(int(self.waitTime / 0.25)):
                ret = Engine.context.agent.OnPublisherCall(methodRunning)
                if not ret:
                    # Process exited already
                    break

                time.sleep(0.25)

            self.closeApp(None, self._windowName)

        @staticmethod
        def enumCallback(hwnd, windowName):
            """
            Will get called by win32gui.EnumWindows, once for each
            top level application window.
            """

            try:
                # Get window title
                title = win32gui.GetWindowText(hwnd)

                # Is this our guy?
                if title.find(windowName) == -1:
                    win32gui.EnumChildWindows(hwnd, FileWriterLauncherGui.enumChildCallback, windowName)
                    return

                # Send WM_CLOSE message
                win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
            except:
                pass

        @staticmethod
        def enumChildCallback(hwnd, windowName):
            """
            Will get called by win32gui.EnumWindows, once for each
            top level application window.
            """

            try:

                # Get window title
                title = win32gui.GetWindowText(hwnd)

                # Is this our guy?
                if title.find(windowName) == -1:
                    return

                # Send WM_CLOSE message
                win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)

            except:
                pass
            #print sys.exc_info()

        def genChildProcesses(self, proc):
            parentPid = proc.pid

            for p in self.genProcesses():
                if p.th32ParentProcessID == parentPid:
                    yield p.th32ProcessID

        def genProcesses(self):

            CreateToolhelp32Snapshot = ctypes.windll.kernel32.CreateToolhelp32Snapshot
            Process32First = ctypes.windll.kernel32.Process32First
            Process32Next = ctypes.windll.kernel32.Process32Next
            CloseHandle = ctypes.windll.kernel32.CloseHandle

            hProcessSnap = CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
            pe32 = PROCESSENTRY32()
            pe32.dwSize = ctypes.sizeof(PROCESSENTRY32)
            if Process32First(hProcessSnap, ctypes.byref(pe32)) == win32con.FALSE:
                print(sys.stderr, "Failed getting first process.")
                return

            while True:
                yield pe32
                if Process32Next(hProcessSnap, ctypes.byref(pe32)) == win32con.FALSE:
                    break

            CloseHandle(hProcessSnap)

        def closeApp(self, hProcess, title):
            """
            Close Application by window title
            """

            try:
                win32gui.EnumWindows(FileWriterLauncherGui.enumCallback, title)

                if hProcess is not None:
                    win32event.WaitForSingleObject(hProcess, 5 * 1000)
                    win32api.CloseHandle(hProcess)

                    for pid in self.genChildProcesses(proc):
                        try:
                            handle = win32api.OpenProcess(1, False, pid)
                            win32process.TerminateProcess(handle, -1)
                            win32api.CloseHandle(handle)
                        except:
                            pass

            except:
                pass

except:
    pass
