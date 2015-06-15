# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from types import StringType

from Peach.transformer import Transformer


class IntToHex(Transformer):
    """Transform an integer into hex."""

    def __init__(self, withPrefix=0):
        """Create IntToHex object.
        withPrefix flag indicates if 0x prefix should be tagged onto string.
        Default is no.
        """
        Transformer.__init__(self)
        self._withPrefix = withPrefix

    def realEncode(self, data):
        if type(data) == StringType:
            data = int(data)
        ret = hex(data)
        if self._withPrefix == 0:
            return ret[2:]
        return ret