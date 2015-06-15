# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
import sys
import time
import socket

from Peach.publisher import Publisher
from Peach.Engine.common import PeachException
from Peach.Utilities.common import *


usingLightBlue = False
usingBluetooth = False

if sys.platform == "darwin":
    try:
        # Do not relay too much on this Publisher when using Lightblue,
        # this library is unmaintained since 2009 but there is no other
        # Python alternative for MacOS except PyObjC IOBluetooth Bridge.
        import lightblue
    except ImportError:
        sys.exit("Lightblue is not installed.")
    else:
        print("[*] Library: Lightblue (%s)" % sys.platform)
        usingLightBlue = True
elif sys.platform == "linux2":
    try:
        import bluetooth
    except ImportError:
        sys.exit("PyBluez is not installed.")
    else:
        print("[*] Library: PyBluez (%s)" % sys.platform)
        usingBluetooth = True
else:
    sys.exit("Unsupported platform.")


def discover():
    print("Scanning for devices ...")

    if usingBluetooth:
        devices = bluetooth.discover_devices()
        print(devices)

    if usingLightBlue:
        devices = lightblue.finddevices()
        print(devices)

    return devices


def enumerate_services(device):
    print("Find services on device: %s" % device)

    if usingBluetooth:
        services = bluetooth.find_service(bdaddr=device) # name ?

    if usingLightBlue:
        services = lightblue.findservices(device)
        print(services)

    return services


def lightblue_server_test():
    # L2CAP server sockets not currently supported :(
    s = lightblue.socket(lightblue.L2CAP)
    s.bind(("", 0x1001))
    s.listen(1)
    lightblue.advertise("Peach", s, lightblue.L2CAP)
    conn, addr = s.accept()
    print("Connected by", addr)
    data = conn.recv(1024)
    print("Received: %s" % data)
    conn.close()
    s.close()


def pybluez_server_test():
    s = bluetooth.BluetoothSocket(bluetooth.L2CAP)
    s.bind(("", 0x1001))
    s.listen(1)
    conn, addr = s.accept()
    print("Connected by %s" % addr)
    data = s.recv(1024)
    print("Received: %s" % data)
    conn.close()
    s.close()


class L2CAP_Client(Publisher):
    def __init__(self, ba_addr, port, timeout=8.0, giveup=3.0):
        Publisher.__init__(self)

        self.ba_addr = ba_addr

        try:
            self.port = int(port)
        except:
            raise PeachException("Publisher parameter for port was not a valid number.")

        try:
            self.timeout = float(timeout)
        except:
            raise PeachException("Publisher parameter for timeout was not a valid number.")

        try:
            self.giveup = float(giveup)
        except:
            raise PeachException("Publisher parameter for giveup was not a valid number.")

        self._socket = None

    def start(self):
        if self._socket:
            return

        if usingLightBlue:
            for each_try in range(1, 5):
                print("[*] Connecting to %s on PSM %d (%d)" % (self.ba_addr, self.port, each_try))
                try:
                    self._socket = lightblue.socket(lightblue.L2CAP)
                    self._socket.connect((self.ba_addr, self.port))
                except socket.error:
                    self._socket = None
                    print("Failed.")
                    print("Wait {} seconds ...".format(self.giveup))
                    time.sleep(self.giveup)
                else:
                    print("Done.")
                    break

        if usingBluetooth:
            for each_try in range(1, 5):
                print("[*] Connecting to %s on PSM %d (%d)" % (self.ba_addr, self.port, each_try))
                try:
                    self._socket = bluetooth.BluetoothSocket(bluetooth.L2CAP)
                    self._socket.connect((self.ba_addr, self.port))
                except socket.error:
                    self._socket = None
                    print("Failed.")
                    print("Wait {} seconds ...".format(self.giveup))
                    time.sleep(self.giveup)
                else:
                    print("Done.")
                    break
        print("")

        if not self._socket:
            raise PeachException("L2CAP connection attempt failed.")

    def connect(self):
        pass

    def send(self, data):
        # Generating zero length data is allowed by the mutator but
        # will block receive. In our case a timeout will be raised.
        packet_len = len(data)
        n = 0

        print("=-" * 38 + "=\n[SEND] Packet")
        printHex(data)

        try:
            n = self._socket.send(data)
        except socket.error as e:
            print("Failed ({})".format(e))
            self.close()

        print("Sent: {}/{} bytes - Loss: {} bytes".format(n, packet_len, packet_len - n))


    def receive(self, size):
        data = ""

        print("=-" * 38 + "=\n[RECV] Packet")

        self._socket.settimeout(self.timeout)

        try:
            data = self._socket.recv(0xfff)
        except socket.error as e:
            if isinstance(e, socket.timeout):
                print("Failed (Timeout)")
            else:
                print("Failed ({})".format(e))
                self.close()

        printHex(data)

        print("Received: {} bytes".format(len(data)))
        print("=-" * 38 + "=\n")

        if self._socket:
            self._socket.settimeout(None)

        return data

    def close(self):
        if self._socket:
            try:
                self._socket.close()
            except:
                pass
        self._socket = None

    def stop(self):
        pass


if __name__ == "__main__":
    devices = discover()
    for each_device in devices:
        enumerate_services(each_device[0])
