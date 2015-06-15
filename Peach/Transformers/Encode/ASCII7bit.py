# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from Peach.transformer import Transformer


class Data7Bit(Transformer):
    def __init__(self):
        Transformer.__init__(self)

    def realEncode(self, data):
        result = []
        count = 0
        last = 0
        for c in data:
            this = ord(c) << (8 - count)
            if count:
                result.append('%02X' % ((last >> 8) | (this & 0xFF)))
            count = (count + 1) % 8
            last = this
        result.append('%02x' % (last >> 8))
        return ''.join(result)

    def realDecode(self, data):
        return data
