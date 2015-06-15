# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
import array
import random
import hashlib
import logging

from Peach.generator import *
from Peach.Generators.data import *
from Peach.Generators.xmlstuff import *
from Peach.Generators import constants
from Peach.mutator import *


class StringCaseMutator(Mutator):
    """
    This mutator changes the case of a string.
    """

    def __init__(self, peach, node):
        Mutator.__init__(self)
        self.isFinite = True
        self.name = "StringCaseMutator"
        self._peach = peach
        self._mutations = [
            self._mutationLowerCase,
            self._mutationUpperCase,
            self._mutationRandomCase,
        ]
        self._count = len(self._mutations)
        self._index = 0

    def next(self):
        self._index += 1
        if self._index >= self._count:
            raise MutatorCompleted()

    def getCount(self):
        return self._count

    @staticmethod
    def supportedDataElement(node):
        if isinstance(node, String) and node.isMutable:
            return True
        return False

    def sequentialMutation(self, node):
        self.changedName = node.getFullnameInDataModel()
        node.currentValue = self._mutations[self._index](node.getInternalValue())

    def randomMutation(self, node, rand):
        self.changedName = node.getFullnameInDataModel()
        node.currentValue = rand.choice(self._mutations)(node.getInternalValue())

    def _mutationLowerCase(self, data):
        return data.lower()

    def _mutationUpperCase(self, data):
        return data.upper()

    def _mutationRandomCase(self, data):
        # Allow us to skip ahead and always get same number
        rand = random.Random()
        rand.seed(hashlib.sha512(str(self._count)).digest())
        if len(data) > 20:
            for i in rand.sample(range(len(data)), 20):
                c = data[i]
                c = rand.choice([c.lower(), c.upper()])
                data = data[:i] + c + data[i + 1:]
            return data
        for i in range(len(data)):
            c = data[i]
            c = rand.choice([c.lower(), c.upper()])
            data = data[:i] + c + data[i + 1:]
        return data


class UnicodeStringsMutator(Mutator):
    """
    This mutator generates unicode strings.
    """
    values = constants.UnicodeStringsMutator

    def __init__(self, peach, node):
        Mutator.__init__(self)
        UnicodeStringsMutator.weight = 2
        self.name = "UnicodeStringsMutator"
        if UnicodeStringsMutator.values is None:
            print("Initialize %s" % self.name)
            self._genValues()

            if Engine.debug:
                fd = open("DEBUG_{}.txt".format(self.name), "wb+")
                for v in self.values:
                    fd.write("\t%s,\n" % repr(v))
                fd.close()

        self.isFinite = True
        self._peach = peach
        self._count = 0
        self._maxCount = len(self.values)

    def _genValues(self):
        if UnicodeStringsMutator.values is None:
            values = []

            sample = random.sample(range(2, 6024), 200)
            sample.append(0)
            sample.append(1024 * 65)

            uchars = range(0, 0xffff)

            for length in sample:
                value = u""
                for i in range(length):
                    value += unichr(random.choice(uchars))
                values.append(value)

            UnicodeStringsMutator.values = values

    def next(self):
        """
        Go to next mutation. When this is called the state machine is updated
        as needed.
        """
        self._count += 1
        if self._count >= self._maxCount:
            self._count -= 1
            raise MutatorCompleted()

    def getCount(self):
        return self._maxCount

    @staticmethod
    def supportedDataElement(node):
        if isinstance(node, String) \
                and node.type != 'ascii' \
                and node.type != 'char' \
                and node.isMutable:
            return True
        return False

    def sequentialMutation(self, node):
        self.changedName = node.getFullnameInDataModel()
        node.currentValue = self.values[self._count]

    def randomMutation(self, node, rand):
        self.changedName = node.getFullnameInDataModel()
        node.currentValue = rand.choice(self.values)


class ValidValuesMutator(Mutator):
    """
    Allows different valid values to be specified.
    """

    def __init__(self, peach, node):
        Mutator.__init__(self)
        ValidValuesMutator.weight = 2
        self.name = "ValidValuesMutator"
        self.values = []
        self._genValues(node)
        self.isFinite = True
        self._peach = peach
        self._count = 0
        self._maxCount = len(self.values)

    def _genValues(self, node):
        self.values = []
        for child in node.hints:
            if child.name == 'ValidValues':
                self.values = child.value.split(';')

    def next(self):
        """
        Go to next mutation. When this is called the state machine is updated
        as needed.
        """
        self._count += 1
        if self._count >= self._maxCount:
            self._count -= 1
            raise MutatorCompleted()

    def getCount(self):
        return self._maxCount

    @staticmethod
    def supportedDataElement(node):
        if (isinstance(node, String)
            or isinstance(node, Number)) and node.isMutable:
            # Look for NumericalString
            for hint in node.hints:
                if hint.name == "ValidValues":
                    return True
        return False

    def sequentialMutation(self, node):
        self.changedName = node.getFullnameInDataModel()
        node.currentValue = self.values[self._count]

    def randomMutation(self, node, rand):
        self.changedName = node.getFullnameInDataModel()
        node.currentValue = rand.choice(self.values)


class UnicodeBomMutator(Mutator):
    """
    Injects BOM markers into default value and longer strings.
    """
    values = constants.UnicodeBomMutator
    boms = ['\xFE\xFF', '\xFF\xEF', '\xEF\xBB\xBF']

    def __init__(self, peach, node):
        Mutator.__init__(self)
        UnicodeBomMutator.weight = 2
        self.name = "UnicodeBomMutator"
        if UnicodeBomMutator.values is None:
            print("Initialize %s" % self.name)
            self._genValues()

            if Engine.debug:
                fd = open("DEBUG_{}.txt".format(self.name), "wb+")
                for v in self.values:
                    fd.write("\t%s,\n" % repr(v))
                fd.close()

        self.isFinite = True
        self._peach = peach
        self._count = 0
        self._maxCount = len(self.values)

    def _genValues(self):
        if UnicodeBomMutator.values is None:
            valuesWithBOM = []
            values = []
            sample = random.sample(range(2, 2024, 2), 200)
            sample.append(0)
            sample.append(1024 * 2)
            for r in sample:
                values.append('A' * r)
            # 1. Prefix with both BOMs
            for v in values:
                for b in self.boms:
                    valuesWithBOM.append(b + v)
            # 2. Every other wchar
            for v in values:
                for b in self.boms:
                    newval = b
                    for i in range(0, len(v), 2):
                        newval += v[i:i + 2]
                        newval += b
                    valuesWithBOM.append(newval)
            # 3. Just BOM's
            for r in sample:
                newval = ""
                for i in range(r):
                    newval += random.choice(self.boms)
                valuesWithBOM.append(newval)
            UnicodeBomMutator.values = valuesWithBOM
            values = None

    def next(self):
        """
        Go to next mutation. When this is called the state machine is updated
        as needed.
        """
        self._count += 1
        if self._count >= self._maxCount:
            self._count -= 1
            raise MutatorCompleted()

    def getCount(self):
        return self._maxCount

    @staticmethod
    def supportedDataElement(node):
        if isinstance(node, String) and node.isMutable:
            return True
        return False

    def sequentialMutation(self, node):
        self.changedName = node.getFullnameInDataModel()
        node.finalValue = self.values[self._count]

    def randomMutation(self, node, rand):
        self.changedName = node.getFullnameInDataModel()
        node.finalValue = rand.choice(self.values)


class UnicodeBadUtf8Mutator(Mutator):
    """
    Generate bad UTF-8 strings.
    """

    values = constants.UnicodeBadUtf8Mutator

    def __init__(self, peach, node):
        Mutator.__init__(self)
        UnicodeBadUtf8Mutator.weight = 2
        self.name = "UnicodeBadUtf8Mutator"
        if UnicodeBadUtf8Mutator.values is None:
            print("Initialize %s" % self.name)
            self._genValues()

            if Engine.debug:
                fd = open("DEBUG_{}.txt".format(self.name), "wb+")
                for v in self.values:
                    fd.write("\t%s,\n" % repr(v))
                fd.close()

        self.isFinite = True
        self._peach = peach
        self._count = 0
        self._maxCount = len(self.values)

    def _genValues(self):
        if UnicodeBadUtf8Mutator.values is None:
            encoding = [
                self._utf8OneByte,
                self._utf8TwoByte,
                self._utf8ThreeByte,
                self._utf8FourByte,
                self._utf8FiveByte,
                self._utf8SixByte,
                self._utf8SevenByte
            ]
            endValues = []
            sample = random.sample(range(2, 2024, 2), 100)
            sample.append(2024)
            for s in random.sample(range(2, 100), 50):
                sample.append(s)
            ascii = range(32, 126)
            for r in sample:
                value = ""
                for i in range(r):
                    value += random.choice(encoding)(random.choice(ascii))
                endValues.append(value)
            UnicodeBadUtf8Mutator.values = endValues

    def _utf8OneByte(self, c):
        return struct.pack("!B", c)

    def binaryFormatter(self, num, bits=None, strip=False):
        if bits is None:
            bits = 64
            strip = True
        if type(num) == str:
            raise Exception("Strings not permitted")
        ret = ""
        for i in range(bits - 1, -1, -1):
            ret += str((num >> i) & 1)
        if strip:
            return ret.lstrip('0')
        return ret

    def _utf8TwoByte(self, c, mask='1100000010000000'):
        bfC = self.binaryFormatter(c)
        if len(bfC) > 11:
            raise Exception("Larger than two byte UTF-8")
        bfC = self.binaryFormatter(c, 11)
        bf = array.array('c', mask)
        bf[3:8] = array.array('c', bfC[0:5])
        bf[10:16] = array.array('c', bfC[5:])
        bfs = bf.tostring()
        return struct.pack("!BB", int(bfs[0:8], 2), int(bfs[8:16], 2))

    def _utf8ThreeByte(self, c, mask='111000001000000010000000'):
        bfC = self.binaryFormatter(c)
        if len(bfC) > 16:
            raise Exception("Larger than three byte UTF-8")
        bfC = self.binaryFormatter(c, 16)
        bf = array.array('c', mask)
        bf[4:8] = array.array('c', bfC[:4])
        bf[10:16] = array.array('c', bfC[4:10])
        bf[18:24] = array.array('c', bfC[10:])
        bfs = bf.tostring()
        return struct.pack("!BBB",
                           int(bfs[0:8], 2),
                           int(bfs[8:16], 2),
                           int(bfs[16:24], 2))

    def _utf8FourByte(self, c, mask='11110000100000001000000010000000'):
        bfC = self.binaryFormatter(c)
        if len(bfC) > 21:
            raise Exception("Larger than four byte UTF-8")
        bfC = self.binaryFormatter(c, 21)
        bf = array.array('c', mask)
        bf[5:8] = array.array('c', bfC[:3])
        bf[10:16] = array.array('c', bfC[3:9])
        bf[18:24] = array.array('c', bfC[9:15])
        bf[26:32] = array.array('c', bfC[15:])
        bfs = bf.tostring()
        return struct.pack("!BBBB",
                           int(bfs[0:8], 2),
                           int(bfs[8:16], 2),
                           int(bfs[16:24], 2),
                           int(bfs[24:32], 2))

    def _utf8FiveByte(self, c, mask='1111100010000000100000001000000010000000'):
        bfC = self.binaryFormatter(c)
        if len(bfC) > 26:
            raise Exception("Larger than five byte UTF-8")
        bfC = self.binaryFormatter(c, 26)
        bf = array.array('c', mask)
        bf[6:8] = array.array('c', bfC[:2])
        bf[10:16] = array.array('c', bfC[2:8])
        bf[18:24] = array.array('c', bfC[8:14])
        bf[26:32] = array.array('c', bfC[14:20])
        bf[34:40] = array.array('c', bfC[20:])
        bfs = bf.tostring()
        return struct.pack("!BBBBB",
                           int(bfs[0:8], 2),
                           int(bfs[8:16], 2),
                           int(bfs[16:24], 2),
                           int(bfs[24:32], 2),
                           int(bfs[32:40], 2))

    def _utf8SixByte(self, c, mask='111111001000000010000000100000001000000010000000'):
        bfC = self.binaryFormatter(c)
        if len(bfC) > 31:
            raise Exception("Larger than six byte UTF-8")
        bfC = self.binaryFormatter(c, 31)
        bf = array.array('c', mask)
        bf[7] = bfC[0]
        bf[10:16] = array.array('c', bfC[1:7])
        bf[18:24] = array.array('c', bfC[7:13])
        bf[26:32] = array.array('c', bfC[13:19])
        bf[34:40] = array.array('c', bfC[19:25])
        bf[42:48] = array.array('c', bfC[25:31])
        bfs = bf.tostring()
        return struct.pack("!BBBBBB",
                           int(bfs[0:8], 2),
                           int(bfs[8:16], 2),
                           int(bfs[16:24], 2),
                           int(bfs[24:32], 2),
                           int(bfs[32:40], 2),
                           int(bfs[40:48], 2))

    def _utf8SevenByte(self, c, mask='11111110100000001000000010000000100000001000000010000000'):
        bfC = self.binaryFormatter(c, 36)
        bf = array.array('c', mask)
        bf[10:16] = array.array('c', bfC[:6])
        bf[18:24] = array.array('c', bfC[6:12])
        bf[26:32] = array.array('c', bfC[12:18])
        bf[34:40] = array.array('c', bfC[18:24])
        bf[42:48] = array.array('c', bfC[24:30])
        bf[50:56] = array.array('c', bfC[30:])
        bfs = bf.tostring()
        return struct.pack("!BBBBBBB",
                           int(bfs[0:8], 2),
                           int(bfs[8:16], 2),
                           int(bfs[16:24], 2),
                           int(bfs[24:32], 2),
                           int(bfs[32:40], 2),
                           int(bfs[40:48], 2),
                           int(bfs[48:], 2))

    def next(self):
        """
        Go to next mutation. When this is called the state machine is updated
        as needed.
        """
        self._count += 1
        if self._count >= self._maxCount:
            self._count -= 1
            raise MutatorCompleted()

    def getCount(self):
        return self._maxCount + 1

    @staticmethod
    def supportedDataElement(node):
        if isinstance(node, String) and node.isMutable \
                and node.type != 'wchar':
            return True
        return False

    def sequentialMutation(self, node):
        self.changedName = node.getFullnameInDataModel()
        node.finalValue = self.values[self._count]

    def randomMutation(self, node, rand):
        self.changedName = node.getFullnameInDataModel()
        node.finalValue = rand.choice(self.values)


class UnicodeUtf8ThreeCharMutator(UnicodeBadUtf8Mutator):
    """
    Generate long UTF-8 three byte strings
    """

    values = constants.UnicodeUtf8ThreeCharMutator

    def __init__(self, peach, node):
        UnicodeBadUtf8Mutator.__init__(self, peach, node)
        UnicodeUtf8ThreeCharMutator.weight = 2
        self.name = "UnicodeUtf8ThreeCharMutator"

        if UnicodeUtf8ThreeCharMutator.values is None:
            print("Initialize %s" % self.name)
            self._genValues()

            if Engine.debug:
                fd = open("DEBUG_{}.txt".format(self.name), "wb+")
                for v in self.values:
                    fd.write("\t%s,\n" % repr(v))
                fd.close()

    def _genValues(self):
        if UnicodeUtf8ThreeCharMutator.values is None:
            endValues = []
            sample = random.sample(range(2, 1024, 2), 300)
            sample.append(1024)
            # 1. Three char encoded values (can cause odd overflows)
            for r in sample:
                s = self._utf8ThreeByte(0xf0f0)
                endValues.append(s * r)
            UnicodeUtf8ThreeCharMutator.values = endValues


class _SimpleGeneratorMutator(Mutator):
    """
    Base class for other mutators that use a generator.
    """

    def __init__(self, peach, node):
        Mutator.__init__(self)
        self.isFinite = True
        self._peach = peach
        self._count = None
        self._generator = None

    def next(self):
        """
        Go to next mutation. When this is called the state machine is updated
        as needed.
        """
        try:
            self._generator.next()
        except GeneratorCompleted:
            raise MutatorCompleted()

    def getCount(self):
        return self._count

    @staticmethod
    def supportedDataElement(node):
        if isinstance(node, String) and node.isMutable:
            return True
        return False

    def sequentialMutation(self, node):
        self.changedName = node.getFullnameInDataModel()
        node.currentValue = self._generator.getValue()

    def randomMutation(self, node, rand):
        """
        TODO: This is slow, we should speed it up
        """
        self.changedName = node.getFullnameInDataModel()
        count = rand.randint(0, self._count - 1)
        gen = BadStrings()
        try:
            for i in range(count):
                gen.next()
        except GeneratorCompleted:
            pass
        node.currentValue = gen.getValue()


class StringMutator(Mutator):
    """
    Apply StringFuzzer to each string node in DDT one Node at a time.
    """

    values = constants.StringMutator

    def __init__(self, peach, node):
        Mutator.__init__(self)
        StringMutator.weight = 3
        self.name = "StringMutator"
        if StringMutator.values is None:
            print("Initialize {}".format(self.name))
            self._genValues()
        self.isFinite = True
        self._peach = peach
        self._count = 0
        self._maxCount = len(self.values)

    def _genValues(self):
        values = []
        sample = random.sample(range(0, 6024), 200)
        sample.append(1024 * 65)
        uchars = range(0, 0xffff)
        for length in sample:
            value = u""
            for _ in range(length):
                value += unichr(random.choice(uchars))
            values.append(value)
        StringMutator.values = values

    def next(self):
        """
        Go to next mutation. When this is called the state machine is updated
        as needed.
        """
        self._count += 1
        if self._count >= self._maxCount:
            self._count -= 1
            raise MutatorCompleted()

    def getCount(self):
        return self._maxCount

    @staticmethod
    def supportedDataElement(node):
        if isinstance(node, String) and node.isMutable:
            return True
        return False

    def sequentialMutation(self, node):
        self.changedName = node.getFullnameInDataModel()
        node.currentValue = self.values[self._count]

    def randomMutation(self, node, rand):
        self.changedName = node.getFullnameInDataModel()
        node.currentValue = rand.choice(self.values)


class XmlW3CMutator(_SimpleGeneratorMutator):
    """
    Example: <String><Hint name="type" value="xml"></String>
    """

    def __init__(self, peach, node):
        _SimpleGeneratorMutator.__init__(self, peach, node)
        XmlW3CMutator.weight = 2
        self.name = "XmlW3CMutator"
        self._generator = XmlParserTests(None)
        gen = XmlParserTests(None)
        try:
            self._count = 0
            while True:
                self._count += 1
                gen.next()
        except GeneratorCompleted:
            pass

    @staticmethod
    def supportedDataElement(node):
        if isinstance(node, String) and node.isMutable:
            for child in node.hints:
                if child.name == 'type' and child.value == 'xml':
                    return True
        return False


class PathMutator(_SimpleGeneratorMutator):
    """
    Example: <String><Hint name="type" value="path"></String>
    """

    def __init__(self, peach, node):
        _SimpleGeneratorMutator.__init__(self, peach, node)
        PathMutator.weight = 2
        self.name = "PathMutator"
        self._generator = BadPath(None)
        gen = BadPath(None)
        try:
            self._count = 0
            while True:
                self._count += 1
                gen.next()
        except GeneratorCompleted:
            pass

    @staticmethod
    def supportedDataElement(node):
        if isinstance(node, String) and node.isMutable:
            for child in node.hints:
                if child.name == 'type' and child.value == 'path':
                    return True
        return False


class HostnameMutator(_SimpleGeneratorMutator):
    """
    Example: <String><Hint name="type" value="hostname"></String>
    """

    def __init__(self, peach, node):
        _SimpleGeneratorMutator.__init__(self, peach, node)
        HostnameMutator.weight = 2
        self.name = "HostnameMutator"
        self._generator = BadHostname(None)
        gen = BadHostname(None)
        try:
            self._count = 0
            while True:
                self._count += 1
                gen.next()
        except GeneratorCompleted:
            pass

    @staticmethod
    def supportedDataElement(node):
        if isinstance(node, String) and node.isMutable:
            for child in node.hints:
                if child.name == 'type' and child.value == 'hostname':
                    return True

        return False


class IpAddressMutator(_SimpleGeneratorMutator):
    """
    Example: <String><Hint name="type" value="ipaddress"></String>
    """

    def __init__(self, peach, node):
        _SimpleGeneratorMutator.__init__(self, peach, node)
        IpAddressMutator.weight = 2
        self.name = "IpAddressMutator"
        self._generator = BadIpAddress(None)
        gen = BadIpAddress(None)
        try:
            self._count = 0
            while True:
                self._count += 1
                gen.next()
        except GeneratorCompleted:
            pass

    @staticmethod
    def supportedDataElement(node):
        if isinstance(node, String) and node.isMutable:
            for child in node.hints:
                if child.name == 'type' and child.value == 'ipaddress':
                    return True
        return False


class TimeMutator(_SimpleGeneratorMutator):
    """
    Example: <String><Hint name="type" value="time"></String>
    """

    def __init__(self, peach, node):
        _SimpleGeneratorMutator.__init__(self, peach, node)
        TimeMutator.weight = 2
        self.name = "TimeMutator"
        self._generator = BadTime(None)
        gen = BadTime(None)
        try:
            self._count = 0
            while True:
                self._count += 1
                gen.next()
        except GeneratorCompleted:
            pass

    @staticmethod
    def supportedDataElement(node):
        if isinstance(node, String) and node.isMutable:
            for child in node.hints:
                if child.name == 'type' and child.value == 'time':
                    return True
        return False


class DateMutator(_SimpleGeneratorMutator):
    """
    Example: <String><Hint name="type" value="date"></String>
    """

    def __init__(self, peach, node):
        _SimpleGeneratorMutator.__init__(self, peach, node)
        HostnameMutator.weight = 2
        self.name = "DateMutator"
        self._generator = BadDate(None)
        gen = BadDate(None)
        try:
            self._count = 0
            while True:
                self._count += 1
                gen.next()
        except GeneratorCompleted:
            pass

    @staticmethod
    def supportedDataElement(node):
        if isinstance(node, String) and node.isMutable:
            for child in node.hints:
                if child.name == 'type' and child.value == 'date':
                    return True
        return False


class FilenameMutator(_SimpleGeneratorMutator):
    """
    Example: <String><Hint name="type" value="filename"></String>
    """

    def __init__(self, peach, node):
        _SimpleGeneratorMutator.__init__(self, peach, node)
        FilenameMutator.weight = 2
        self.name = "FilenameMutator"
        self._generator = BadFilename(None)
        gen = BadFilename(None)
        try:
            self._count = 0
            while True:
                self._count += 1
                gen.next()
        except GeneratorCompleted:
            pass

    @staticmethod
    def supportedDataElement(node):
        if isinstance(node, String) and node.isMutable:
            for child in node.hints:
                if child.name == 'type' and child.value == 'filename':
                    return True
        return False
