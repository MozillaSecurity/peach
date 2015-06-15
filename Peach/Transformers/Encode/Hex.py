# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from binascii import b2a_hex, a2b_hex

from Peach.transformer import Transformer


class Hex(Transformer):
    """Transform a data stream into Hex."""

    def realEncode(self, data):
        return b2a_hex(data)

    def realDecode(self, data):
        return a2b_hex(data)
