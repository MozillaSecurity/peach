# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
import sys
import threading
import os
import re
import socket

from Peach.agent import Monitor


try:
    def search_file(filename):
        """Find a file in a search path."""
        search_path = os.getenv("path")
        paths = search_path.split(os.path.pathsep)
        for path in paths:
            if os.path.exists(os.path.join(path, filename)):
                return True
        return False
    if sys.platform == 'win32' and search_file("wpcap.dll"):
        import pcap
    elif sys.platform != 'win32':
        import pcap
except:
    pass


class PingMonitor(Monitor):
    """
    This monitor will report a fault if it cannot ping the specified hostname.
    """

    def __init__(self, args):
        """
        Constructor. Arguments are supplied via the Peach XML file.

        @type	args: Dictionary
        @param	args: Dictionary of parameters
        """
        self.hostname = str(args['hostname']).replace("'''", "")
        self._name = "PingMonitor"

    def DetectedFault(self):
        """
        Check if a fault was detected.
        """
        if sys.platform == "win32":
            ping_send_command = "ping -n 2 "
            ping_send_command3 = "ping -n 3 "
            ping_reply_regex = r"Reply from \d+\.\d+\.\d+\.\d+: bytes="
        elif sys.platform == "linux2":
            ping_send_command = "ping -c 2 "
            ping_send_command3 = "ping -c 3 "
            ping_reply_regex = r"64 bytes from \d+\.\d+\.\d+\.\d+:"
        else:
            raise Exception("PingAgent running on unsupported platform "
                            "{}".format(sys.platform))
        pipe = os.popen(ping_send_command + self.hostname)
        buff = pipe.read()
        pipe.close()
        if re.compile(ping_reply_regex, re.M).search(buff) is not None:
            return False
        # If we didn't see a ping, let's try again with 3 pings just to make
        # sure.
        pipe = os.popen(ping_send_command3 + self.hostname)
        buff = pipe.read()
        pipe.close()
        if re.compile(ping_reply_regex, re.M).search(buff) is not None:
            return False
        return True


class UdpThread(threading.Thread):
    """
    Thread class for UdpMonitor
    """

    def __init__(self, host, port):
        threading.Thread.__init__(self)
        threading.Thread.setDaemon(self, True)
        self._host = host
        self._port = port
        self.stopEvent = threading.Event()
        self.stopEvent.clear()
        self.receivedPacket = threading.Event()
        self.receivedPacket.clear()
        self.packets = []

    def run(self):
        print("UdpThread(): Starting up UDP listener")
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind((self._host, int(self._port)))
        sock.setblocking(False)
        while not self.stopEvent.isSet():
            try:
                data = None
                data, addr = sock.recvfrom(65565)
                if data is not None and len(data) > 0:
                    print("UdpThread: Received packet from {}".format(addr))
                    self.packets.append(data)
                    self.receivedPacket.set()
            except socket.error:
                # Thrown if non-blocking and no packet available to receive.
                pass
        print("UdpThread: Shutting down")
        sock.close()


class UdpMonitor(Monitor):
    """
    Watches for incoming packets on a UDP port. If packet received will
    trigger fault saving data from packet.
    """

    def __init__(self, args):
        self.host = str(args['host']).replace("'''", "")
        self.port = str(args['port']).replace("'''", "")
        self._name = "UdpMonitor"
        self.thread = None
        self.thread = UdpThread(self.host, self.port)
        self.thread.start()

    def GetMonitorData(self):
        data = ""
        for d in self.thread.packets:
            data += d
        self.thread.packets = []
        self.thread.receivedPacket.clear()
        return {'UdpMonitor.txt': data}

    def OnShutdown(self):
        if self.thread is not None and self.thread.isAlive():
            self.thread.stopEvent.set()
            self.thread.join()
        self.thread = None

    def DetectedFault(self):
        return self.thread.receivedPacket.isSet()


class PcapThread(threading.Thread):
    def __init__(self, parent, device, filter, pcapFile):
        threading.Thread.__init__(self)
        threading.Thread.setDaemon(self, True)
        self._device = device
        self._filter = filter
        self._pcapFile = pcapFile
        self.stopEvent = threading.Event()
        self.stopEvent.clear()
        self.dumpClosed = threading.Event()
        self.dumpClosed.clear()
        self._packets = []

    def run(self):
        print("PcapThread(): Starting up pcap")
        pc = pcap.pcap(self._device)
        pc.dumpopen(self._pcapFile)
        if self._filter is not None:
            pc.setfilter(self._filter)
        pc.setnonblock()
        print("PcapThread(): Packet capture loop")
        while not self.stopEvent.isSet():
            # Do not remove print. For some reason packets are only captures
            # when it's there!!!
            print(".")
            pc.readpkts()
        pc.dumpclose()
        self.dumpClosed.set()


class PcapMonitor(Monitor):
    """
    Monitor network using pcap library.
    """

    def __init__(self, args):
        try:
            self.device = str(args['device']).replace("'''", "")
            if len(self.device) < 1:
                self.device = pcap.getDefaultName()
        except:
            self.device = pcap.getDefaultName()
        self.filter = str(args['filter']).replace("'''", "")
        self.data = None
        self.tempFile = os.tmpnam()
        self.thread = None

    def OnTestStarting(self):
        self.thread = PcapThread(self, self.device, self.filter, self.tempFile)
        self.thread.start()
        self.data = None
        print("PcapMonitor: OnTestStarting done")

    def OnTestFinished(self):
        # Stop thread
        self.data = None
        if self.thread is not None and self.thread.isAlive():
            self.thread.stopEvent.set()
            self.thread.join()
            self.thread.dumpClosed.wait()
            # Read dump
            f = open(self.tempFile, "rb")
            self.data = f.read()
            f.close()
            print("PcapMonitor: Thread joined, dump saved")
        self.thread = None

    def GetMonitorData(self):
        return {'Capture.pcap': self.data}

    def OnShutdown(self):
        if self.thread is not None and self.thread.isAlive():
            self.thread.stopEvent.set()
            self.thread.join()
