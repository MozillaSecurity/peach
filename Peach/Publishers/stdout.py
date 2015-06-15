# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
import logging

from Peach.publisher import Publisher
from Peach.Utilities.common import printHex


class Stdout(Publisher):
    """
    Basic stdout publisher. All data is written to stdout.
    No input is available from this publisher.
    """

    def accept(self):
        pass

    def connect(self):
        pass

    def close(self):
        pass

    def send(self, data):
        print(data)

    def receive(self, size=None):
        return ""

    def call(self, method, args):
        str = ""
        for a in args:
            str += "%s, " % repr(a)
        print("%s(%s)" % (method, str[:-2]))
        return ""


class StdoutHex(Publisher):
    """
    Basic stdout publisher that emits a hex dump. All data is written to stdout.
    No input is available from this publisher.
    """

    def accept(self):
        pass

    def connect(self):
        pass

    def close(self):
        pass

    def send(self, src):
        # http://code.activestate.com/recipes/142812/
        FILTER = "".join([(len(repr(chr(x))) == 3) and chr(x) or '.' for x in range(256)])
        N = 0
        result = ""
        length = 16
        while src:
            s, src = src[:length], src[length:]
            hexa = " ".join(["%02X" % ord(x) for x in s])
            s = s.translate(FILTER)
            result += "%04X   %-*s   %s\n" % (N, length * 3, hexa, s)
            N += length
        logging.debug("Hexdump of mutated data:\n%s" % result)

    def receive(self, size=None):
        return ""

    def call(self, method, args):
        str = ""
        for a in args:
            str += "%s, " % repr(a)
        print("%s(%s)" % (method, str[:-2]))
        return ""


class Null(Publisher):
    """
    Basic stdout publisher. All data is written to stdout.
    No input is available from this publisher.
    """

    def accept(self):
        pass

    def connect(self):
        pass

    def close(self):
        pass

    def send(self, data):
        pass

    def receive(self):
        return ""

    def call(self, method, args):
        return ""


class StdoutCtypes(Publisher):
    withNode = True

    def connect(self):
        pass

    def sendWithNode(self, data, dataNode):
        """
        Publish some data

        @type	data: string
        @param	data: Data to publish
        @type   dataNode: DataElement
        @param  dataNode: Root of data model that produced data
        """
        value = dataNode.asCType()
        print(value)
        print(dir(value))

    def close(self):
        """
        Close current stream/connection.
        """
        pass
