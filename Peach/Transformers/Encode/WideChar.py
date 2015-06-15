# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from Peach.transformer import Transformer


class WideChar(Transformer):
    """Transform a normal string into a wchar string.
    Does not convert unicode into wchar strings or anything super fancy.
    """

    def realEncode(self, data):
        try:
            return data.encode("utf-16le")
        except Exception as e:
            pass
        ret = ""
        for c in data:
            ret += c + "\0"
        return ret

    def realDecode(self, data):
        try:
            return str(data.decode("utf-16le"))
        except Exception as e:
            pass
        ret = ""
        for i in range(0, len(data), 2):
            ret += data[i]
        return ret