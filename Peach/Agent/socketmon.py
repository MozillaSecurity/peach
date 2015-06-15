# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
import sys
import time
import socket

sys.path.append("..")
sys.path.append("../..")

from Peach.agent import Monitor
from twisted.internet import reactor, protocol
from threading import Thread

g_socketData = None
g_faultDetected = False
g_stopReactor = False

# TODO: Port this over to use ThreadedSelectReactor
# http://twistedmatrix.com/documents/current/api/twisted.internet._threadedselect.ThreadedSelectReactor.html

class SocketMonitor(Monitor):

    def __init__(self, args):
        """
        Constructor.  Arguments are supplied via the Peach XML file.

        @type	args: Dictionary
        @param	args: Dictionary of parameters
        """
        try:
            self._name = "Socket Monitor"
            self._ip = ""
            self._port = ""
            self._protocol = ""
            self._thread = None
            self._internalError = False
            self._stopOnFault = False
            # Report an error if no MemoryLimit and/or neither pid nor
            # processName is defined.
            while 1:
                if args.has_key('IP'):
                    self._ip = str(args["IP"]).replace("'''", "")
                else:
                    print("Socket Monitor: No IP specified, using using "
                          "127.0.0.1")
                    self._ip = "127.0.0.1"
                if args.has_key('Port'):
                    self._port = int(args['Port'].replace("'''", ""))
                    print("Socket Monitor: Listening on Port: {}"
                          .format(self._port))
                else:
                    print("Socket Monitor: No Port specified, using 80")
                    self._port = "8002"
                if args.has_key('Protocol'):
                    self._protocol = args['Protocol'].replace("'''", "")
                    print("Socket Monitor: Protocol = %s" % self._protocol)
                else:
                    print("Socket Monitor: No Protocol specified, using TCP")
                    self._protocol = "tcp"
                break
        except:
            self._internalError = True
            print("Socket Monitor: Caught Exception Parsing Arguments")
            raise

    def OnTestStarting(self):
        """
        Called right before start of test case or variation.
        """
        global g_faultDetected
        global g_socketData
        # fire up twisted if it hasn't been already
        if self._thread is None:
            self._thread = ReactorThread(self._ip, self._port, self._protocol)
            self._thread.start()
        g_socketData = None
        g_faultDetected = False
        return

    def GetMonitorData(self):
        """
        Get any monitored data from a test case.
        """
        global g_socketData
        return {'SocketData.txt': str(g_socketData)}

    def DetectedFault(self):
        """
        Check if a fault was detected.
        """
        global g_faultDetected
        return g_faultDetected

    def OnShutdown(self):
        """
        Called when Agent is shutting down, typically at end of a test run or
        when a Stop-Run occurs.
        """
        global g_stopReactor
        g_stopReactor = True
        s = None
        # hack to stop reactor
        if self._protocol.lower() == "tcp":
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        else:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect((self._ip, int(self._port)))
        s.close()

    def StopRun(self):
        """
        Return True to force test run to fail. This should return True if an
        unrecoverable error occurs.
        """
        return self._internalError


class ReactorThread(Thread):
    def __init__(self, ip, port, protocol):
        Thread.__init__(self)
        self._ip = ip
        self._port = port
        self._protocol = protocol
        self._factory = None

    def run(self):
        self._factory = protocol.ServerFactory()
        self._factory.protocol = Listener
        if self._protocol.lower() == "tcp":
            reactor.listenTCP(int(self._port), self._factory)
        else:
            reactor.listenUDP(int(self._port), self._factory)
        reactor.run(installSignalHandlers=0)


class Listener(protocol.Protocol):
    def connectionMade(self):
        global g_stopReactor
        global g_socketData
        # hack until ThreadedSelectReactor is implemented
        if g_stopReactor:
            print("Socket Monitor: Stopping Reactor")
            reactor.stop()
        else:
            host = self.transport.getHost()
            g_socketData = host.host + ":" + str(host.port)
            global g_faultDetected
            g_faultDetected = True


if __name__ == "__main__":
    d = {
        "IP": "127.0.0.1",
        "Port": "8002",
        "Protocol": "tcp"
    }
    a = SocketMonitor(d)
    a.OnTestStarting()
    while True:
        a.OnTestStarting()
        time.sleep(2)
        print(a.DetectedFault())
        a.OnTestFinished()
    a.OnShutdown()
