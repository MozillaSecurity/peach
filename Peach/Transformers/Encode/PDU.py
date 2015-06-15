# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from Peach.transformer import Transformer


class PhoneNumber(Transformer):
    def __init__(self):
        Transformer.__init__(self)

    def realEncode(self, data):
        s = ""

        # Add padding F to make length of phone number even
        s = s + "F" if len(data) % 2 else s

        # Split string in 2 byte segments
        segments = [s[i:i + 2] for i in range(0, len(s), 2)]

        # Reverse and join back together
        segments = "".join([i[1] + i[0] for i in segments])

        return segments

    def realDecode(self, data):
        # NOTE: after Data.realDecode data is binary NOT semi decimal octets!

        # Split string in 2 bytes segments
        segments = [data[i] for i in range(0, len(data), 1)]

        segments = ["%02x" % ord(i) for i in segments]

        # Reverse and join back together
        segments = "".join([i[1] + i[0] for i in segments])

        # Strip potential padding F
        s = segments[:-1] if segments[-1].upper() == "F" else segments

        return s
