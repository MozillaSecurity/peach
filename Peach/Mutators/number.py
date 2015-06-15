# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
import random
import hashlib

from Peach.Generators.data import *
from Peach.mutator import *


class NumericalVarianceMutator(Mutator):
    """
    Produce numbers that are defaultValue - N to defaultValue + N.
    """

    def __init__(self, peach, node):
        Mutator.__init__(self)
        NumericalVarianceMutator.weight = 2
        self.name = "NumericalVarianceMutator"
        self.isFinite = True
        self._count = None
        self._dataElementName = node.getFullname()
        self._n = self._getN(node, 50)
        self._values = range(0 - self._n, self._n)
        self._currentCount = 0
        if isinstance(node, String):
            self._minValue = -2147483647
            self._maxValue = 4294967295
        else:
            self._minValue = node.getMinValue()
            self._maxValue = node.getMaxValue()

    def _getN(self, node, n):
        for c in node.hints:
            if c.name == 'NumericalVarianceMutator-N':
                try:
                    n = int(c.value)
                except:
                    raise PeachException("Expected numerical value for Hint "
                                         "named [{}]".format(c.name))
        return n

    def next(self):
        self._currentCount += 1
        if self._currentCount >= len(self._values):
            raise MutatorCompleted()

    def getCount(self):
        return len(self._values)

    @staticmethod
    def supportedDataElement(node):
        if isinstance(node, String) and node.isMutable:
            for hint in node.hints:
                if hint.name == "NumericalString":
                    return True
        # Disable for 8 bit ints, we try all values already
        if (isinstance(node, Number) or isinstance(node, Flag)) \
                and node.isMutable and node.size > 8:
            return True
        return False

    def sequentialMutation(self, node):
        self.changedName = node.getFullnameInDataModel()
        # If a negative value is passed into struct.pack we end up generating
        # 0 for that value. Instead lets verify the generated value against
        # min/max and skip bad values.
        while True:
            # Sometimes self._n == 0, catch that here
            if self._currentCount >= len(self._values):
                return
            print("===> %s %s" % (repr(node.getInternalValue()), self.changedName))
            node.currentValue = int(node.getInternalValue()) - \
                                self._values[self._currentCount]
            # Is number okay?
            if self._minValue <= node.currentValue <= self._maxValue:
                break
            # If not lets skip to next iteration
            try:
                self.next()
            except:
                break
        if isinstance(node, String):
            node.currentValue = unicode(node.currentValue)

    def randomMutation(self, node, rand):
        self.changedName = node.getFullnameInDataModel()
        try:
            count = rand.choice(self._values)
            node.currentValue = str(int(node.getInternalValue()) + count)
            if isinstance(node, String):
                node.currentValue = unicode(node.currentValue)
        except ValueError:
            # Okay to skip, another mutator probably changes this value
            # already (like a datatree one).
            pass


class NumericalEdgeCaseMutator(Mutator):
    """
    This is a straight up generation class. Produces values that have nothing
    todo with defaultValue.
    """

    _values = None
    _allowedSizes = [8, 16, 24, 32, 64]

    def __init__(self, peach, node):
        Mutator.__init__(self)
        NumericalEdgeCaseMutator.weight = 3
        self.isFinite = True
        self.name = "NumericalEdgeCaseMutator"
        self._peach = peach
        self._count = None
        self._n = self._getN(node, 50)
        if self._values is None:
            self._populateValues()
        if isinstance(node, String):
            self._size = 32
        else:
            self._size = node.size
        # For flags, pick the next proper size up
        if self._size not in self._allowedSizes:
            for s in self._allowedSizes:
                if self._size <= s:
                    self._size = s
                    break
        self._dataElementName = node.getFullname()
        self._currentCount = 0
        if isinstance(node, String):
            self._minValue = -2147483647
            self._maxValue = 4294967295
        else:
            self._minValue = node.getMinValue()
            self._maxValue = node.getMaxValue()

    def _populateValues(self):
        NumericalEdgeCaseMutator._values = {}
        nums = []
        try:
            gen = BadNumbers8()
            while True:
                nums.append(int(gen.getValue()))
                gen.next()
        except:
            pass
        self._values[8] = nums
        nums = []
        try:
            gen = BadNumbers16(None, self._n)
            while True:
                nums.append(int(gen.getValue()))
                gen.next()
        except:
            pass
        self._values[16] = nums
        nums = []
        try:
            gen = BadNumbers24(None, self._n)
            while True:
                nums.append(int(gen.getValue()))
                gen.next()
        except:
            pass
        self._values[24] = nums
        nums = []
        try:
            gen = BadNumbers32(None, self._n)
            while True:
                nums.append(int(gen.getValue()))
                gen.next()
        except:
            pass
        self._values[32] = nums
        nums = []
        try:
            gen = BadNumbers(None, self._n)
            while True:
                nums.append(int(gen.getValue()))
                gen.next()
        except:
            pass
        self._values[64] = nums

    def next(self):
        self._currentCount += 1
        if self._currentCount >= len(self._values[self._size]):
            raise MutatorCompleted()

    def getCount(self):
        if self._count is None:
            cnt = 0
            for i in self._values[self._size]:
                if i < self._minValue or i > self._maxValue:
                    continue
                cnt += 1
            self._count = cnt
        return self._count

    @staticmethod
    def supportedDataElement(node):
        if isinstance(node, String) and node.isMutable:
            for hint in node.hints:
                if hint.name == "NumericalString":
                    return True
        if (isinstance(node, Number) or isinstance(node, Flag)) \
                and node.isMutable:
            return True
        return False

    def _getN(self, node, n):
        for c in node.hints:
            if c.name == 'NumericalEdgeCaseMutator-N':
                try:
                    n = int(c.value)
                except:
                    raise PeachException("Expected numerical value for Hint "
                                         "named [{}]".format(c.name))
        return n

    def sequentialMutation(self, node):
        self.changedName = node.getFullnameInDataModel()
        # If a negative value is passed into struct.pack we end up generating
        # 0 for that value. Instead lets verify the generated value against
        # min/max and skip bad values.
        while True:
            if isinstance(node, String):
                node.currentValue = \
                    unicode(self._values[self._size][self._currentCount])
            else:
                node.currentValue = \
                    self._values[self._size][self._currentCount]
            # Is number okay?
            if self._minValue <= int(node.currentValue) <= self._maxValue:
                break
            # If not lets skip to next iteration
            try:
                self.next()
            except:
                break

    def randomMutation(self, node, rand):
        self.changedName = node.getFullnameInDataModel()
        if isinstance(node, String):
            node.currentValue = unicode(rand.choice(self._values[self._size]))
        else:
            node.currentValue = rand.choice(self._values[self._size])


class FiniteRandomNumbersMutator(Mutator):
    """
    Produce a finite number of random numbers for each <Number> element.
    """

    def __init__(self, peach, node):
        Mutator.__init__(self)
        #: Weight to be chosen randomly
        FiniteRandomNumbersMutator.weight = 2
        self.name = "FiniteRandomNumbersMutator"
        self._peach = peach
        self._countThread = None
        self._n = self._getN(node, 5000)
        self._currentCount = 0
        if isinstance(node, String):
            self._minValue = 0
            self._maxValue = 4294967295
        else:
            self._minValue = node.getMinValue()
            self._maxValue = node.getMaxValue()

    def next(self):
        self._currentCount += 1
        if self._currentCount > self._n:
            raise MutatorCompleted()

    def getCount(self):
        return self._n

    @staticmethod
    def supportedDataElement(node):
        if (isinstance(node, Number) or isinstance(node, Flag)) and \
                node.isMutable and node.size > 8:
            return True
        if isinstance(node, String) and node.isMutable:
            for hint in node.hints:
                if hint.name == "NumericalString":
                    return True
        return False

    def _getN(self, node, n):
        for c in node.hints:
            if c.name == 'FiniteRandomNumbersMutator-N':
                try:
                    n = int(c.value)
                except:
                    raise PeachException("Expected numerical value for Hint "
                                         "named [{}]".format(c.name))
        return n

    def sequentialMutation(self, node):
        # Allow us to skip ahead and always get same number
        rand = random.Random()
        rand.seed(hashlib.sha512(str(self._currentCount)).digest())
        self.changedName = node.getFullnameInDataModel()
        if isinstance(node, String):
            node.currentValue = \
                unicode(rand.randint(self._minValue, self._maxValue))
        else:
            node.currentValue = rand.randint(self._minValue, self._maxValue)

    def randomMutation(self, node, rand):
        self.changedName = node.getFullnameInDataModel()
        if isinstance(node, String):
            node.currentValue = \
                unicode(rand.randint(self._minValue, self._maxValue))
        else:
            node.currentValue = rand.randint(self._minValue, self._maxValue)


class NumericalEvenDistributionMutator(Mutator):
    """
    This mutator will generate numbers evenly distributed through the total
    numerical space of the number range.
    """

    _values = None

    def __init__(self, peach, node):
        Mutator.__init__(self)
        self.weight = 3
        self.isFinite = True
        self.name = "NumericalEdgeCaseMutator"
        self._peach = peach
        self._n = self._getN(node, 50)
        if self._values is None:
            self._populateValues()
        if isinstance(node, String):
            self._size = 32
        else:
            self._size = node.size
        self._dataElementName = node.getFullname()
        self._random = random.Random()
        self._currentCount = 0
        if isinstance(node, String):
            self._minValue = 0
            self._maxValue = 4294967295
        else:
            self._minValue = node.getMinValue()
            self._maxValue = node.getMaxValue()

    def _populateValues(self):
        NumericalEdgeCaseMutator._values = {}
        nums = []
        try:
            gen = BadNumbers8()
            while True:
                nums.append(int(gen.getValue()))
                gen.next()
        except:
            pass
        self._values[8] = nums
        nums = []
        try:
            gen = BadNumbers16(None, self._n)
            while True:
                nums.append(int(gen.getValue()))
                gen.next()
        except:
            pass
        self._values[16] = nums
        nums = []
        try:
            gen = BadNumbers24(None, self._n)
            while True:
                nums.append(int(gen.getValue()))
                gen.next()
        except:
            pass
        self._values[24] = nums
        nums = []
        try:
            gen = BadNumbers32(None, self._n)
            while True:
                nums.append(int(gen.getValue()))
                gen.next()
        except:
            pass
        self._values[32] = nums
        nums = []
        try:
            gen = BadNumbers(None, self._n)
            while True:
                nums.append(int(gen.getValue()))
                gen.next()
        except:
            pass
        self._values[64] = nums

    def next(self):
        self._currentCount += 1
        if self._currentCount >= len(self._values[self._size]):
            raise MutatorCompleted()

    def getCount(self):
        return len(self._values[self._size])

    @staticmethod
    def supportedDataElement(node):
        if isinstance(node, String):
            for hint in node.hints:
                if hint.name == "NumericalString":
                    return True
        if isinstance(node, Number) and node.isMutable:
            return True
        return False

    def _getN(self, node, n):
        for c in node.hints:
            if c.name == 'NumericalEdgeCaseMutator-N':
                try:
                    n = int(c.value)
                except:
                    raise PeachException("Expected numerical value for Hint "
                                         "named [{}]".format(c.name))
        return n

    def sequentialMutation(self, node):
        if isinstance(node, String):
            node.currentValue = \
                unicode(self._values[self._size][self._currentCount])
        else:
            node.currentValue = self._values[self._size][self._currentCount]

    def randomMutation(self, node):
        if isinstance(node, String):
            node.currentValue = \
                unicode(self._random.choice(self._values[self._size]))
        else:
            node.currentValue = self._random.choice(self._values[self._size])
