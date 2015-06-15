# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
import bz2

from Peach.transformer import Transformer


class Compress(Transformer):
    """Bzip2 compression transform.
    Allows for compression level selection (default is 9).
    """

    def __init__(self, level=9):
        """
        @type level: int
        @param level: The compress level parameter, if given, must be a number
                      between 1 and 9; the default is 9.
        """
        Transformer.__init__(self)
        self._level = level

    def realEncode(self, data):
        return bz2.compress(data, self._level)

    def realDecode(self, data):
        return bz2.decompress(data)


class Bz2Decompress(Transformer):
    """Bzip2 decompression transform."""

    def realEncode(self, data):
        return bz2.decompress(data)

    def realDecode(self, data):
        return bz2.compress(data, 6)
