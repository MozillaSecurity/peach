# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
import struct
import hashlib
import imp
import random
from re import findall

from Peach.mutator import *
from Peach.Engine.common import *


class DWORDSliderMutator(Mutator):
    """
    Slides a DWORD through the blob.

    @author Chris Clark
    """

    def __init__(self, peach, node):
        Mutator.__init__(self)
        DWORDSliderMutator.weight = 2
        self.isFinite = True
        self.name = "DWORDSliderMutator"
        self._peach = peach
        self._curPos = 0
        self._len = len(node.getInternalValue())
        self._position = 0
        self._dword = 0xFFFFFFFF
        self._counts = 0

    def next(self):
        self._position += 1
        if self._position >= self._len:
            raise MutatorCompleted()

    def getCount(self):
        return self._len

    @staticmethod
    def supportedDataElement(e):
        if (isinstance(e, Blob) or isinstance(e, Template)) and e.isMutable:
            for child in e.hints:
                if child.name == 'DWORDSliderMutator' and child.value == 'off':
                    return False
            return True
        return False

    def sequentialMutation(self, node):
        self.changedName = node.getFullnameInDataModel()
        self._performMutation(node, self._position)

    def randomMutation(self, node, rand):
        self.changedName = node.getFullnameInDataModel()
        count = rand.randint(0, self._len - 1)
        self._performMutation(node, count)

    def _performMutation(self, node, position):
        data = node.getInternalValue()
        length = len(data)
        if position >= length:
            return
        inject = ''
        remaining = length - position
        if remaining == 1:
            inject = struct.pack('B', self._dword & 0x000000FF)
        elif remaining == 2:
            inject = struct.pack('H', self._dword & 0x0000FFFF) #ushort
        elif remaining == 3:
            inject = struct.pack('B', (self._dword & 0x00FF0000) >> 16) + \
                struct.pack('>H', self._dword & 0xFFFF)
        else:
            inject = struct.pack('L', self._dword)
        node.currentValue = \
            data[:position] + inject + data[position + len(inject):]


class BitFlipperMutator(Mutator):
    """
    Flip a % of total bits in blob. Default % is 20.
    """

    def __init__(self, peach, node):
        Mutator.__init__(self)
        BitFlipperMutator.weight = 3
        self.isFinite = True
        self.name = "BitFlipperMutator"
        self._peach = peach
        self._n = self._getN(node, None)
        self._current = 0
        self._len = len(node.getInternalValue())
        if self._n is not None:
            self._count = self._n
        else:
            self._count = int((len(node.getInternalValue()) * 8) * 0.2)

    def _getN(self, node, n):
        for c in node.hints:
            if c.name == 'BitFlipperMutator-N':
                try:
                    n = int(c.value)
                except:
                    raise PeachException("Expected numerical value for Hint "
                                         "named [{}]".format(c.name))
        return n

    def next(self):
        self._current += 1
        if self._current > self._count:
            raise MutatorCompleted()

    def getCount(self):
        return self._count

    @staticmethod
    def supportedDataElement(e):
        if (isinstance(e, Blob) or isinstance(e, Template)) and e.isMutable:
            return True
        return False

    def sequentialMutation(self, node):
        # Allow us to skip ahead and always get same number
        rand = random.Random()
        rand.seed(hashlib.sha512(str(self._current)).digest())
        self.changedName = node.getFullnameInDataModel()
        data = node.getInternalValue()
        for i in range(rand.randint(0, 10)):
            if self._len - 1 <= 0:
                count = 0
            else:
                count = rand.randint(0, self._len - 1)
            data = self._performMutation(data, count, rand)
        node.currentValue = data

    def randomMutation(self, node, rand):
        self.changedName = node.getFullnameInDataModel()
        data = node.getInternalValue()
        for i in range(rand.randint(0, 10)):
            if self._len - 1 <= 0:
                count = 0
            else:
                count = rand.randint(0, self._len - 1)
            data = self._performMutation(data, count, rand)
        node.currentValue = data

    def _performMutation(self, data, position, rand):
        length = len(data)
        if len(data) == 0:
            return data
        # How many bytes to change
        size = rand.choice([1, 2, 4, 8])
        if (position + size) >= length:
            position = length - size
        if position < 0:
            position = 0
        if size > length:
            size = length
        for i in range(position, position + size):
            byte = struct.unpack('B', data[i])[0]
            byte ^= rand.randint(0, 255)
            packedup = struct.pack("B", byte)
            data = data[:i] + packedup + data[i + 1:]
        return data


class BlobMutator(BitFlipperMutator):
    """
    This mutator will do more types of changes than BitFlipperMutator
    currently can perform. We will grow the Blob, shrink the blob, etc.
    """

    def __init__(self, peach, node):
        BitFlipperMutator.__init__(self, peach, node)
        self.name = "BlobMutator"

    def sequentialMutation(self, node):
        # Allow us to skip ahead and always get same number
        rand = random.Random()
        rand.seed(hashlib.sha512(str(self._current)).digest())
        self.changedName = node.getFullnameInDataModel()
        node.currentValue = self._performMutation(node, rand)

    def randomMutation(self, node, rand):
        self.changedName = node.getFullnameInDataModel()
        node.currentValue = self._performMutation(node, rand)

    def getRange(self, size, rand):
        start = rand.randint(0, size)
        end = rand.randint(0, size)
        if start > end:
            return end, start
        return start, end

    def getPosition(self, rand, size, length=0):
        pos = rand.randint(0, size - length)
        return pos

    def _performMutation(self, node, rand):
        data = node.getInternalValue()
        func = rand.choice([
            self.changeExpandBuffer,
            self.changeReduceBuffer,
            self.changeChangeRange,
            self.changeChangeRangeSpecial,
            self.changeNullRange,
            self.changeUnNullRange,
        ])
        return func(data, rand)

    def changeExpandBuffer(self, data, rand):
        """
        Expand the size of our buffer
        """
        size = rand.randint(0, 255)
        pos = self.getPosition(rand, size)
        return data[:pos] + self.generateNewBytes(size, rand) + data[pos:]

    def changeReduceBuffer(self, data, rand):
        """
        Reduce the size of our buffer
        """
        (start, end) = self.getRange(len(data), rand)
        return data[:start] + data[end:]

    def changeChangeRange(self, data, rand):
        """
        Change a sequence of bytes in our buffer
        """
        (start, end) = self.getRange(len(data), rand)
        if end > (start + 100):
            end = start + 100
        for i in range(start, end):
            data = data[:i] + chr(rand.randint(0, 255)) + data[i + 1:]
        return data

    def changeChangeRangeSpecial(self, data, rand):
        """
        Change a sequence of bytes in our buffer to some special chars.
        """
        special = ["\x00", "\x01", "\xfe", "\xff"]
        (start, end) = self.getRange(len(data), rand)
        if end > (start + 100):
            end = start + 100
        for i in range(start, end):
            data = data[:i - 1] + rand.choice(special) + data[i:]
        return data

    def changeNullRange(self, data, rand):
        """
        Change a range of bytes to null.
        """
        (start, end) = self.getRange(len(data), rand)
        if end > (start + 100):
            end = start + 100
        for i in range(start, end):
            data = data[:i - 1] + chr(0) + data[i:]
        return data

    def changeUnNullRange(self, data, rand):
        """
        Change all zero's in a range to something else.
        """
        (start, end) = self.getRange(len(data), rand)
        if end > (start + 100):
            end = start + 100
        for i in range(start, end):
            if ord(data[i]) == 0:
                data = data[:i - 1] + chr(rand.randint(1, 255)) + data[i:]
        return data

    # ######################################

    def generateNewBytes(self, size, rand):
        """
        Generate new bytes to inject into Blob.
        """
        func = rand.choice([
            self.GenerateNewBytesSingleRandom,
            self.GenerateNewBytesIncrementing,
            self.GenerateNewBytesZero,
            self.GenerateNewBytesAllRandom,
        ])
        return func(size, rand)

    def GenerateNewBytesSingleRandom(self, size, rand):
        """
        Generate a buffer of size bytes, each byte is the same random number.
        """
        return chr(rand.randint(0, 255)) * size

    def GenerateNewBytesIncrementing(self, size, rand):
        """
        Generate a buffer of size bytes, each byte is incrementing from a
        random start.
        """
        buff = ""
        x = rand.randint(0, size)
        for i in range(0, size):
            if i + x > 255:
                return buff
            buff += chr(i + x)
        return buff

    def GenerateNewBytesZero(self, size, rand):
        """
        Generate a buffer of size bytes, each byte is zero (NULL).
        """
        return "\0" * size

    def GenerateNewBytesAllRandom(self, size, rand):
        """
        Generate a buffer of size bytes, each byte is randomly generated.
        """
        buff = ""
        for i in range(size):
            buff += chr(rand.randint(0, 255))
        return buff


class BlobSpread(Mutator):
    def __init__(self, peach, node):
        Mutator.__init__(self)
        self.name = "BlobSpread"
        self.isFinite = True
        self._peach = peach

        # File-length variables
        self._len = len(node.getInternalValue())
        self._position = 0

        self._cumulatedOffsetLength = -1

        # TODO: Bug in Peach core?
        # Works only if --seed is provided
        self._rand = random.Random()
        self._rand.seed(float(self._peach.SEED))

        # Default Hint values
        self._endian = '<'
        self._typeOfValues = "custom"
        self._validValues = [[0, 255]]
        self._maxRandomLength = 4
        self._offsets = [[0, self._len - 1]]
        self._modCustomValues = None
        self._allowedValues = ["8bit"]
        self._mutationMode = None
        self._lookRange = 4

        # Setup Hints
        self._parseHintMutatorAttributes(node)
        self._parseHintTypeOfValues(node)
        self._parseHintValidValues(node)
        self._parseHintMaxRandomLength(node)
        self._parseHintOffsets(node)
        self._parseHintValueFile(node)
        self._parseHintValueFilter(node)

        self._adjustLength()

        self._customValues = self._setCustomValues()
        self._nextCustomValue = 0
        # Initialize offset deliverer for sequential mode
        """ self._nextOffset = self._getNextOffset()
        try:
            self._position = self._nextOffset.next()
        except StopIteration:
            print "INFO: self._position is 0 and self._len is 1."
            raise MutatorCompleted()
        """

    # Gets only called in sequential mode
    def next(self):
        if self._typeOfValues == "custom":
            self._nextCustomValue += 1
            if self._nextCustomValue == len(self._customValues):
                self._nextCustomValue = 0
                try:
                    self._position = self._nextOffset.next()
                except StopIteration:
                    raise MutatorCompleted()

        if self._typeOfValues == "random":
            try:
                self._position = self._nextOffset.next()
            except StopIteration:
                raise MutatorCompleted()

    # Get only called in sequential mode
    def getCount(self):
        if self._typeOfValues == "random":
            return self._cumulatedOffsetLength
        return self._cumulatedOffsetLength * len(self._customValues)

    @staticmethod
    def supportedDataElement(node):
        if isinstance(node, Blob) and node.isMutable:
            for child in node.hints:
                if child.name == 'BlobSpread' and child.value == 'on':
                    return True
            if node.get_Name().startswith("BlobSpread"):
                return True
        return False

    # Gets chosen by the provided mutation strategy
    def sequentialMutation(self, node):
        self._mutationMode = "sequential"

        self.changedName = node.getFullnameInDataModel()

        # self._predictString(data, offset, self._lookRange)

        if self._typeOfValues == "custom":
            value = self._customValues[self._nextCustomValue]
        elif self._typeOfValues == "random":
            value = self._setRandomValue(self._rand)
        else:
            raise NotImplementedError(
                "Sequential mode doesn't support %s as ValuesType Hint." % self._typeOfValues)

        offset = self._position
        self._performMutation(node, offset, value)

    # Gets chosen by the provided mutation strategy
    def randomMutation(self, node, rand):
        self._mutationMode = "random"

        self.changedName = node.getFullnameInDataModel()

        # self._predictString(data, offset, self._lookRange)

        if self._typeOfValues == "custom":
            value = rand.choice(self._customValues)
        elif self._typeOfValues == "random":
            value = self._setRandomValue(rand)
        else:
            raise NotImplementedError(
                "Random mode doesn't support %s as ValuesType Hint." % self._typeOfValues)

        offset = self._getRandomOffset(rand)
        self._performMutation(node, offset, value)

    def _performMutation(self, node, offset, value):
        print("Seed: {}".format(self._peach.SEED))

        print("File: {}".format(self._getFilenameInAction(node)))
        data = node.getInternalValue()

        value_hex = self._hexdump(value)

        print("Offsets in queue: {}/{}"
              .format(self._cumulatedOffsetLength, self._len))
        print("Exchange value at position {}/{} with: {}"
              .format(offset, self._len, value_hex))

        node.currentValue = data[:offset] + value + data[offset + len(value):]

    def _getFilenameInAction(self, node):
        for n in dir(node):
            if n == "parent":
                return self._getFilenameInAction(node.parent)
            if n == "data":
                return node.data.fileName

    def _hexdump(self, value):
        dump = []
        for v in value:
            vhex = hex(ord(v))[2:]
            if len(vhex) == 1:
                dump.append("0" + vhex)
            else:
                dump.append(vhex)
        return " ".join(dump).upper()

    def _parseHintValidValues(self, node):
        for child in node.hints:
            if child.name == "ValidValues":
                pairs = findall("(\d+):(\d+)", child.value)
                self._validValues = [(int(i), int(j)) for i, j in pairs]

    def _parseHintTypeOfValues(self, node):
        for child in node.hints:
            if child.name == "ValuesType":
                self._typeOfValues = child.value

    def _parseHintMutatorAttributes(self, node):
        for child in node.hints:
            if child.name == "Endian":
                if child.value == "little":
                    self._endian = '<'
                if child.value == "big":
                    self._endian = '>'

    def _parseHintMaxRandomLength(self, node):
        for child in node.hints:
            if child.name == "MaxRandomLength":
                self._maxRandomLength = int(child.value)

    def _parseHintOffsets(self, node):
        for child in node.hints:
            if child.name == "Offsets":
                pairs = findall("(\d+):(\-?\d+)", child.value)
                self._offsets = [[int(i), int(j)] for i, j in pairs]

    def _parseHintValueFile(self, node):
        for child in node.hints:
            if child.name == "ValueFile":
                self._modCustomValues = imp.load_source("values", child.value)

    def _parseHintValueFilter(self, node):
        for child in node.hints:
            if child.name == "ValueFilter":
                self._allowedValues = child.value.split(";")

    def _parseHintStringPredictionRange(self, node):
        for child in node.hints:
            if child.name == "StringPredictionRange":
                self._lookRange = int(child.value)

    def _setCustomValues(self):
        values = []
        for v in filter(lambda x: x[0] in self._allowedValues, self._modCustomValues.CustomValues):
            if v[1]:
                if self._endian == ">":
                    values += self._modCustomValues.CustomValues[v][::-1]
                if self._endian == "<":
                    values += self._modCustomValues.CustomValues[v]
            else:
                values += self._modCustomValues.CustomValues[v]
        return values

    def _setRandomValue(self, rand):
        v = ""
        for size in range(rand.randint(1, self._maxRandomLength)):
            i, j = rand.choice(self._validValues)
            v += chr(rand.randint(i, j))
        return v

    def _adjustLength(self):
        if len(self._offsets) == 1 and self._offsets[0][1] == -1:
            self._offsets[0][1] = self._len - 1
        self._cumulatedOffsetLength = sum([i[1] - i[0] for i in self._offsets])

    def _getRandomOffset(self, rand):
        return rand.randint(*rand.choice(self._offsets))

    def _getNextOffset(self):
        for j in self._offsets:
            for i in range(*j):
                yield i

    def _predictString(self, data, position, lookRange):
        isString = False
        for i in range(lookRange):
            ch = ord(data[position + i])
            if (48 <= ch <= 57) or (65 <= ch <= 90) or (97 <= ch <= 122):
                isString = True
                continue
            else:
                break
        return isString


if __name__ == '__main__':
    data = "skaldjalskjdlaskjdlaskjdlaksjdlaksjdlkajsdlkajsdljaslkdjalskdjalskdjalskjdlaksjdlakjsd"
    b = BlobMutator(None, None)
    b.changeExpandBuffer(data)
    b.changeReduceBuffer(data)
    b.changeChangeRange(data)
    b.changeChangeRangeSpecial(data)
    b.changeNullRange(data)
    b.changeUnNullRange(data)
