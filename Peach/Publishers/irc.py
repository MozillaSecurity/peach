# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
import sys
import time
import socket

from Peach.Engine.common import PeachException
from Peach.Publishers.tcp import TcpListener


#
# CAP REQ :multi-prefix
# NICK cdiehl
# USER cdiehl 0 * :Christoph Diehl
#


class FakeServer(TcpListener):
    def __init__(self, host, port):
        TcpListener.__init__(self, host, port)
        self._accepted = False

    def start(self):
        if self._listen is None:
            for i in range(3):
                try:
                    self._listen = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    self._listen.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    self._listen.bind((self._host, self._port))
                    self._listen.listen(1)
                    exception = None
                    break
                except:
                    self._listen = None
                    exception = sys.exc_info()
                time.sleep(0.5)
            if self._listen is None:
                value = ""
                try:
                    value = str(exception[1])
                except:
                    pass
                raise PeachException("TCP bind attempt failed: %s" % value)
        self.buff = ""
        self.pos = 0

    def accept(self):
        if not self._accepted:
            self.buff = ""
            self.pos = 0

            conn, addr = self._listen.accept()
            self._socket = conn
            self._clientAddr = addr
            self._accepted = True

    def close(self):
        pass

    def stop(self):
        pass



# connectedUsers = []
#
# request = client.recv(1024)
# initialized = True
#
# request = request.split("\r\n")
# for line in request:
# 	if line.startswith("NICK"):
# 		connectedUsers.append(line.split("NICK ")[1])
#
# hostname = client.gethostname()
# client.send(":%s %s")
