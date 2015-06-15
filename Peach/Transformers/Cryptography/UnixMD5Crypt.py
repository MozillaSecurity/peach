# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
import string
import hashlib

from Peach.transformer import Transformer


MAGIC = '$1$'
ITOA64 = "./0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"


def to64(v, n):
    ret = ''
    while n - 1 >= 0:
        n -= 1
        ret += ITOA64[v & 0x3f]
        v >>= 6
    return ret


def apache_md5_crypt(pw, salt):
    # change the Magic string to match the one used by Apache
    return unix_md5_crypt(pw, salt, '$apr1$')


def unix_md5_crypt(pw, salt, magic=None):
    if magic is None:
        magic = MAGIC

    # Take care of the magic string if present
    if salt[:len(magic)] == magic:
        salt = salt[len(magic):]

    # salt can have up to 8 characters:
    salt = string.split(salt, '$', 1)[0]
    salt = salt[:8]

    ctx = pw + magic + salt
    final = hashlib.md5(pw + salt + pw).digest()

    for pl in range(len(pw), 0, -16):
        if pl > 16:
            ctx = ctx + final[:16]
        else:
            ctx = ctx + final[:pl]

    # Now the 'weird' xform (??)
    i = len(pw)
    while i:
        if i & 1:
            ctx += chr(0)
        else:
            ctx = ctx + pw[0]
        i >>= 1

    final = hashlib.md5(ctx).digest()

    # The following is supposed to make things run slower.
    for i in range(1000):
        ctx1 = ''
        if i & 1:
            ctx1 = ctx1 + pw
        else:
            ctx1 = ctx1 + final[:16]
        if i % 3:
            ctx1 = ctx1 + salt
        if i % 7:
            ctx1 = ctx1 + pw
        if i & 1:
            ctx1 = ctx1 + final[:16]
        else:
            ctx1 = ctx1 + pw
        final = hashlib.md5(ctx1).digest()

    # Final xform
    passwd = ''
    passwd += to64((int(ord(final[0])) << 16)
                   | (int(ord(final[6])) << 8)
                   | (int(ord(final[12]))), 4)
    passwd += to64((int(ord(final[1])) << 16)
                   | (int(ord(final[7])) << 8)
                   | (int(ord(final[13]))), 4)
    passwd += to64((int(ord(final[2])) << 16)
                   | (int(ord(final[8])) << 8)
                   | (int(ord(final[14]))), 4)
    passwd += to64((int(ord(final[3])) << 16)
                   | (int(ord(final[9])) << 8)
                   | (int(ord(final[15]))), 4)
    passwd += to64((int(ord(final[4])) << 16)
                   | (int(ord(final[10])) << 8)
                   | (int(ord(final[5]))), 4)
    passwd += to64((int(ord(final[11]))), 2)
    return magic + salt + '$' + passwd


class ApacheMd5Crypt(Transformer):
    """Apache style MD5 crypt.
    If no salt is specified will use first	two chars of data, ala pwd style.

    Uses '$apr1$' as magic.

    From underlying docs:
    I{apache_md5_crypt() provides a function compatible with Apache's
    .htpasswd files. This was contributed by Bryan Hart <bryan@eai.com>.}

    I{"THE BEER-WARE LICENSE" (Revision 42):
    <phk@login.dknet.dk> wrote this file. As long as you retain this notice
    you can do whatever you want with this stuff. If we meet some day, and you
    think this stuff is worth it, you can buy me a beer in return.
    Poul-Henning Kamp}
    """

    _salt = None

    def __init__(self, salt=None):
        """
        :param salt: salt for crypt (optional)
        :type salt: str
        """
        Transformer.__init__(self)
        self._salt = salt

    def realEncode(self, data):
        if self._salt is None:
            return apache_md5_crypt(data, data[:2])
        return apache_md5_crypt(data, self._salt)


class UnixMd5Crypt(Transformer):
    """UNIX style MD5 crypt.
    If no salt is specified will use first two chars of data, ala pwd style.

    From underlying docs:

    I{unix_md5_crypt() provides a crypt()-compatible interface to the
    rather new MD5-based crypt() function found in modern operating systems.
    It's based on the implementation found on FreeBSD 2.2.[56]-RELEASE and
    contains the following license in it:}

    I{"THE BEER-WARE LICENSE" (Revision 42):
    <phk@login.dknet.dk> wrote this file. As long as you retain this notice
    you can do whatever you want with this stuff. If we meet some day, and you
    think this stuff is worth it, you can buy me a beer in return.
    Poul-Henning Kamp}
    """

    _salt = None
    _magic = None

    def __init__(self, salt=None, magic=None):
        """
        :type salt: str
        :param salt: salt for crypt (optional)
        :type magic: str
        :param magic: magic, usually $1$ on unix (optional)
        """
        Transformer.__init__(self)
        self._salt = salt
        self._magic = magic

    def realEncode(self, data):
        if self._salt is None:
            return unix_md5_crypt(data, data[:2], self._magic)
        return unix_md5_crypt(data, self._salt, self._magic)
