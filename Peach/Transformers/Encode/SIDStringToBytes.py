# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from struct import pack

from Peach.transformer import Transformer


class SidStringToBytes(Transformer):
    """Transform a string representation of SID to a bytes.
    Format: S-1-5-21-2127521184-1604012920-1887927527-1712781
    """

    def realEncode(self, data):
        sid = data.split('-')
        if len(sid) < 3 or sid[0] != 'S':
            raise Exception("Invalid SID string: {!s}".format(data))
        ret = pack("BBBBBBBB", int(sid[1]), int(sid[2]), 0, 0, 0, 0, 0, 5)
        for i in range(int(sid[2])):
            ret += pack("I", int(sid[i + 3]))
        return ret