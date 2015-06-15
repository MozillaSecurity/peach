# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
import hashlib

from Peach.transformer import Transformer


class Sha1(Transformer):
    """SHA-1 transform (hex and binary)"""

    _asHex = 0

    def __init__(self, asHex=0):
        """
        @param asHex: 1 is hex, 0 is binary
        @type asHex: int
        """
        Transformer.__init__(self)
        self._asHex = asHex

    def realEncode(self, data):
        if self._asHex == 0:
            return hashlib.sha1(data).digest()
        return hashlib.sha1(data).hexdigest()
