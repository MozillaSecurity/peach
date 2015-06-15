# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
import socket
from Peach.publisher import *
import Peach


def Debug(msg):
    if Peach.Engine.engine.Engine.debug:
        print("%r" % msg)


class Udp(Publisher):
    """
    A simple UDP publisher.
    """

    def __init__(self, host, port, timeout=2):
        """
        @type	host: string
        @param	host: Remote hostname
        @type	port: number
        @param	port: Remote port
        """
        Publisher.__init__(self)
        self._host = host
        self._port = port
        self._timeout = float(timeout)

        if self._timeout is None:
            self._timeout = 2

        self._socket = None
        self.buff = ""
        self.pos = 0

    def stop(self):
        """Close connection if open"""
        self.close()

    def close(self):
        if self._socket is not None:
            self._socket.close()
            self._socket = None
        self.buff = ""
        self.pos = 0

    def connect(self):
        if self._socket is not None:
            # Close out old socket first
            self._socket.close()
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._socket.connect((self._host, int(self._port)))
        self.buff = ""
        self.pos = 0

    def send(self, data):
        """
        Send data via sendall.

        @type	data: string
        @param	data: Data to send
        """
        try:
            self._socket.sendall(data)
            Debug(data)
        except socket.error:
            pass

    def receive(self, size=None):
        try:
            self._socket.settimeout(self._timeout)
            data, addr = self._socket.recvfrom(65565)
            Debug(data)
            if hasattr(self, "publisherBuffer"):
                self.publisherBuffer.haveAllData = True
            return data
        except:
            raise Timeout("")


class Udp6(Publisher):
    """
    A simple UDP publisher.
    """

    def __init__(self, host, port, timeout=2):
        """
        @type	host: string
        @param	host: Remote hostname
        @type	port: number
        @param	port: Remote port
        """
        Publisher.__init__(self)
        self._host = host
        self._port = port
        self._timeout = float(timeout)

        if self._timeout is None:
            self._timeout = 2

        self._socket = None
        self.buff = ""
        self.pos = 0

    def stop(self):
        """Close connection if open"""
        self.close()

    def close(self):
        if self._socket is not None:
            self._socket.close()
            self._socket = None
        self.buff = ""
        self.pos = 0

    def connect(self):
        if self._socket is not None:
            # Close out old socket first
            self._socket.close()

        self._socket = socket.socket(23, socket.SOCK_DGRAM)
        self._socket.connect((self._host, int(self._port)))
        self.buff = ""
        self.pos = 0

    def send(self, data):
        """
        Send data via sendall.

        @type	data: string
        @param	data: Data to send
        """
        try:
            self._socket.sendall(data)
        except socket.error:
            pass

    def receive(self, size=None):
        data = None
        try:
            self._socket.settimeout(self._timeout)
            data, addr = self._socket.recvfrom(65565)

            if hasattr(self, "publisherBuffer"):
                self.publisherBuffer.haveAllData = True

            return data
        except:
            if data is None or len(data) < size:
                raise Timeout("")

            return data


class UdpListener(Publisher):
    """
    A simple UDP publisher.
    """

    def __init__(self, host, port, timeout=2):
        """
        @type	host: string
        @param	host: Remote hostname
        @type	port: number
        @param	port: Remote port
        """
        Publisher.__init__(self)
        self._host = host
        self._port = port
        self._timeout = float(timeout)

        if self._timeout is None:
            self._timeout = 2

        self._socket = None

    def stop(self):
        """Close connection if open"""
        self.close()

    def close(self):
        if self._socket is not None:
            self._socket.close()
            self._socket = None

    def connect(self):
        if self._socket is not None:
            # Close out old socket first
            self._socket.close()
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._socket.bind((self._host, int(self._port)))

    def send(self, data):
        """
        Send data via sendall.

        @type	data: string
        @param	data: Data to send
        """
        Debug(data)
        try:
            self._socket.sendto(data, self.addr)
        except socket.error:
            pass

    def receive(self, size=None):
        data, self.addr = self._socket.recvfrom(65565)
        Debug(data)
        if hasattr(self, "publisherBuffer"):
            self.publisherBuffer.haveAllData = True
        return data


class Udp6Listener(Publisher):
    """
    A simple UDP publisher.
    """

    def __init__(self, host, port, timeout=2):
        """
        @type	host: string
        @param	host: Remote hostname
        @type	port: number
        @param	port: Remote port
        """
        Publisher.__init__(self)
        self._host = host.lower()
        self._port = port
        self._timeout = float(timeout)

        if self._timeout is None:
            self._timeout = 2

        self._socket = None

    def stop(self):
        """Close connection if open"""
        self.close()

    def close(self):
        if self._socket is not None:
            self._socket.close()
            self._socket = None

    def connect(self):
        if self._socket is not None:
            # Close out old socket first
            self._socket.close()
        self._socket = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
        self._socket.bind(("", int(self._port)))

    def send(self, data):
        """
        Send data via sendall.

        @type	data: string
        @param	data: Data to send
        """
        try:
            self._socket.sendto(data, self.addr)

        except socket.error:
            pass

    def receive(self, size=None):
        while True:
            data, self.addr = self._socket.recvfrom(65565)
            if self.addr[0].lower().find(self._host) != -1:
                break

        if hasattr(self, "publisherBuffer"):
            self.publisherBuffer.haveAllData = True

        return data


class UdpProxyB(UdpListener):
    def __init__(self, host, port):
        UdpListener.__init__(self, host, port)


class UdpProxyA(Udp):
    def __init__(self, host, port):
        Udp.__init__(self, host, port)

"""
from twisted.internet.protocol import DatagramProtocol
from twisted.internet import reactor

class Client(DatagramProtocol):
    def __init__(self, server, host, port):
        self.server = server
        self.host = host
        self.port = port

    def startProtocol(self):
        self.transport.connect(desthost, destport)

    def datagramReceived(self, data, (host, port)):
        self.server.transport.write(data, (self.host, self.port))

class Server(DatagramProtocol):
    client = None
    def datagramReceived(self, data, (host, port)):
        self.client = Client(self, host, port)
        reactor.listenUDP(0, self.client)
        self.client.transport.write(data, (desthost, destport))

reactor.listenUDP(localport, Server())
reactor.run()
"""