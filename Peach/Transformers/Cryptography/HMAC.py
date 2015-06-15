# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
import hmac
import hashlib

from Peach.transformer import Transformer


class Hmac(Transformer):
    """HMAC as described in RFC 2104."""

    _key = None
    _digestmod = None
    _asHex = None

    def __init__(self, key, digestmod=hashlib.md5, asHex=0):
        """
        Key is a generator for HMAC key, digestmod is hash to use (md5 or sha)

        :param key: HMAC key
        :type key: Generator
        :param digestmod: which digest to use
        :type digestmod: MD5 or SHA hashlib object
        :param asHex: 1 is hex, 0 is binary
        :type asHex: int
        """
        Transformer.__init__(self)
        self._key = key
        self._digestmod = digestmod
        self._asHex = asHex

    def realEncode(self, data):
        if self._asHex == 0:
            return hmac.new(self._key.getValue(), data, self._digestmod).digest()
        return hmac.new(self._key.getValue(), data, self._digestmod).hexdigest()
