# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
import os
import re
import sys
import time
import uuid
import socket
import atexit
import logging
import subprocess
try:
    from urlparse import urlparse
except ImportError as e:
    from urllib.parse import urlparse
try:
    import win32process
    import win32con
except ImportError as e:
    pass
try:
    import cPickle as pickle
except ImportError as e:
    import pickle
try:
    from xmlrpclib import ServerProxy
    from xmlrpclib import Error
except ImportError as e:
    from xmlrpc.client import ServerProxy
    from xmlrpc.client import Error

from Peach import xmlrpc
from twisted.web import server

from Peach.Publishers import *
from Peach.Engine.common import *
from Peach.Utilities.common import *


agentProcesses = []


@atexit.register
def cleanup_agent():
    if agentProcesses and len(agentProcesses) > 0:
        logging.debug("Killing agents.")
        for process in agentProcesses:
            process.terminate()
            process.kill()


def Debug(msg):
    #print msg
    pass


def MonitorDebug(monitor, msg):
    print("Monitor[%s]: %s" % (monitor, highlight.info(msg)))


def PeachStr(s):
    """Our implementation of str() which does not convert None to 'None'."""
    return None if s is None else str(s)


class Monitor(object):
    """
    Extend from this to implement a Monitor.
    Monitors are run by an Agent and must operate in an async manner.
    Any blocking tasks must be performed in another thread.

    Agent: onTestStarting()
    Agent: onTestFinished()
    Agent: redoTest()
    Agent: Sending redoTest result [False]
    Agent: detectFault()
    Agent: Detected fault!
    Agent: Sending detectFault result [True]
    Agent: getMonitorData()
    Agent: onFault()
    Agent: stopRun()
    Agent: onShutdown()
    """

    def __init__(self, args):
        """
        Arguments are supplied via the Peach XML file.

        @type	args: Dictionary
        @param	args: Dictionary of parameters
        """
        self._name = None

    def OnTestStarting(self):
        """Called right before start of test case or variation."""
        pass

    def OnTestFinished(self):
        """Called right after a test case or variation."""
        pass

    def GetMonitorData(self):
        """Get any monitored data from a test case."""
        return None

    def RedoTest(self):
        """Should the current test be re-performed."""
        return False

    def DetectedFault(self):
        """Check if a fault was detected."""
        return False

    def OnFault(self):
        """Called when a fault was detected."""
        pass

    def OnShutdown(self):
        """Called when Agent is shutting down, typically at end of a test run or when a Stop-Run occurs."""
        pass

    def StopRun(self):
        """Return True to force test run to fail. This should return True if an unrecoverable error occurs."""
        return False

    def PublisherCall(self, method):
        """Called when a call action is being performed.
        Call actions are used to launch programs, this gives the monitor a chance to determine if it should be
        running the program under a debugger instead. Note: This is a bit of a hack to get this working.
        """
        pass

# Need to define Monitor before we do this include!
from Peach.Agent import *


class _MsgType(object):
    """Type of message"""
    ClientHello = 2  #: Sent by fuzzer, will include password (optional)
    AgentHello = 1  #: Sent if password okay, else drop
    ClientDisconnect = 5
    AgentDisconnect = 6
    AgentReady = 7
    Ack = 17  #: Ack that we completed and finished
    Nack = 18  #: Ack that we did not complete, error occurred
    #: exception in msg.exception
    ## Monitors
    GetMonitorData = 11
    DetectFault = 8
    OnFault = 9
    OnShutdown = 10  #: Test completed, shutting down
    OnTestStarting = 13  #: On Test Case Starting
    OnTestFinished = 14  #: On Test Case Finished
    StopRun = 20
    RedoTest = 30  #: Should we re-perform the current test?
    StartMonitor = 15  #: Startup a monitor
    # Expect a msg.monitorName: str, msg.monitorClass: str and msg.params: dictionary
    StopMonitor = 16  #: Stop a monitor
    ## Publishers
    PublisherStart = 21
    PublisherStop = 22
    PublisherAccept = 23
    PublisherConnect = 24
    PublisherClose = 25
    PublisherCall = 26  #: Notify that we are running a call action
    PublisherProperty = 27  #: Notify that we are running a property action
    PublisherSend = 28
    PublisherReceive = 29


class _Msg(object):
    """This is a message holder that is serialized and sent over the named pipe."""

    def __init__(self, id, type, results=None):
        self.id = id
        self.type = type
        self.results = results
        self.stopRun = False
        self.password = False
        self.pythonPaths = None
        self.imports = None


class Agent(object):
    """A remote or local Agent that listens on a named pipe.
    Each agent can only be connected to by a single Peach Fuzzer.
    """

    def __init__(self, password=None, port=9000):
        """
        Creates and Agent instance and attempts to connect to the AgentMaster.
        If connection works the Client Hello message is sent.

        @type	password: string
        @param	password: Password to use
        """
        from twisted.internet import reactor

        agent = AgentXmlRpc()
        agent._password = password
        agent._monitors = []
        agent._publishers = {}
        agent._id = None
        reactor.listenTCP(port, server.Site(agent))
        if agent._password is not None:
            print("\n[Agent] Listening on [%s] with password [%s]\n" % (port, agent._password))
        else:
            print("\n[Agent] Listening on [%s] with no password\n" % port)
        reactor.run()


class AgentXmlRpc(xmlrpc.XMLRPC):
    def xmlrpc_clientHello(self, msg):
        msg = pickle.loads(msg)
        if msg.password != self._password:
            print("Agent: Incorrect password on clientHello [%s]" % msg.password)
            return pickle.dumps(_Msg(None, _MsgType.Nack))
        if msg.type != _MsgType.ClientHello:
            return pickle.dumps(_Msg(None, _MsgType.Nack))
        print("Agent: clientHello()")
        if self._id is not None:
            self._stopAllMonitors()
        self._id = str(uuid.uuid1())
        print("Agent: Session ID: ", self._id)
        # Handle any PythonPath or Imports
        if msg.pythonPaths is not None:
            for p in msg.pythonPaths:
                sys.path.append(p['name'])
        if msg.imports is not None:
            for i in msg.imports:
                self._handleImport(i)
        print("Agent: clientHello() all done")
        return pickle.dumps(_Msg(self._id, _MsgType.AgentHello))

    def GetClassesInModule(self, module):
        """Return array of class names in module."""
        classes = []
        for item in dir(module):
            i = getattr(module, item)
            if isinstance(i, type) and item[0] != '_':
                classes.append(item)
        return classes

    def _handleImport(self, i):
        importStr = i['import']
        if i['from'] is not None and len(i['from']) > 0:
            fromStr = i['from']
            if importStr == "*":
                module = __import__(PeachStr(fromStr), globals(), locals(), [PeachStr(importStr)], -1)
                try:
                    # If we are a module with other modules in us then we have an __all__
                    for item in module.__all__:
                        globals()[item] = getattr(module, item)
                except Exception as e:
                    # Else we just have some classes in us with no __all__
                    for item in self.GetClassesInModule(module):
                        globals()[item] = getattr(module, item)
            else:
                module = __import__(PeachStr(fromStr), globals(), locals(), [PeachStr(importStr)], -1)
                for item in importStr.split(','):
                    item = item.strip()
                    globals()[item] = getattr(module, item)
        else:
            globals()[importStr] = __import__(PeachStr(importStr), globals(), locals(), [], -1)

    def xmlrpc_clientDisconnect(self, msg):
        msg = pickle.loads(msg)
        if self._id is None or msg.id != self._id:
            return pickle.dumps(_Msg(None, _MsgType.Nack))
        if msg.type != _MsgType.ClientDisconnect:
            return pickle.dumps(_Msg(None, _MsgType.Nack))
        print("Agent: clientDisconnect()")
        self._stopAllMonitors()
        return pickle.dumps(_Msg(None, _MsgType.Ack))

    def xmlrpc_stopRun(self, msg):
        msg = pickle.loads(msg)
        if self._id is None or msg.id != self._id:
            return pickle.dumps(_Msg(None, _MsgType.Nack))
        if msg.type != _MsgType.StopRun:
            return pickle.dumps(_Msg(None, _MsgType.Nack))
        print("Agent: stopRun()")
        msg = _Msg(None, _MsgType.Ack)
        msg.results = False
        for m in self._monitors:
            if m.StopRun():
                print("Agent: Stop run request!")
                msg.results = True
        return pickle.dumps(msg)

    def xmlrpc_detectFault(self, msg):
        msg = pickle.loads(msg)
        if self._id is None or msg.id != self._id:
            return pickle.dumps(_Msg(None, _MsgType.Nack))
        if msg.type != _MsgType.DetectFault:
            return pickle.dumps(_Msg(None, _MsgType.Nack))
        print("Agent: detectFault()")
        msg = _Msg(None, _MsgType.Ack)
        msg.results = False
        for m in self._monitors:
            if m.DetectedFault():
                print("Agent: Detected fault!")
                msg.results = True
        print("Agent: Sending detectFault result [%s]" % repr(msg.results))
        return pickle.dumps(msg)

    def xmlrpc_redoTest(self, msg):
        msg = pickle.loads(msg)
        if self._id is None or msg.id != self._id:
            return pickle.dumps(_Msg(None, _MsgType.Nack))
        if msg.type != _MsgType.RedoTest:
            return pickle.dumps(_Msg(None, _MsgType.Nack))
        print("Agent: redoTest()")
        msg = _Msg(None, _MsgType.Ack)
        msg.results = False
        for m in self._monitors:
            if m.RedoTest():
                msg.results = True
        print("Agent: Sending redoTest result [%s]" % repr(msg.results))
        return pickle.dumps(msg)

    def xmlrpc_getMonitorData(self, msg):
        msg = pickle.loads(msg)
        if self._id is None or msg.id != self._id:
            return pickle.dumps(_Msg(None, _MsgType.Nack))
        if msg.type != _MsgType.GetMonitorData:
            return pickle.dumps(_Msg(None, _MsgType.Nack))
        print("Agent: getMonitorData()")
        msg = _Msg(None, _MsgType.Ack)
        msg.results = []
        for m in self._monitors:
            try:
                data = m.GetMonitorData()
                if data is not None:
                    msg.results.append(data)
            except Exception as e:
                print("Agent: getMonitorData: Failrue getting data from:", m.monitorName)
                raise
        return pickle.dumps(msg)

    def xmlrpc_onFault(self, msg):
        msg = pickle.loads(msg)
        if self._id is None or msg.id != self._id:
            return pickle.dumps(_Msg(None, _MsgType.Nack))
        if msg.type != _MsgType.OnFault:
            return pickle.dumps(_Msg(None, _MsgType.Nack))
        print("Agent: onFault()")
        for m in self._monitors:
            m.OnFault()
        return pickle.dumps(_Msg(None, _MsgType.Ack))

    def xmlrpc_onTestFinished(self, msg):
        msg = pickle.loads(msg)
        if self._id is None or msg.id != self._id:
            return pickle.dumps(_Msg(None, _MsgType.Nack))
        if msg.type != _MsgType.OnTestFinished:
            return pickle.dumps(_Msg(None, _MsgType.Nack))
        print("Agent: onTestFinished()")
        for m in self._monitors:
            m.OnTestFinished()
        return pickle.dumps(_Msg(None, _MsgType.Ack))

    def xmlrpc_onTestStarting(self, msg):
        msg = pickle.loads(msg)
        if self._id is None or msg.id != self._id:
            return pickle.dumps(_Msg(None, _MsgType.Nack))
        if msg.type != _MsgType.OnTestStarting:
            return pickle.dumps(_Msg(None, _MsgType.Nack))
        print("Agent: onTestStarting()")
        for m in self._monitors:
            m.OnTestStarting()
        return pickle.dumps(_Msg(None, _MsgType.Ack))

    def xmlrpc_onPublisherCall(self, msg):
        msg = pickle.loads(msg)
        if self._id is None or msg.id != self._id:
            return pickle.dumps(_Msg(None, _MsgType.Nack))
        if msg.type != _MsgType.PublisherCall:
            return pickle.dumps(_Msg(None, _MsgType.Nack))
        print("Agent: onPublisherCall():", msg.method)
        outRet = None
        for m in self._monitors:
            ret = m.PublisherCall(msg.method)
            if ret is not None:
                outRet = ret
        return pickle.dumps(_Msg(None, _MsgType.Ack, outRet))

    def _stopAllMonitors(self):
        """Stop all monitors. Part of resetting our connection."""
        for m in self._monitors:
            m.OnShutdown()
        self._monitors = []

    def xmlrpc_onShutdown(self, msg):
        msg = pickle.loads(msg)
        if self._id is None or msg.id != self._id:
            return pickle.dumps(_Msg(None, _MsgType.Nack))
        if msg.type != _MsgType.OnShutdown:
            return pickle.dumps(_Msg(None, _MsgType.Nack))
        print("Agent: onShutdown()")
        self._stopAllMonitors()
        return pickle.dumps(_Msg(None, _MsgType.Ack))

    def xmlrpc_stopMonitor(self, msg):
        msg = pickle.loads(msg)
        if self._id is None or msg.id != self._id:
            return pickle.dumps(_Msg(None, _MsgType.Nack))
        if msg.type != _MsgType.StopMonitor:
            return pickle.dumps(_Msg(None, _MsgType.Nack))
        print("Agent: stopMonitor(%s)" % msg.monitorName)
        for i in range(len(self._monitors)):
            m = self._monitors[i]
            if m._name == msg.monitorName:
                try:
                    m.OnShutdown()
                except Exception as e:
                    pass
                self._monitors.remove(m)
                break
        return pickle.dumps(_Msg(None, _MsgType.Ack))

    def xmlrpc_startMonitor(self, msg):
        msg = pickle.loads(msg)
        if self._id is None or msg.id != self._id:
            return pickle.dumps(_Msg(None, _MsgType.Nack))
        if msg.type != _MsgType.StartMonitor:
            return pickle.dumps(_Msg(None, _MsgType.Nack))
        print("Agent: startMonitor(%s)" % msg.monitorName)
        try:
            code = msg.monitorClass + "(msg.params)"
            print("code:", code)
            monitor = eval(code)
            if monitor is None:
                print("Agent: Unable to create Monitor [%s]" % msg.monitorClass)
                return pickle.dumps(_Msg(self._id, _MsgType.Nack, "Unable to create Monitor [%s]" % msg.monitorClass))
            monitor.monitorName = msg.monitorName
            self._monitors.append(monitor)
            print("Agent: Sending Ack")
            return pickle.dumps(_Msg(None, _MsgType.Ack))
        except Exception as e:
            print("Agent: Unable to create Monitor [%s], exception occured." % msg.monitorClass)
            raise

    ## Publishers ######################################################

    def xmlrpc_publisherInitialize(self, id, name, cls, *args):
        if self._id is None or id != self._id:
            print("xmlrpc_publisherInitialize: Can't validate clients session id")
            return -1
        print("Agent: xmlrpc_publisherInitialize(%s, %s)" % (name, cls))
        try:
            code = cls + "("
            for cnt in range(len(args[0])):
                code += "args[0][%d]," % cnt
            code = code[:-1] + ")"
            print("Agent: Code: %s" % code)
            publisher = eval(code)
            if publisher is None:
                print("Agent: Unable to create Publisher [%s]" % cls)
                return -2
            publisher.publisherName = name
            self._publishers[name] = publisher
            print("Agent: Publisher created okay!")
            return 0
        except Exception as e:
            print("Agent: Unable to create Publisher [%s], exception occurred." % cls)
            return -2

    def xmlrpc_publisherStart(self, id, name):
        if self._id is None or id != self._id:
            print("xmlrpc_publisherStart: Can't validate clients session id")
            return -1
        if name not in self._publishers:
            return -2
        self._publishers[name].start()
        return 0

    def xmlrpc_publisherStop(self, id, name):
        if self._id is None or id != self._id:
            print("xmlrpc_publisherStop: Can't validate clients session id")
            return -1
        if name not in self._publishers:
            return -2
        self._publishers[name].stop()
        return 0

    def xmlrpc_publisherAccept(self, id, name):
        if self._id is None or id != self._id:
            print("xmlrpc_publisherAccept: Can't validate clients session id")
            return -1
        if name not in self._publishers:
            return -2
        self._publishers[name].accept()
        return 0

    def xmlrpc_publisherConnect(self, id, name):
        if self._id is None or id != self._id:
            print("xmlrpc_publisherConnect: Can't validate clients session id")
            return -1
        if name not in self._publishers:
            return -2
        self._publishers[name].connect()
        return 0

    def xmlrpc_publisherClose(self, id, name):
        if self._id is None or id != self._id:
            print("xmlrpc_publisherClose: Can't validate clients session id")
            return -1
        if name not in self._publishers:
            return -2
        self._publishers[name].close()
        return 0

    def xmlrpc_publisherCall(self, id, name, method, args):
        if self._id is None or id != self._id:
            print("xmlrpc_publisherCall: Can't validate clients session id")
            return -1
        if name not in self._publishers:
            return -2
        args = pickle.loads(args)
        ret = self._publishers[name].call(method, args)
        if ret is None:
            return 0
        return ret

    def xmlrpc_publisherProperty(self, id, name, property, value):
        if self._id is None or id != self._id:
            print("xmlrpc_publisherProperty: Can't validate clients session id")
            return -1
        if name not in self._publishers:
            return -2
        value = pickle.loads(value)
        ret = self._publishers[name].property(property, value)
        if ret is None:
            return 0
        return ret

    def xmlrpc_publisherSend(self, id, name, data):
        if self._id is None or id != self._id:
            print("xmlrpc_publisherSend: Can't validate clients session id")
            return -1
        if name not in self._publishers:
            return -2
        # TODO: ??
        value = pickle.loads(data)
        ret = self._publishers[name].send(data)
        if ret is None:
            return 0
        return ret

    def xmlrpc_publisherReceive(self, id, name, size):
        if self._id is None or id != self._id:
            print("xmlrpc_publisherReceive: Can't validate clients session id")
            return -1
        if name not in self._publishers:
            return -2
        return self._publishers[name].receive(size)


class AgentClient(object):
    """An Agent client. Clients connect and send/recieve messages with a single remote Agent."""

    def __init__(self, agentUri, password, pythonPaths=None, imports=None, configs=None):
        """
        Creates and Agent instance and attempts to connect to the AgentMaster.
        If connection works the Client Hello message is sent.

        @type	agentUri: string
        @param	agentUri: Url of agent
        @type	password: string
        @param	password: [optional] Password to authenticate to agent.  Warning: CLEAR-TEXT!!
        @type	pythonPaths: list
        @param	pythonPaths: List of paths we should configure on the remote agent
        @type	imports: list
        @param	imports: list of imports that should be performed on the remote agent
        """

        self._pythonPaths = pythonPaths
        self._imports = imports
        self._password = password
        self._monitors = []
        self._id = None
        self._agent = None
        self._agentUri = agentUri

        agentUrl = urlparse(agentUri)
        agentPort = agentUrl.port
        agentHostname = agentUrl.hostname

        # This is nicer, but does not work on darwin:
        #if socket.getfqdn(agentHostname) in ('localhost', socket.gethostname()):
        if agentHostname in ("127.0.0.1", "0.0.0.0", "localhost", socket.gethostname()):
            peachPath = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            macros = []
            if configs:
                macros.append("-macros")
                for kv in configs.iteritems():
                    macros.append("=".join(kv))
            if sys.platform == "win32":
                agentProcess = subprocess.call(['start',
                                                "Peach Agent",
                                                sys.executable,
                                                "%s\peach.py" % peachPath,
                                                "-agent", str(agentPort), password] + macros)
                agentProcesses.append(agentProcess)
            elif sys.platform == "darwin":
                if not self.isPeachRunning(agentPort):
                    peachAgentCommand = [sys.executable, 'peach.py', '-agent', str(agentPort), password] + macros
                    if configs and getBooleanAttribute(configs, "HideAgentWindow"):
                        logging.warning("Agent window will not be visible!")
                        agentProcess = subprocess.Popen(peachAgentCommand,
                                                        cwd=peachPath,
                                                        stdout=open('/dev/null', 'w'))
                        agentProcesses.append(agentProcess)
                    else:
                        logging.info("Opening agent in new terminal.")
                        osxTerminalCommand = \
                            """osascript -e 'tell application "Terminal" to do script "cd %s; %s; exit"'""" % \
                            (peachPath, re.sub(r"""(['"])""", r"\\\1", subprocess.list2cmdline(peachAgentCommand)))
                        agentProcess = subprocess.Popen(osxTerminalCommand,
                                                        stdout=subprocess.PIPE,
                                                        shell=True)
                        agentProcesses.append(agentProcess)
            elif sys.platform == "linux2":
                if not self.isPeachRunning(agentPort):
                    logging.info("Opening agent in new terminal.")
                    peachAgentCommand = [sys.executable, "peach.py", "-agent", str(agentPort), password] + macros
                    if "COLORTERM" in os.environ and 'gnome-terminal' in os.environ["COLORTERM"]:
                        linuxTerminalCommands = ['gnome-terminal', '-x'] + peachAgentCommand
                    else:
                        linuxTerminalCommands = ['xterm', '-hold']
                        if configs and getBooleanAttribute(configs, "AgentTerminalLogging"):
                            linuxTerminalCommands += ["-l"]
                        linuxTerminalCommands += ['-e'] + peachAgentCommand
                    agentProcess = subprocess.Popen(linuxTerminalCommands,
                                                    cwd=peachPath,
                                                    stdout=subprocess.PIPE)
                    agentProcesses.append(agentProcess)
            else:
                raise PeachException("We only support auto starting agents on Windows, OSX and Linux. "
                                     "Please configure all agents with location URIs and launch any Agent manually.")

        # Connect to remote agent
        try:
            m = re.search(r"://([^/]*)", agentUri)
            self._name = m.group(1)
        except:
            raise PeachException("Please make sure your agent location string is a valid http URL.")
        self.Connect()

    def isPeachRunning(self, agentPort):
        running = False
        if sys.platform == "darwin" or sys.platform == "linux2":
            agentList = subprocess.check_output(["ps x | grep peach.py"], shell=True)
            for agent in agentList.splitlines():
                try:
                    port = re.findall("peach\.py \-agent (\d+)", agent)[0]
                except IndexError:
                    continue
                if int(port) == agentPort:
                    running = True
        if running:
            logging.warning("An agent is already running on port %d" % agentPort)
        return running

    def LaunchWin32Process(self, command):
        try:
            StartupInfo = win32process.STARTUPINFO()
            StartupInfo.dwFlags = win32process.STARTF_USESHOWWINDOW
            StartupInfo.wShowWindow = win32con.SW_NORMAL
            win32process.CreateProcess(
                None,
                command,
                None,
                None,
                0,
                win32process.NORMAL_PRIORITY_CLASS,
                None,
                None,
                StartupInfo)
        except Exception as e:
            print(sys.exc_info())
            print("Exception in LaunchWin32Process")
            pass

    def Connect(self):
        """Connect to agent. Will retry the connection 10 times before giving up."""
        for i in range(20):
            try:
                self._agent = ServerProxy(self._agentUri)
                msg = _Msg(None, _MsgType.ClientHello, self._name)
                msg.password = self._password
                msg.pythonPaths = self._pythonPaths
                msg.imports = self._imports
                msg = pickle.loads(self._agent.clientHello(pickle.dumps(msg)))
                if msg.type != _MsgType.AgentHello:
                    raise PeachException("Error connecting to remote agent %s, invalid response." % self._name)
                self._id = msg.id
                return
            except Exception as e:
                if i == 19:
                    raise
            time.sleep(1)
            logging.warning("Agent connection failed, retrying.")

    def Reconnect(self):
        """Reconnect to remote agent"""
        try:
            self.Connect()
            for m in self._monitors:
                self.StartMonitor(m[0], m[1], m[2], True)
        except Exception as e:
            raise PeachException("Unable to reconnect to Agent %s." % self._name)

    def StartMonitor(self, name, classStr, params, restarting=False):
        Debug("> StartMonitor")
        msg = _Msg(self._id, _MsgType.StartMonitor)
        msg.monitorName = name
        msg.monitorClass = classStr
        msg.params = params
        msg = pickle.loads(self._agent.startMonitor(pickle.dumps(msg)))
        if msg.type != _MsgType.Ack:
            raise PeachException("Lost connection to Agent %s during StartMonitor call." % self._name)
        if not restarting:
            self._monitors.append([name, classStr, params])
        Debug("< StartMonitor")

    def StopMonitor(self, name):
        Debug("> StopMonitor")
        msg = _Msg(self._id, _MsgType.StopMonitor)
        msg.monitorName = name
        msg = pickle.loads(self._agent.stopMonitor(pickle.dumps(msg)))
        if msg.type != _MsgType.Ack:
            raise PeachException("Lost connection to Agent %s during StopMonitor call." % self._name)
        for m in self._monitors:
            if m[0] == name:
                self._monitors.remove(m)
        Debug("< StopMonitor")

    def OnTestStarting(self):
        """Called right before start of test."""
        Debug("> OnTestStarting")
        msg = _Msg(self._id, _MsgType.OnTestStarting)
        try:
            msg = pickle.loads(self._agent.onTestStarting(pickle.dumps(msg)))
        except Exception as e:
            self.Reconnect()
            raise RedoTestException("Communication error with Agent %s" % self._name)
        if msg.type != _MsgType.Ack:
            raise PeachException("Lost connection to Agent %s during OnTestStarting call." % self._name)
        Debug("< OnTestStarting")

    def OnPublisherCall(self, method):
        Debug("> OnPublisherCall")
        msg = _Msg(self._id, _MsgType.PublisherCall)
        msg.method = method
        try:
            msg = pickle.loads(self._agent.onPublisherCall(pickle.dumps(msg)))
        except Exception as e:
            self.Reconnect()
            raise RedoTestException("Communication error with Agent %s" % self._name)
        if msg.type != _MsgType.Ack:
            raise PeachException("Lost connection to Agent %s during OnPublisherCall call." % self._name)
        Debug("< OnPublisherCall")
        return msg.results

    def OnTestFinished(self):
        """Called right after a test."""
        Debug("> OnTestFinished")
        msg = _Msg(self._id, _MsgType.OnTestFinished)
        try:
            msg = pickle.loads(self._agent.onTestFinished(pickle.dumps(msg)))
        except Exception as e:
            self.Reconnect()
            raise RedoTestException("Communication error with Agent %s" % self._name)
        if msg.type != _MsgType.Ack:
            raise PeachException("Lost connection to Agent %s during OnTestFinished call." % self._name)
        Debug("< OnTestFinished")

    def GetMonitorData(self):
        """Get any monitored data."""
        Debug("> GetMonitorData")
        msg = _Msg(self._id, _MsgType.GetMonitorData)
        try:
            msg = pickle.loads(self._agent.getMonitorData(pickle.dumps(msg)))
        except Exception as e:
            self.Reconnect()
            raise RedoTestException("Communication error with Agent %s" % self._name)
        if msg.type != _MsgType.Ack:
            raise PeachException("Lost connection to Agent %s during GetMonitorData call." % self._name)
        Debug("< GetMonitorData")
        return msg.results

    def RedoTest(self):
        """Should we repeat current test."""
        Debug("> RedoTest")
        try:
            msg = _Msg(self._id, _MsgType.RedoTest)
            msg = pickle.loads(self._agent.redoTest(pickle.dumps(msg)))
        except Exception as e:
            self.Reconnect()
            raise RedoTestException("Communication error with Agent %s" % self._name)
        if msg.type != _MsgType.Ack:
            raise PeachException("Lost connection to Agent %s during RedoTest call." % self._name)
        Debug("< RedoTest")

        return msg.results

    def DetectedFault(self):
        """Check if a fault was detected."""
        Debug("> DetectedFault")
        try:
            msg = _Msg(self._id, _MsgType.DetectFault)
            msg = pickle.loads(self._agent.detectFault(pickle.dumps(msg)))
        except Exception as e:
            self.Reconnect()
            raise RedoTestException("Communication error with Agent %s" % self._name)
        if msg.type != _MsgType.Ack:
            raise PeachException("Lost connection to Agent %s during GetMonitorData call." % self._name)
        Debug("< DetectedFault")
        return msg.results

    def OnFault(self):
        """Called when a fault was detected."""
        Debug("> OnFault")
        try:
            msg = _Msg(self._id, _MsgType.OnFault)
            msg = pickle.loads(self._agent.onFault(pickle.dumps(msg)))
        except Exception as e:
            self.Reconnect()
            raise RedoTestException("Communication error with Agent %s" % self._name)
        if msg.type != _MsgType.Ack:
            raise PeachException("Lost connection to Agent %s during GetMonitorData call." % self._name)
        Debug("< OnFault")

    def OnShutdown(self):
        """Called when Agent is shutting down."""
        Debug("> OnShutdown")
        msg = _Msg(self._id, _MsgType.OnShutdown)
        self._agent.onShutdown(pickle.dumps(msg))
        Debug("< OnShutdown")

    def StopRun(self):
        """Return True to force test run to fail. This should return True if an unrecoverable error occurs."""
        Debug("> StopRun")
        try:
            msg = _Msg(self._id, _MsgType.StopRun)
            msg = pickle.loads(self._agent.stopRun(pickle.dumps(msg)))
        except Exception as e:
            self.Reconnect()
            raise RedoTestException("Communication error with Agent %s" % self._name)
        if msg.type != _MsgType.Ack:
            raise PeachException("Lost connection to Agent %s during GetMonitorData call." % self._name)
        Debug("< StopRun")
        return msg.results

    #  Publishers
    def PublisherInitialize(self, name, cls, args):
        ret = self._agent.publisherInitialize(self._id, name, cls, args)
        if ret is not None and ret < 0:
            raise Exception("That sucked")

    def PublisherStart(self, name):
        ret = self._agent.publisherStart(self._id, name)
        if ret < 0:
            raise Exception("That sucked")

    def PublisherStop(self, name):
        ret = self._agent.publisherStop(self._id, name)
        if ret < 0:
            raise Exception("That sucked")

    def PublisherAccept(self, name):
        ret = self._agent.publisherAccept(self._id, name)
        if ret < 0:
            raise Exception("That sucked")

    def PublisherConnect(self, name):
        ret = self._agent.publisherConnect(self._id, name)
        if ret < 0:
            raise Exception("That sucked")

    def PublisherClose(self, name):
        ret = self._agent.publisherClose(self._id, name)
        if ret < 0:
            raise Exception("That sucked")

    def PublisherCall(self, name, method, args):
        ret = self._agent.publisherCall(self._id, name, method, pickle.dumps(args))
        if ret < 0:
            raise Exception("That sucked")
        return ret

    def PublisherProperty(self, name, property, value=None):
        ret = self._agent.publisherProperty(self._id, name, property, pickle.dumps(value))
        if ret < 0:
            raise Exception("That sucked")
        return ret

    def PublisherSend(self, name, data):
        ret = self._agent.publisherSend(self._id, name, pickle.dumps(data))
        if ret < 0:
            raise Exception("That sucked")
        return ret

    def PublisherReceive(self, name, size=None):
        ret = self._agent.publisherReceive(self._id, name, size)
        if ret < 0:
            raise Exception("That sucked")
        return ret


class AgentPlexer(object):
    """Manages communication with one or more agent."""

    def __init__(self):
        self._agents = {}

    def __getitem__(self, key):
        return self._agents[key]

    def __setitem__(self, key, value):
        self._agents[key] = value

    def AddAgent(self, name, agentUri, password=None, pythonPath=None, imports=None, configs=None):
        #m = re.search(r"://([^:/]*)", agentUri)
        #name = m.group(1)
        agent = AgentClient(agentUri, password, pythonPath, imports, configs)
        self._agents[name] = agent
        return agent

    def OnTestStarting(self):
        """Called right before start of test."""
        for name in self._agents.keys():
            self._agents[name].OnTestStarting()

    def OnPublisherCall(self, method):
        ourRet = None
        for name in self._agents.keys():
            ret = self._agents[name].OnPublisherCall(method)
            if ret is not None:
                ourRet = ret
        return ourRet

    def OnTestFinished(self):
        """Called right after a test."""
        for name in self._agents.keys():
            self._agents[name].OnTestFinished()

    def GetMonitorData(self):
        """Get any monitored data."""
        ret = {}
        for name in self._agents.keys():
            arrayOfMonitorData = self._agents[name].GetMonitorData()
            for hashOfData in arrayOfMonitorData:
                for key in hashOfData.keys():
                    ret["%s_%s" % (name, key)] = hashOfData[key]
        return ret

    def RedoTest(self):
        """Check if a fault was detected."""
        ret = False
        for name in self._agents.keys():
            if self._agents[name].RedoTest():
                ret = True
        return ret

    def DetectedFault(self):
        """Check if a fault was detected."""
        ret = False
        for name in self._agents.keys():
            if self._agents[name].DetectedFault():
                ret = True
        return ret

    def OnFault(self):
        """Called when a fault was detected."""
        for name in self._agents.keys():
            self._agents[name].OnFault()

    def OnShutdown(self):
        """Called when Agent is shutting down."""
        for name in self._agents.keys():
            self._agents[name].OnShutdown()
        self._agents = {}

    def StopRun(self):
        """Return True to force test run to fail. This should return True if an unrecoverable error occurs."""
        ret = False
        for name in self._agents.keys():
            if self._agents[name].StopRun():
                ret = True
        return ret

    # Publishers
    def PublisherInitialize(self, name, cls, args):
        for name in self._agents.keys():
            self._agents[name].PublisherInitialize(name, cls, args)

    def PublisherStart(self, name):
        for name in self._agents.keys():
            self._agents[name].PublisherStart(name)

    def PublisherStop(self, name):
        for name in self._agents.keys():
            self._agents[name].PublisherStop(name)

    def PublisherAccept(self, name):
        for name in self._agents.keys():
            self._agents[name].PublisherAccept(name)

    def PublisherConnect(self, name):
        for name in self._agents.keys():
            self._agents[name].PublisherConnect(name)

    def PublisherClose(self, name):
        for name in self._agents.keys():
            self._agents[name].PublisherClose(name)

    def PublisherCall(self, name, method, args):
        for name in self._agents.keys():
            ret = self._agents[name].PublisherCall(name, method, args)
            if ret is not None:
                return ret

    def PublisherProperty(self, name, property, value=None):
        for name in self._agents.keys():
            ret = self._agents[name].PublisherProperty(name, property, value)
            if ret is not None:
                return ret

    def PublisherSend(self, name, data):
        for name in self._agents.keys():
            self._agents[name].PublisherSend(name, data)

    def PublisherReceive(self, name, size=None):
        for name in self._agents.keys():
            ret = self._agents[name].PublisherReceive(name, size)
            if ret is not None:
                return ret
