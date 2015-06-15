# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from struct import pack
from struct import unpack
from types import IntType
from types import FloatType
from types import LongType

from Peach.transformer import Transformer


class NumberToString(Transformer):
    """Transforms any type of number (int, long, float) to string."""

    def __init__(self, formatString=None):
        """Create NumberToString Instance.
        |formatString| is a standard Python string formatter (optional).
        """
        Transformer.__init__(self)
        self._formatString = formatString

    def realEncode(self, data):
        """Convert number to string.
        If no formatString was specified in class constructor data type is
        dynamically determined and converted using a default formatString of
        "%d", "%f", or "%d" for Int, Float, and Long respectively.
        """

        if self._formatString is None:
            retType = type(data)
            if retType is IntType:
                return "%d" % data
            elif retType is FloatType:
                return "%f" % data
            elif retType is LongType:
                return "%d" % data
            else:
                return data

        return self._formatString % data


class SignedNumberToString(Transformer):
    """Transforms unsigned numbers to strings."""

    def __init__(self):
        Transformer.__init__(self)
        self._size = None

    def realEncode(self, data):
        self._size = size = len(data) * 8

        if size == 0:
            return ""
        elif size == 8:
            return str(unpack("b", data)[0])
        elif size == 16:
            return str(unpack("h", data)[0])
        elif size == 24:
            raise Exception("24 bit numbers not supported")
        elif size == 32:
            return str(unpack("i", data)[0])
        elif size == 64:
            return str(unpack("q", data)[0])

        raise Exception("Unknown numerical size")

    def realDecode(self, data):
        size = self._size

        if size is None:
            return ""

        if size == 8:
            return pack("b", data)
        elif size == 16:
            return pack("h", data)
        elif size == 24:
            raise Exception("24 bit numbers not supported")
        elif size == 32:
            return pack("i", data)
        elif size == 64:
            return pack("q", data)

        raise Exception("Unknown numerical size")


class UnsignedNumberToString(Transformer):
    """Transforms unsigned numbers to strings."""

    def __init__(self):
        Transformer.__init__(self)
        self._size = None

    def realEncode(self, data):
        self._size = size = len(data) * 8

        if size == 0:
            return ""
        elif size == 8:
            return str(unpack("B", data)[0])
        elif size == 16:
            return str(unpack("H", data)[0])
        elif size == 24:
            raise Exception("24 bit numbers not supported")
        elif size == 32:
            return str(unpack("I", data)[0])
        elif size == 64:
            return str(unpack("Q", data)[0])

        raise Exception("Unknown numerical size:")

    def realDecode(self, data):
        size = self._size

        if size is None:
            return ""

        if size == 8:
            return pack("B", data)
        elif size == 16:
            return pack("H", data)
        elif size == 24:
            raise Exception("24 bit numbers not supported")
        elif size == 32:
            return pack("I", data)
        elif size == 64:
            return pack("Q", data)

        raise Exception("Unknown numerical size")
