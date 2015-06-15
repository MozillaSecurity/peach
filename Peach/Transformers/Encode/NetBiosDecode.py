# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from Peach.transformer import Transformer


class NetBiosDecode(Transformer):
    """NetBiosName decode.
    @author: Blake Frantz
    """

    def __init__(self, anotherTransformer=None):
        """Create Transformer object.

        :param anotherTransformer: a transformer to run next
        :type anotherTransformer: Transformer
        """
        Transformer.__init__(self, anotherTransformer)

    def realEncode(self, data):
        if data % 2 != 0:
            raise Exception("Invalid NetBiosEncoding, length must be "
                            "divisible by two.")
        decoded = ""
        data = data.upper()
        for cnt in range(0, len(data), 2):
            c1 = ord(data[cnt])
            c2 = ord(data[cnt + 1])
            part1 = (c1 - 0x41) * 16
            part2 = (c2 - 0x41)
            decoded += chr(part1 + part2)
        return decoded

    def realDecode(self, data):
        encoded = ""
        data = data.upper()
        if self._pad:
            while len(data) < 16:
                data += " "
            data = data[:16]
        for c in data:
            ascii = ord(c)
            encoded += chr((ascii / 16) + 0x41)
            encoded += chr((ascii - (ascii / 16 * 16) + 0x41))
        # The 16th byte is the name scope id, set it to 'host' and
        # null term it.
        if self._pad:
            encoded = encoded[:30]
            encoded += '\x41'
            encoded += '\x41'
        return encoded
