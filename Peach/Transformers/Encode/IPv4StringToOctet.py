# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from struct import pack

from Peach.transformer import Transformer


class Ipv4StringToOctet(Transformer):
    """Convert a dot notation IPv4 address into a 4 byte octet representation.
    """

    def realEncode(self, data):
        data = data.split('.')
        for i in range(len(data)):
            data[i] = int(data[i])
        return pack('BBBB', data[0], data[1], data[2], data[3])
