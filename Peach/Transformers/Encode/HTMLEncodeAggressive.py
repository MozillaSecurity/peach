# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from Peach.transformer import Transformer


class HtmlEncodeAggressive(Transformer):
    """Perform aggressive HTML encoding. Only alpha-nums will not be encoded.
    """

    def realEncode(self, data):
        # Allow: a-z A-Z 0-9 SP , .
        # Allow (dec): 97-122 65-90 48-57 32 44 46
        if data is None or len(data) == 0:
            return ""
        out = ""
        for char in data:
            c = ord(char)
            if ((97 <= c <= 122) or
                    (65 <= c <= 90) or
                    (48 <= c <= 57) or
                    c == 32 or c == 44 or c == 46):
                out += char
            else:
                out += "&#{};".format(c)
        return out
