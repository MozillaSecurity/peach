# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
import random
import string
import re
import time

from Peach.fixup import Fixup


class Uppercase(Fixup):

    def __init__(self, ref):
        Fixup.__init__(self)
        self.ref = ref

    def fixup(self):
        stuff = self.context.findDataElementByName(self.ref).getValue()
        if stuff is None:
            raise Exception("Error: Uppercase was unable to locate "
                            "[{}].".format(self.ref))
        return stuff.upper()


class Escape(Fixup):

    def __init__(self, ref):
        Fixup.__init__(self)
        self.ref = ref

    def fixup(self):
        stuff = self.context.findDataElementByName(self.ref).getValue()
        if stuff is None:
            raise Exception("Error: Escape was unable to locate "
                            "[{}].".format(self.ref))
        return '"' + stuff + '"'


class LogicalField(Fixup):

    def __init__(self, values, listsep="; ", unitsep=","):
        Fixup.__init__(self)
        self.values = values
        self.listsep = listsep
        self.unitsep = unitsep

    def fixup(self):
        values = string.split(self.values, self.listsep)
        if values is None:
            raise Exception("Error: LogicalField was unable to locate its "
                            "values.")
        rndIndex = random.randint(0, len(values) - 1)
        rndValue = string.split(values[rndIndex], self.unitsep)
        if rndValue[0] == "String":
            return TranslateHexDigits(rndValue[1])
        if rndValue[0] == "Number":
            return int(rndValue[1], 16)
        return TranslateHexDigits(rndValue[1])


class RandomField(Fixup):

    def __init__(self, minlen, maxlen, fieldtype):
        Fixup.__init__(self)
        self.minlen = minlen
        self.maxlen = maxlen
        self.fieldtype = fieldtype

    def fixup(self):
        minlen = self.minlen
        maxlen = self.maxlen
        if minlen is None:
            raise Exception("Error: RandomField was unable to locate minlen.")
        if maxlen is None:
            raise Exception("Error: RandomField was unable to locate maxlen.")
        if int(minlen) > int(maxlen):
            raise Exception("Error: minlen ({}) > maxlen ({})."
                            .format(minlen, maxlen))
        value = ""
        length = random.randint(int(minlen), int(maxlen))
        if self.fieldtype == "String":
            for _ in range(length):
                value += random.choice(string.printable)
        elif self.fieldtype == "Number":
            for _ in range(length):
                value += random.choice(string.digits)
        else:
            for _ in range(length):
                value += random.choice(string.hexdigits)
            value = TranslateHexDigits(value)
        return value


class Padding(Fixup):

    def __init__(self, ref):
        Fixup.__init__(self)
        self.ref = ref

    def fixup(self):
        ref = self.context.findDataElementByName(self.ref)
        stuff = ref.getValue()
        if stuff is None:
            raise Exception("Error: PaddingFixup was unable to locate "
                            "[{}]".format(self.ref))
        x = len(stuff) % 4
        return x * "\x00" if x == 0 else (4 - x) * "\x00"


def TranslateHexDigits(value):
    regsHex = (
        re.compile(r"^([,\s]*\\x([a-zA-Z0-9]{2})[,\s]*)"),
        re.compile(r"^([,\s]*%([a-zA-Z0-9]{2})[,\s]*)"),
        re.compile(r"^([,\s]*0x([a-zA-Z0-9]{2})[,\s]*)"),
        re.compile(r"^([,\s]*x([a-zA-Z0-9]{2})[,\s]*)"),
        re.compile(r"^([,\s]*([a-zA-Z0-9]{2})[,\s]*)")
    )
    ret = ""
    valueLen = len(value) + 1
    while valueLen > len(value):
        valueLen = len(value)
        for i in range(len(regsHex)):
            match = regsHex[i].search(value)
            if match is not None:
                while match is not None:
                    ret += chr(int(match.group(2), 16))
                    value = regsHex[i].sub('', value)
                    match = regsHex[i].search(value)
                break
    return ret


class Timestamp(Fixup):

    def __init__(self, ref):
        Fixup.__init__(self)
        self.ref = ref

    def fixup(self):
        ref = self.context.findDataElementByName(self.ref)
        stuff = ref.getValue()
        if stuff is None:
            raise Exception("Error: Timestamp Fixup was unable to locate "
                            "[{}]" % self.ref)
        values = time.strftime("%y %m %d %H %M %S %z",
                               time.gmtime()).split(" ")
        x = 0
        if values[-1][0] == "+":
            x = 0
        if values[-1][0] == "-":
            x = 1
        values[-1] = "%02d" % (int(values[-1][1:3]) | x << 3)
        s = ""
        for i in values:
            s += i[::-1]
        s = s.decode("hex")
        return s
