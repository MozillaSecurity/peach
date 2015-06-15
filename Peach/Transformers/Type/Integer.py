# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from struct import pack
from struct import unpack

from Peach.transformer import Transformer


class _AsNumber(Transformer):
    """Base class to transform a number to a specific size."""

    def __init__(self, isSigned=1, isLittleEndian=1):
        """
        :param isSigned: 1 for signed, 0 for unsigned
        :type isSigned: number
        :param isLittleEndian: 1 for signed, 0 for unsigned
        :type isLittleEndian: number
        """

        Transformer.__init__(self)
        self._isSigned = isSigned
        self._isLittleEndian = isLittleEndian

    def _unfuglyNumber(self, data):
        """
        Will attempt to figure out if the incoming data is a byte stream that
        must be converted to get our number we will then cast, due to
        StaticBinary issues.
        """
        try:
            if int(data) == int(str(data)):
                return int(data)
        except Exception as e:
            pass
        hexString = ""
        for c in data:
            h = hex(ord(c))[2:]
            if len(h) < 2:
                h = "0" + h
            hexString += h
        return int(hexString, 16)

    def realEncode(self, data):
        data = self._unfuglyNumber(data)
        packStr = ''
        if self._isLittleEndian == 1:
            packStr = '<'
        else:
            packStr = '>'
        if self._isSigned == 1:
            packStr += self._packFormat.lower()
        else:
            packStr += self._packFormat.upper()
        # Prevent silly deprecation warnings from Python
        if packStr[1] == 'b' and data > 0xfe:
            data = 0
        elif packStr[1] == 'B' and (data > 0xff or data < 0):
            data = 0
        elif packStr[1] == 'h' and data > 0xfffe:
            data = 0
        elif packStr[1] == 'H' and (data > 0xffff or data < 0):
            data = 0
        elif packStr[1] == 'i' and data > 0xfffffffe:
            data = 0
        elif packStr[1] == 'L' and (data > 0xffffffff or data < 0):
            data = 0
        elif packStr[1] == 'q' and data > 0xfffffffffffffffe:
            data = 0
        elif packStr[1] == 'Q' and (data > 0xffffffffffffffff or data < 0):
            data = 0
        try:
            return pack(packStr, int(data))
        except Exception as e:
            return pack(packStr, 0)

    def realDecode(self, data):
        packStr = ''
        if self._isLittleEndian == 1:
            packStr = '<'
        else:
            packStr = '>'
        if self._isSigned == 1:
            packStr += self._packFormat.lower()
        else:
            packStr += self._packFormat.upper()
        try:
            return unpack(packStr, data)[0]
        except Exception as e:
            return 0


class AsInt8(_AsNumber):
    """Transform an number to an Int8 or UInt8."""
    _packFormat = 'b'


class AsInt16(_AsNumber):
    """Transform an number to an Int16 or UInt16."""
    _packFormat = 'h'


class AsInt24(Transformer):
    """Transform an number to a UInt24."""

    def __init__(self, isSigned=1, isLittleEndian=1):
        """
        @param isSigned: 1 for signed, 0 for unsigned (we ignore this)
        @type isSigned: number
        @param isLittleEndian: 1 for signed, 0 for unsigned
        @type isLittleEndian: number
        """
        Transformer.__init__(self)
        self._isLittleEndian = isLittleEndian

    def realEncode(self, data):
        try:
            data = int(data)
            packStr = ''
            if self._isLittleEndian == 1:
                packStr = '<'
            else:
                packStr = '>'
            packStr += 'L'
            v = pack(packStr, data)
            if self._isLittleEndian == 1:
                return v[:3]
            else:
                return v[1:]
        except Exception as e:
            return '0'


class AsInt32(_AsNumber):
    """Transform an number to an Int32 or UInt32."""
    _packFormat = 'l'


class AsInt64(_AsNumber):
    """Transform an number to an Int64 or UInt64."""
    _packFormat = 'q'
