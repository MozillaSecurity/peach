# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
import socket
import time

from Peach.publisher import Publisher


class Icmp(Publisher):
    """
    A simple ICMP publisher.
    """

    _host = None
    _socket = None

    def __init__(self, host, timeout=0.1):
        """
        @type	host: string
        @param	host: Remote host
        @type	timeout: number
        @param	timeout: How long to wait for response
        """
        Publisher.__init__(self)
        self._host = host
        self._timeout = float(timeout)

    def stop(self):
        """
        Close connection if open.
        """
        self.close()

    def connect(self):
        if self._socket is not None:
            # Close out old socket first
            self._socket.close()
        self._socket = socket.socket(socket.AF_INET,
                                     socket.SOCK_RAW,
                                     socket.getprotobyname('icmp'))
        self._socket.connect((self._host, 22))

    def close(self):
        if self._socket is not None:
            self._socket.close()
            self._socket = None

    def send(self, data):
        """
        Send data via sendall.

        @type	data: string
        @param	data: Data to send
        """
        self._socket.sendall(data)

    def receive(self, size=None):
        """
        Receive up to 10000 bytes of data.

        @rtype: string
        @return: received data.
        """
        if size is not None:
            return self._socket.recv(size)
        else:
            self._socket.setblocking(0)
            timeout = self._timeout
            beginTime = time.time()
            ret = ""
            try:
                while True:
                    if len(ret) > 0 or time.time() - beginTime > timeout:
                        break
                    try:
                        ret += self._socket.recv(10000)
                    except socket.error as e:
                        if str(e).find("The socket operation could not "
                                       "complete without blocking") == -1:
                            raise
            except socket.error as e:
                print("Tcp::Receive(): Caught socket.error [{}]".format(e))
            self._socket.setblocking(1)
            return ret
