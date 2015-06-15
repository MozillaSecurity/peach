# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
import zlib

from Peach.transformer import Transformer


class Compress(Transformer):
    """Gzip compression transformer.
    Allows compression level selection (default is 6).
    """

    def __init__(self, level=6):
        """
        :param level: an integer from 1 to 9 controlling the level of
                      compression; 1 is fastest and produces the least
                      compression, 9 is slowest and produces the most.
                      The default value is 6.
        :type level: int
        """
        Transformer.__init__(self)
        self._level = level
        self._wbits = 15

    def realEncode(self, data):
        return zlib.compress(data, self._level)

    def realDecode(self, data):
        return zlib.decompress(data, self._wbits)


class Decompress(Transformer):
    """Gzip decompression transform."""

    def __init__(self, wbits=15):
        """
        :type wbits: int
        :param wbits: The absolute value of wbits is the base two logarithm
                      of the size of the history buffer (the 'window size')
                      used when compressing data. Its absolute value should be
                      between 8 and 15 for the most recent versions of the
                      zlib library, larger values resulting in better
                      compression at the expense of greater memory usage.
                      The default value is 15. When wbits is negative, the
                      standard gzip header is suppressed; this is an
                      undocumented feature of the zlib library, used for
                      compatibility with unzip's compression file format.
        """
        Transformer.__init__(self)
        self._wbits = wbits
        self._level = 6

    def realEncode(self, data):
        return zlib.decompress(data, self._wbits)

    def realDecode(self, data):
        return zlib.compress(data, self._level)
