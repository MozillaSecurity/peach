# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
import xml.sax.saxutils

from Peach.transformer import Transformer


class HtmlEncode(Transformer):
    """Perform standard HTML encoding of < > & and "."""

    def realEncode(self, data):
        return xml.sax.saxutils.quoteattr(data).strip('"')

    def realDecode(self, data):
        return xml.sax.saxutils.unescape(data)
