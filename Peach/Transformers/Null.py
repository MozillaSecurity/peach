# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from Peach.transformer import Transformer


class Null(Transformer):
    """Null transformer. Returns that data unaltered."""

    def realEncode(self, data):
        return data

    def realDecode(self, data):
        return data
