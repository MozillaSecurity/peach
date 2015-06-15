# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
import socket
import SocketServer
import multiprocessing
import SimpleHTTPServer
import atexit
import logging

socketProcesses = []
assignedPorts = set()


@atexit.register
def cleanupSocketProcesses():
    logging.debug("Killing socket processes.")
    for process in socketProcesses:
        process.join()


def getUnboundPort(host="", minRange=30000, maxRange=35000, socket_type=1, assignOnlyOnce=False):
    for port in range(minRange, maxRange):
        if port in assignedPorts:
            continue

        sd = socket.socket(type=socket_type)
        try:
            sd.bind((host, port))
        except socket.error as err:
            if err.errno != 48:
                print(err.strerror)
            sd = None
        else:
            sd.close()
            if assignOnlyOnce:
                assignedPorts.add(port)
            return port
    return -1


def runHTTPDThread():
    port = getUnboundPort(minRange=8000, maxRange=9000)
    httpd = SocketServer.TCPServer(("", port), SimpleHTTPServer.SimpleHTTPRequestHandler)
    p = multiprocessing.Process(target=httpd.serve_forever, args=())
    p.start()
    socketProcesses.append(p)
    return port
