# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from Peach.transformer import Transformer


class Utf8(Transformer):
    """Encode string as UTF-8."""

    def realEncode(self, data):
        return data.encode("utf8")

    def realDecode(self, data):
        return str(data.decode("utf8"))

