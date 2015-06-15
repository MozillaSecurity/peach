# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
import os
import sys
import struct

from Peach.publisher import Publisher
from Peach.Engine.common import PeachException


try:
    import usb.core
    import usb.util
except ImportError:
    print("Please install the following dependencies:")

    if sys.platform == "darwin":
        sys.exit("sudo port install libusb py27-pyusb-devel")

    if sys.platform == "linux2":
        sys.exit("sudo apt-get install libusb-1.0-0 python-usb")

    if sys.platform == "nt":
        sys.exit("PyUSB: http://sourceforge.net/apps/trac/pyusb/\r\n"
                 "LibUSB: http://sourceforge.net/apps/trac/libusb-win32/")


def getDevice(idVendor, idProduct):
    busses = usb.busses()
    for i, dev in enumerate(busses[0].devices):
        if dev.idProduct == idProduct and dev.idVendor == idVendor:
            return busses[0].devices[i]


def getDeviceName(handle):
    name = []
    for index in range(1, 3):
        name.append(handle.getString(index, 32))
    return " ".join(name)


def getConfiguration(dev):
    return dev.configurations[0]


def getInterface(dev):
    conf = getConfiguration(dev)
    return conf.interfaces[0][0]


def getEndpoints(dev):
    endpoints = []
    for endpoint in getInterface(dev):
        endpoints.append(endpoint)
    return endpoints


def send_controlMsg(handle, command):
    try:
        #handle.controlMsg(0xA1, 1, 0)
        handle.controlMsg(usb.TYPE_CLASS, 0x9, [0x01, command, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00], 0x200, 2000)
    except usb.USBError as e:
        print(e)


def send_interruptWrite(handle):
    try:
        handle.interruptWrite(0x81, [0] * 64, 1000)
    except:
        pass


def send_ctrl_transfer():
    dev = usb.core.find(idVendor=0x05ac, idProduct=0x12a0)
    dev.set_configuration()
    dev.ctrl_transfer(0x80, 6, 0x100, 1, [0x40, 1, 3], 1000)


class USBCtrlTransfer(Publisher):
    def __init__(self, idVendor, idProduct):
        Publisher.__init__(self)

        self.idVendor = int(idVendor, 16)
        self.idProduct = int(idProduct, 16)

        self.dev = None

    def start(self):
        #if self.dev:
        #    return

        self.dev = usb.core.find(idVendor=self.idVendor, idProduct=self.idProduct)

        if not self.dev:
            raise PeachException("Device not found.")

        try:
            self.dev.set_configuration()
        except usb.core.USBError as e:
            raise PeachException(str(e))

    def send(self, data):
        try:
            bmRequestType, bRequest, wValue, wIndex, wLength = struct.unpack(">BBHHH", data)
        except:
            pass
        else:
            try:
                self.dev.ctrl_transfer(bmRequestType, bRequest, wValue, wIndex, wLength, timeout=1000)
            except:
                pass

    def connect(self):
        pass

    def close(self):
        pass


if __name__ == "__main__":

    if sys.platform == "darwin":
        os.system("system_profiler SPUSBDataType")

    dev = getDevice(0x05ac, 0x12a0)
    usbConfiguration = getConfiguration(dev)
    usbInterface = getInterface(dev)

    handle = dev.open()

    print("\nDevice Name: {}\n".format(getDeviceName(handle)))

    try:
        prin("Unload current driver from interface ...")
        handle.detachKernelDriver(usbInterface.interfaceNumber)
        print("Done.")
    except usb.USBError as e:
        print("Failed!")

    try:
        print("Loading USB config ...")
        handle.setConfiguration(usbConfiguration.value)
        print("Done.")
    except usb.USBError as e:
        print("Failed!")

    try:
        print("Claiming interface ...")
        handle.claimInterface(usbInterface.interfaceNumber)
        print("Done.")
    except usb.USBError as e:
        print("Failed!")

    try:
        print("Set alternative interface ...")
        handle.setAltInterface(usbInterface.interfaceNumber)
        print("Done.")
    except usb.USBError as e:
        print("Failed!")

    try:
        print("Resetting device ...")
        handle.reset()
        print("Done.")
    except usb.USBError as e:
        print("Failed!")

    # ...

    try:
        print("Releasing interface ...")
        handle.releaseInterface()
        print("done.")
    except usb.USBError as e:
        print("failed!")