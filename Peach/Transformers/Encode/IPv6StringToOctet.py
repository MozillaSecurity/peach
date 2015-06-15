# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from struct import pack

from Peach.transformer import Transformer


class Ipv6StringToOctet(Transformer):
    """Convert a collen notation IPv6 address into a 4 byte octet
    representation.
    """

    def realEncode(self, data):
        return pack('BBBBBBBBBBBBBBBB', data.split(':'))
