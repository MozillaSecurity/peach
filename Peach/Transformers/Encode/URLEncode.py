# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
import urllib

from Peach.transformer import Transformer


class UrlEncode(Transformer):
    """URL encode without pluses."""

    def realEncode(self, data):
        return urllib.quote(data)

    def realDecode(self, data):
        return urllib.unquote(data)


class UrlEncodePlus(Transformer):
    """URL encode with pluses."""

    def realEncode(self, data):
        return urllib.quote_plus(data)

    def realDecode(self, data):
        return urllib.unquote_plus(data)
