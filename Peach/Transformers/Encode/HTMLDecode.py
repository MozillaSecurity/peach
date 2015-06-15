# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
import xml.sax.saxutils

from Peach.transformer import Transformer


class HtmlDecode(Transformer):
    """Decode HTML encoded string."""

    def realEncode(self, data):
        return xml.sax.saxutils.unescape(data)

    def realEncode(self, data):
        return xml.sax.saxutils.escape(data)
