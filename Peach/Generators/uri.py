# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from Peach.generator import Generator
from Peach.group import *
from Peach.Transformers import *
from Peach.Generators.dictionary import *
from Peach.Generators.data import *
from Peach.Transformers.Encode.URLEncode import UrlEncode, UrlEncodePlus
from Peach.Transformers.Encode.UTF16 import Utf16
from Peach.Generators.incrementor import *
from Peach.Generators.unicode import *


class _UriFragment(SimpleGenerator):
    """
    Generate resource id (#....)
    """

    def __init__(self, group=None):
        SimpleGenerator.__init__(self, group)
        # fragment    = *( pchar / "/" / "?" )
        self._generator = GeneratorList(None, [
            BadStrings(),
            GoodUnicode(None, BadStrings()),
            BadUnicode(None, BadStrings()),

            BadIpAddress(),
            BadHostname(),
            BadNumbers(),

            BadPath(),
            GoodUnicode(None, BadPath()),
            BadUnicode(None, BadPath()),

            BadFilename(),
            GoodUnicode(None, BadFilename()),
            BadUnicode(None, BadFilename()),

            #Repeater(None, Static('A'), 1, 100000),
            Repeater(None, Block2([
                Static('#'),
                Repeater(None, Static("A"), 1, 1000)
            ]), 1, 1000)
        ])


class UriFragment(SimpleGenerator):
    """
    Generate resource id (#....)
    """

    def __init__(self, group=None):
        SimpleGenerator.__init__(self, group)
        self._generator = Block2([
            Static("#"),
            GeneratorList(None, [
                Static("Peach"),
                _UriFragment(),
                _UriFragment().setTransformer(UrlEncode()),
                _UriFragment().setTransformer(UrlEncodePlus()),
                _UriFragment().setTransformer(Utf16()),
                _UriFragment().setTransformer(Utf16().addTransformer(UrlEncode())),
                _UriFragment().setTransformer(UrlEncode().addTransformer(Utf16())),
                Static("Peach")
            ])
        ])


class UriSchemeKnown(SimpleGenerator):
    """
    Known valid scheme/protocols.
    """

    def __init__(self, group=None):
        SimpleGenerator.__init__(self, group)
        self._generator = List(None, [
            'about', 'chrome',
            'data', 'default',
            'default-blocked',
            'feed', 'file',
            'ftp', 'gopher',
            'http', 'https',
            'jar', 'keyword',
            'moz-icon', 'pcast',
            'resource', 'view-source',
            'wyciwyg', 'mailto',
            'telnet', 'ldap',
            'disk', 'disks',
            'news', 'urn',
            'tel', 'javascript',
            'jscript', 'vbscript'
        ])


class UriScheme(SimpleGenerator):
    """
    Generate variouse uri scheme's.
    """

    def __init__(self, group=None):
        SimpleGenerator.__init__(self, group)
        self._generator = GeneratorList(None, [
            Static('http'),
            UriSchemeKnown(),
            BadStrings(),
            GoodUnicode(None, BadStrings()),
            BadUnicode(None, BadStrings()),
            RepeaterGI(None, Static('A'), BadUnsignedNumbers16()),
            Static('http')
        ])


class UriAuthority(SimpleGenerator):
    """
    Generate variouse location portions of URI's.
    """

    # authority   = [ userinfo "@" ] host [ ":" port ]

    def __init__(self, group=None):
        SimpleGenerator.__init__(self, group)
        self._generator = GeneratorList(None, [
            Static('localhost'),
            UriHost(),
            Block2([
                UriUserinfo(),
                Static('@localhost')
            ]),
            Block2([
                Static('localhost:'),
                UriPort()
            ]),
            RepeaterGI(None, Static('A'), BadUnsignedNumbers16()),
            Static('localhost'),
        ])


class UriUserinfo(SimpleGenerator):
    def __init__(self, group=None):
        SimpleGenerator.__init__(self, group)
        self._generator = GeneratorList(None, [
            Static('Peach:Ing'),
            BadStrings(),
            Block2([
                BadStrings(),
                Static(':'),
                BadStrings()
            ]),
            RepeaterGI(None, Static('A'), BadUnsignedNumbers16()),
            Static('Peach:Ing'),
        ])


class UriHost(SimpleGenerator):
    # host        = IP-literal / IPv4address / reg-name
    # IP-literal = "[" ( IPv6address / IPvFuture  ) "]"
    # IPvFuture  = "v" 1*HEXDIG "." 1*( unreserved / sub-delims / ":" )
    #
    #   IPv6address =                            6( h16 ":" ) ls32
    #               /                       "::" 5( h16 ":" ) ls32
    #               / [               h16 ] "::" 4( h16 ":" ) ls32
    #               / [ *1( h16 ":" ) h16 ] "::" 3( h16 ":" ) ls32
    #               / [ *2( h16 ":" ) h16 ] "::" 2( h16 ":" ) ls32
    #               / [ *3( h16 ":" ) h16 ] "::"    h16 ":"   ls32
    #               / [ *4( h16 ":" ) h16 ] "::"              ls32
    #               / [ *5( h16 ":" ) h16 ] "::"              h16
    #               / [ *6( h16 ":" ) h16 ] "::"
    #
    #   ls32        = ( h16 ":" h16 ) / IPv4address
    #               ; least-significant 32 bits of address
    #
    #   h16         = 1*4HEXDIG
    #               ; 16 bits of address represented in hexadecimal
    #   IPv4address = dec-octet "." dec-octet "." dec-octet "." dec-octet
    #
    #   dec-octet   = DIGIT                 ; 0-9
    #               / %x31-39 DIGIT         ; 10-99
    #               / "1" 2DIGIT            ; 100-199
    #               / "2" %x30-34 DIGIT     ; 200-249
    #               / "25" %x30-35          ; 250-255
    # reg-name    = *( unreserved / pct-encoded / sub-delims )
    def __init__(self, group=None):
        SimpleGenerator.__init__(self, group)
        self._generator = GeneratorList(None, [
            Static('localhost'),
            BadStrings(),
            BadIpAddress(),
            BadHostname(),
            GoodUnicode(None, BadIpAddress()),
            BadUnicode(None, BadHostname()),
            RepeaterGI(None, Static('A'), BadUnsignedNumbers16()),
            Static('localhost')
        ])


class UriPort(SimpleGenerator):
    # port        = *DIGIT
    def __init__(self, group=None):
        SimpleGenerator.__init__(self, group)
        self._generator = GeneratorList(None, [
            Static('81'),
            BadStrings(),
            RepeaterGI(None, Static('A'), BadUnsignedNumbers16()),
            BadNumbers(),
            Static('81')
        ])


class UriPath(SimpleGenerator):
    """
    Generate variouse resource portions of URI's.  This does
    not include querystrings or id's (#xxx)
    """

    #path          = path-abempty    ; begins with "/" or is empty
    #              / path-absolute   ; begins with "/" but not "//"
    #              / path-noscheme   ; begins with a non-colon segment
    #              / path-rootless   ; begins with a segment
    #              / path-empty      ; zero characters
    #
    #path-abempty  = *( "/" segment )
    #path-absolute = "/" [ segment-nz *( "/" segment ) ]
    #path-noscheme = segment-nz-nc *( "/" segment )
    #path-rootless = segment-nz *( "/" segment )
    #path-empty    = 0<pchar>
    #
    #segment       = *pchar
    #segment-nz    = 1*pchar
    #segment-nz-nc = 1*( unreserved / pct-encoded / sub-delims / "@" )
    #              ; non-zero-length segment without any colon ":"
    #
    #pchar         = unreserved / pct-encoded / sub-delims / ":" / "@"

    def __init__(self, group=None):
        SimpleGenerator.__init__(self, group)
        self._generator = Block2([
            Static('/'),
            GeneratorList(None, [
                Static('AAAAA'),
                BadStrings(),
                GoodUnicode(None, BadStrings()),
                BadUnicode(None, BadStrings()),

                BadIpAddress(),
                BadHostname(),
                BadNumbers(),

                BadPath(),
                GoodUnicode(None, BadPath()),
                BadUnicode(None, BadPath()),

                BadFilename(),
                GoodUnicode(None, BadFilename()),
                BadUnicode(None, BadFilename()),

                Repeater(None, Static('AAAA/'), 10, 100),
                Repeater(None, Static('AAAA/'), 100, 100),
                Repeater(None, Static('AAAA/../'), 20, 100),
                Repeater(None, Static('../AAAA/'), 20, 100),
                RepeaterGI(None, Static('A/'), BadUnsignedNumbers16()),
                Static('AAAAA')
            ])
        ])


class _UriQuery_GenName(SimpleGenerator):
    """
    Helper class to create names for key/value pairs
    """

    def __init__(self, group=None):
        SimpleGenerator.__init__(self, group)
        self._generator = GeneratorList(None, [
            BadStrings(),
            GoodUnicode(None, BadStrings()),
            BadUnicode(None, BadStrings()),

            BadIpAddress(),
            BadHostname(),
            BadNumbers(),

            BadPath(),
            GoodUnicode(None, BadPath()),
            BadUnicode(None, BadPath()),

            BadFilename(),
            GoodUnicode(None, BadFilename()),
            BadUnicode(None, BadFilename())
        ], "_UriQuery_GenName")


class _UriQuery_GenNameAll(SimpleGenerator):
    """
    Helper class to create names for key/value pairs.
    """

    def __init__(self, group=None):
        SimpleGenerator.__init__(self, group)
        self._generator = GeneratorList(None, [
            _UriQuery_GenName(),
            _UriQuery_GenName().setTransformer(UrlEncode()),
            #_UriQuery_GenName().setTransformer( BadUrlEncode())
        ], "_UriQuery_GenNameAll")


class UriQuery(SimpleGenerator):
    """
    Generate querystring's "?k=v&k=v&k=v"
    """

    def __init__(self, group=None):
        SimpleGenerator.__init__(self, group)
        self._generator = Block2([
            GeneratorList(None, [
                Static("?"),
                GoodUnicode(None, Static("?")),
                BadUnicode(None, Static("?")),
                Static("")
            ], "_generator_question-mark"),

            GeneratorList(None, [
                _UriQuery_GenNameAll(),

                GeneratorList(None, [
                    Block2([
                        _UriQuery_GenNameAll(),
                        Static('=')
                    ]),
                    Block2([
                        Static('='),
                        _UriQuery_GenNameAll()
                    ]),
                    Block2([
                        _UriQuery_GenNameAll(),
                        Static('='),
                        _UriQuery_GenNameAll()
                    ])
                ], "_generator_1"),

                Repeater(None, Block2([
                    Static('KEY'),
                    PerCallIncrementor(None, 1, 1),
                    Static('='),
                    Static('VALUE'),
                    PerCallIncrementor(None, 1, 1),
                    Static('&')
                ]), 10, 1000),

                Repeater(None, Block2([
                    Repeater(None, Static('KKKKKKKKK'), 10, 1000),
                    PerCallIncrementor(None, 1, 1),
                    Static('='),
                    Repeater(None, Static('VVVVVVVVV'), 10, 1000),
                    PerCallIncrementor(None, 1, 1),
                    Static('&')
                ]), 10, 1000)
            ], "_generator_2")
        ])


class Uri(SimpleGenerator):
    """
    Generate a gazillion URI's!!
    """

    #   foo://example.com:8042/over/there?name=ferret#nose
    #   \_/   \______________/\_________/ \_________/ \__/
    #    |           |            |            |        |
    # scheme     authority       path        query   fragment

    # formats
    # prot://location/resource/
    # prot://user:pass@location/resource
    # prot://location/reqource#stuff
    # prot://location/resource?key=value&key=value
    # mailto:dd@phed.org
    # tel:xxxx
    # urn:oasis:names:blah:blah:

    def __init__(self, group=None):
        SimpleGenerator.__init__(self, group)

        groupAA = Group()
        groupBB = GroupSequence([Group(), Group()], "UriGroupBB")
        groupCC = GroupSequence([Group(), Group(), Group()], "UriGroupCC")
        groupDD = GroupSequence([Group(), Group(), Group(), Group()], "UriGroupDD")
        groupEE = GroupSequence([Group(), Group(), Group()], "UriGroupED")
        groupFF = GroupSequence([Group(), Group()], "UriGroupFF")

        groupA = GroupSequence([Group(), Group()], "UriGroupA")
        groupB = GroupSequence([Group(), Group(), Group()], "UriGroupB")
        groupC = GroupSequence([Group(), Group(), Group(), Group()], "UriGroupC")
        groupD = GroupSequence([Group(), Group(), Group(), Group(), Group()], "UriGroupD")
        groupE = GroupSequence([Group(), Group(), Group(), Group()], "UriGroupE")
        groupF = GroupSequence([Group(), Group(), Group()], "UriGroupF")

        groupEach = Group()
        groupDo = Group()
        groupForeach = GroupForeachDo(groupEach, groupDo)

        self._generator = GeneratorList(None, [

            # For each known Scheme do some basic fuzzing of each
            # uri component
            Block3(groupForeach, [# Note, groupForeach is incremented by Block3
                                  UriSchemeKnown(groupEach),
                                  GeneratorList2(groupDo, [
                                      groupAA,
                                      groupBB,
                                      groupCC,
                                      groupDD,
                                      groupEE,
                                      groupFF
                                  ], [
                                                     Block([
                                                         Static('://'),
                                                         UriAuthority(groupAA),
                                                     ]),
                                                     Block([
                                                         Static('://'),
                                                         UriAuthority(groupBB[0]),
                                                         UriPath(groupBB[1]),
                                                     ]),
                                                     Block([
                                                         Static('://'),
                                                         UriAuthority(groupCC[0]),
                                                         UriPath(groupCC[1]),
                                                         UriQuery(groupCC[2]),
                                                     ]),
                                                     Block([
                                                         Static('://'),
                                                         UriAuthority(groupDD[0]),
                                                         UriPath(groupDD[1]),
                                                         UriQuery(groupDD[2]),
                                                         UriFragment(groupDD[3])
                                                     ]),
                                                     Block([
                                                         Static('://'),
                                                         UriAuthority(groupEE[0]),
                                                         UriPath(groupEE[1]),
                                                         UriFragment(groupEE[2])
                                                     ]),
                                                     Block([
                                                         Static('://'),
                                                         UriAuthority(groupFF[0]),
                                                         UriFragment(groupFF[1])
                                                     ])
                                                 ])
            ]),

            Block2([
                UriScheme(),
                Static('://localhost')
            ]),

            # Do some scheme fuzzing with other portions fuzzing
            # not sure how usefull this is?
            GeneratorList2(None, [
                groupA,
                groupB,
                groupC,
                groupD,
                groupE,
                groupF
            ], [
                               Block([
                                   UriScheme(groupA[0]),
                                   Static('://'),
                                   UriAuthority(groupA[1]),
                               ]),
                               Block([
                                   UriScheme(groupB[0]),
                                   Static('://'),
                                   UriAuthority(groupB[1]),
                                   UriPath(groupB[2]),
                               ]),
                               Block([
                                   UriScheme(groupC[0]),
                                   Static('://'),
                                   UriAuthority(groupC[1]),
                                   UriPath(groupC[2]),
                                   UriQuery(groupC[3]),
                               ]),
                               Block([
                                   UriScheme(groupD[0]),
                                   Static('://'),
                                   UriAuthority(groupD[1]),
                                   UriPath(groupD[2]),
                                   UriQuery(groupD[3]),
                                   UriFragment(groupD[4])
                               ]),
                               Block([
                                   UriScheme(groupE[0]),
                                   Static('://'),
                                   UriAuthority(groupE[1]),
                                   UriPath(groupE[2]),
                                   UriFragment(groupE[3])
                               ]),
                               Block([
                                   UriScheme(groupF[0]),
                                   Static('://'),
                                   UriAuthority(groupF[1]),
                                   UriFragment(groupF[2])
                               ])
                           ])
        ])


# ############################################################################

import inspect
import pyclbr


def RunUnit(obj, clsName):
    print("Unittests for: %s" % clsName)
    cnt = 0
    try:
        while True:
            s = obj.getValue()
            obj.next()
            cnt += 1

    except GeneratorCompleted:
        print("%d tests found." % cnt)


if __name__ == "__main__":
    print("\n -- Running A Quick Unittest for %s --\n" % __file__)
    mod = inspect.getmodulename(__file__)
    for clsName in pyclbr.readmodule(mod):
        cls = globals()[clsName]
        if str(cls).find('__main__') > -1 and hasattr(cls, 'next') and hasattr(cls, 'getValue'):
            try:
                RunUnit(cls(), clsName)
            except TypeError:
                pass
