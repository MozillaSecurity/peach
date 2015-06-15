# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
import base64

from Peach.transformer import Transformer


class Base64Encode(Transformer):
    """Base64 encode."""

    def realEncode(self, data):
        return base64.encodestring(data).rstrip().replace('\n', '')

    def realDecode(self, data):
        return base64.decodestring(data)
