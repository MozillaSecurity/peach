# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from struct import pack

from Peach.transformer import Transformer


class Utf16Le(Transformer):
    """Encode string as UTF-16LE.
    Supports surrogate pair encoding of values larger then 0xFFFF.
    """

    def realEncode(self, data):
        ret = ''
        for c in data:
            if ord(c) <= 0xFF:
                ret += pack(">BB", ord(c), 0x00)
            elif ord(c) <= 0xFFFF:
                ret += pack("<H", ord(c))
            elif ord(c) > 0xFFFF:
                # Perform surrogate pair encoding
                value = ord(c)  # value
                value -= 0x10000
                valueHigh = value & 0xFFF  # high bits
                valueLow = value & 0xFFF000  # low bits
                word1 = 0xD800
                word2 = 0xDC00
                word1 |= valueHigh
                word2 |= valueLow
                ret += pack("<HH", word1, word2)
        return ret