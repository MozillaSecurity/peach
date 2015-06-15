# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
import sys
import logging

from Peach.Engine.common import highlight


def isSupportedOS(platforms):
    return filter(lambda x: x == sys.platform, platforms)


def isPosix():
    return 'posix' in sys.builtin_module_names


def isLinux():
    return sys.platform == "linux2"


def isMacOS():
    return sys.platform == "darwin"


def isWindows():
    return sys.platform == "win32"


def printHex(src):
    FILTER = ''.join([(len(repr(chr(x))) == 3) and chr(x) or '.' for x in range(256)])
    N = 0
    result = ''
    length = 16
    while src:
        s, src = src[:length], src[length:]
        hexa = ' '.join(["%02X" % ord(x) for x in s])
        s = s.translate(FILTER)
        result += "%04X   %-*s   %s\n" % (N, length * 3, hexa, s)
        N += length
    print(result)


def getBooleanAttribute(args, name):
    val = args.get(name, '0').lower().replace("'''", "")
    result = val in ('true', 'yes', '1')
    if not result:
        assert val in ('false', 'no', '0')
    return result


def getFloatAttribute(args, name, default=""):
    return float(args.get(name, default).replace("'''", ""))


def getStringAttribute(args, name, default=""):
    return args.get(name, default).replace("'''", "")


def setAttributesFromParams(node):
    if node is not None and node.get('params') is not None:
        for kv in node.get('params').split(','):
            try:
                k, v = [s.strip() for s in kv.split('=', 1)]
            except ValueError:
                logging.error(highlight.error("The macro %s has no value." % kv))
                sys.exit(-1)
            k = k[0].lower() + k[1:]  # CamelCase -> camelCase
            node.set(k, v)
