# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from Peach.transformer import Transformer


class HexString(Transformer):
    """Transform a string of bytes into the specified hex format.

    Example:

    gen = Static("AAAABBBB").setTransformer(HexString())
    print gen.getValue()
        41 41 41 41 42 42 42 42

    gen = Static("AAAABBBB").setTransformer(HexString(None, 4, "0x"))
    print gen.getValue()
        0x414141410x42424242

    gen = Static("AAAABBBB").setTransformer(HexString(None, 1, " \\x"))
    print gen.getValue()
        \x41 \x41 \x41 \x41 \x42 \x42 \x42 \x42
    """

    def __init__(self, anotherTransformer=None, resolution=None, prefix=None):
        """Create Transformer object.

        :param anotherTransformer: a transformer to run next
        :type anotherTransformer: Transformer
        :param resolution: number of nibbles between separator
                           (must be a positive even integer)
        :type resolution: int
        :param prefix: a value to prepend each chunk with (defaults to ' ')
        :type prefix: str
        """

        Transformer.__init__(self, anotherTransformer)
        self._resolution = resolution
        self._prefix = prefix

    def realEncode(self, data):
        ret = ''
        if self._resolution is None:
            self._resolution = 1
        # Try to detect if user passed in an odd numbered value
        if self._resolution % 2 and self._resolution != 1:
            raise Exception("Resolution must be 1 or a multiple of two.")
        if len(data) % self._resolution != 0:
            raise Exception("Data length must be divisible by resolution.")
        if self._prefix is None:
            self._prefix = " "
        tmp = ''
        for c in data:
            h = hex(ord(c))[2:]
            if len(h) == 2:
                tmp += h
            else:
                tmp += "0%s" % h
            if len(tmp) / 2 == self._resolution:
                ret += self._prefix + tmp
                tmp = ''
        ret = ret.strip()
        return ret