# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from struct import pack

from Peach.transformer import Transformer


class Pack(Transformer):
    """Simple pack transform.
    Only a single piece of data can be used. Useful to generate binary data
    from a generator.

    Format          C Type              Python
    x 	            pad byte 	        no value
    c               char 	            string of length 1
    b 	            signed char         integer
    B               unsigned char 	    integer
    h               short               integer
    H               unsigned short      integer
    i               int                 integer
    I               unsigned int        long
    l               long                integer
    L               unsigned long       long
    q               long long           long
    Q               unsigned long long  long
    f               float               float
    d               double              float
    s               char[]              string
    p               char[]              string
    P               void*               integer
    """

    def __init__(self, packFormat):
        """Create a Pack transformer.
        packFormat is a standard pack format string. Format string should only
        contain a single data place holder.
        """
        Transformer.__init__(self)
        self._packFormat = packFormat

    def realEncode(self, data):
        return pack(self._packFormat, data)