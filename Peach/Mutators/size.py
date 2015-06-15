# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from Peach.Generators.data import *
from Peach.mutator import *


class SizedVarianceMutator(Mutator):
    """
    Change the length of sizes to count - N to count + N.
    """

    def __init__(self, peach, node):
        Mutator.__init__(self)
        SizedVarianceMutator.weight = 2
        self.isFinite = True
        self.name = "SizedVarianceMutator"
        self._peach = peach
        self._dataElementName = node.getFullname()
        self._n = self._getN(node, 50)
        self._range = range(0 - self._n, self._n)
        self._currentCount = 0

    def _getN(self, node, n):
        for c in node.hints:
            if c.name == ('{}-N'.format(self.name)):
                try:
                    n = int(c.value)
                except:
                    raise PeachException("Expected numerical value for Hint "
                                         "named [{}]".format(c.name))
        return n

    def next(self):
        self._currentCount += 1
        if self._currentCount >= len(self._range):
            raise MutatorCompleted()

    def getCount(self):
        return len(self._range)

    @staticmethod
    def supportedDataElement(node):
        if isinstance(node, DataElement) and node._HasSizeofRelation(node) \
                and node.isMutable:
            return True
        return False

    def sequentialMutation(self, node):
        self.changedName = node.getFullnameInDataModel()
        self._performMutation(node, self._range[self._currentCount])

    def randomMutation(self, node, rand):
        self.changedName = node.getFullnameInDataModel()
        count = rand.choice(self._range)
        self._performMutation(node, count)

    def _performMutation(self, node, count):
        """
        Perform array mutation using count
        """
        relation = node._GetSizeofRelation()
        nodeOf = relation.getOfElement()
        size = int(node.getInternalValue())
        realSize = len(nodeOf.getValue())
        n = size + count
        # In cases were expressionSet/Get changes the size value +/- some
        # amount, we need to take that into account if possible.
        diff = size - realSize
        ## Can we make the value?
        if n - diff < 0:
            # We can't make N the # we want, so do our best and get our of
            # here w/o an assert check.
            nodeOf.currentValue = ""
            return
        ## Otherwise Make the value
        if n <= 0:
            nodeOf.currentValue = ""
        elif n < size:
            nodeOf.currentValue = str(nodeOf.getInternalValue())[:n - diff]
        elif size == 0:
            nodeOf.currentValue = "A" * (n - diff)
        else:
            try:
                nodeOf.currentValue = \
                    (str(nodeOf.getInternalValue()) *
                     (((n - diff) / realSize) + 2))[:n - diff]
            except ZeroDivisionError:
                nodeOf.currentValue = ""

            # Verify things worked out okay
            #try:
            #	assert((n == long(node.getInternalValue()) and (n-diff) == len(nodeOf.getValue())) or n < 0)
            #except:
            #	print "realSize:", realSize
            #	print "diff:", diff
            #	print "node.name:", node.name
            #	print "nodeOf.name:", nodeOf.name
            #	print "nodeOf:", nodeOf
            #	print "n:", n
            #	print "long(node.getInternalValue()):",long(node.getInternalValue())
            #	print "len(nodeOf.getValue()):", len(nodeOf.getValue())
            #	print "repr(nodeOf.getValue()):", repr(nodeOf.getValue())
            #	raise


class SizedNumericalEdgeCasesMutator(Mutator):
    """
    Change the length of sizes to numerical edge cases
    """

    def __init__(self, peach, node):
        Mutator.__init__(self)
        SizedNumericalEdgeCasesMutator.weight = 2
        self.isFinite = True
        self.name = "SizedNumericalEdgeCasesMutator"
        self._peach = peach
        self._dataElementName = node.getFullname()
        self._n = self._getN(node, 50)
        self._range = self._populateValues(node)
        self._currentCount = 0

    def _populateValues(self, node):
        if isinstance(node, Number):
            size = node.size
        elif isinstance(node, Flag):
            size = node.length
            if size < 16:
                size = 8
            elif size < 32:
                size = 16
            elif size < 64:
                size = 32
            else:
                size = 64
        else:
            size = 64  # In the case of strings or blobs
        nums = []
        try:
            if size < 16:
                gen = BadNumbers8()
            else:
                gen = BadNumbers16(None, self._n)
            # Only if we are testing large memory
            #gen = BadNumbers24(None, self._n)
            #gen = BadNumbers32(None, self._n)
            #gen = BadNumbers(None, self._n)
            while True:
                nums.append(int(gen.getValue()))
                gen.next()
        except:
            pass
        return nums

    def _getN(self, node, n):
        for c in node.hints:
            if c.name == ('{}-N'.format(self.name)):
                try:
                    n = int(c.value)
                except:
                    raise PeachException("Expected numerical value for Hint "
                                         "named [{}]".format(c.name))
        return n

    def next(self):
        self._currentCount += 1
        if self._currentCount >= len(self._range):
            raise MutatorCompleted()

    def getCount(self):
        return len(self._range)

    @staticmethod
    def supportedDataElement(node):
        # This will pick up both numbers or strings, etc that have a size-of
        # relation.
        if isinstance(node, DataElement) and node._HasSizeofRelation(node) \
                and node.isMutable:
            return True
        return False

    def sequentialMutation(self, node):
        self.changedName = node.getFullnameInDataModel()
        self._performMutation(node, self._range[self._currentCount])

    def randomMutation(self, node, rand):
        self.changedName = node.getFullnameInDataModel()
        count = rand.choice(self._range)
        self._performMutation(node, count)

    def _performMutation(self, node, count):
        """
        Perform array mutation using count
        """
        relation = node._GetSizeofRelation()
        nodeOf = relation.getOfElement()
        size = int(node.getInternalValue())
        realSize = len(nodeOf.getValue())
        n = size + count
        # In cases were expressionSet/Get changes the size value +/- some
        # amount, we need to take that into account if possible.
        diff = size - realSize
        ## Can we make the value?
        if n - diff < 0:
            # We can't make N the # we want, so do our best and get our of
            # here w/o an assert check.
            nodeOf.currentValue = ""
            return
        ## Otherwise make the value
        if n <= 0:
            nodeOf.currentValue = ""
        elif n < size:
            nodeOf.currentValue = nodeOf.getInternalValue()[:n - diff]
        elif size == 0:
            nodeOf.currentValue = "A" * (n - diff)
        else:
            try:
                nodeOf.currentValue = \
                    (str(nodeOf.getInternalValue()) *
                     (((n - diff) / realSize) + 2))[:n - diff]
            except ZeroDivisionError:
                nodeOf.currentValue = ""

            # Verify things worked out okay
            ##try:
            ##	assert((n == long(node.getInternalValue()) and (n-diff) == len(nodeOf.getValue())) or n < 0)
            ##except:
            ##	print "realSize:", realSize
            ##	print "diff:", diff
            ##	print "node.name:", node.name
            ##	print "nodeOf.name:", nodeOf.name
            ##	print "nodeOf:", nodeOf
            ##	print "n:", n
            ##	print "long(node.getInternalValue()):",long(node.getInternalValue())
            ##	print "len(nodeOf.getValue()):", len(nodeOf.getValue())
            ##	print "repr(nodeOf.getValue()):", repr(nodeOf.getValue())[:100]
            ##	raise


class SizedDataVarianceMutator(Mutator):
    """
    Change the length of sized data to count - N to count + N.
    Size indicator will stay the same
    """

    def __init__(self, peach, node):
        Mutator.__init__(self)
        SizedDataVarianceMutator.weight = 2
        self.isFinite = True
        self.name = "SizedDataVarianceMutator"
        self._peach = peach
        self._dataElementName = node.getFullname()
        self._n = self._getN(node, 50)
        self._range = range(0 - self._n, self._n)
        self._currentCount = 0

    def _getN(self, node, n):
        for c in node.hints:
            if c.name == ('{}-N'.format(self.name)):
                try:
                    n = int(c.value)
                except:
                    raise PeachException("Expected numerical value for Hint "
                                         "named [{}]".format(c.name))
        return n

    def next(self):
        self._currentCount += 1
        if self._currentCount >= len(self._range):
            raise MutatorCompleted()

    def getCount(self):
        return len(self._range)

    @staticmethod
    def supportedDataElement(node):
        if isinstance(node, DataElement) and node._HasSizeofRelation(node) \
                and node.isMutable:
            return True
        return False

    def sequentialMutation(self, node):
        self.changedName = node.getFullnameInDataModel()
        self._performMutation(node, self._range[self._currentCount])

    def randomMutation(self, node, rand):
        self.changedName = node.getFullnameInDataModel()
        count = rand.choice(self._range)
        self._performMutation(node, count)

    def _performMutation(self, node, count):
        """
        Perform array mutation using count
        """
        relation = node._GetSizeofRelation()
        nodeOf = relation.getOfElement()
        size = int(node.getInternalValue())
        realSize = len(nodeOf.getValue())
        # Keep size indicator the same
        node.value = node.getValue()
        node.currentValue = node.getInternalValue()
        # Modify data
        n = size + count
        if n == 0:
            nodeOf.value = ""
        elif n < size:
            nodeOf.value = nodeOf.getValue()[:n]
        elif size == 0:
            nodeOf.value = "A" * n
        else:
            nodeOf.value = (nodeOf.getValue() * ((n / realSize) + 1))[:n]

        # Verify things worked out okay
        #assert(size == long(node.getInternalValue()) and n == len(nodeOf.getValue()))


class SizedDataNumericalEdgeCasesMutator(Mutator):
    """
    Change the length of sizes to numerical edge cases
    """

    def __init__(self, peach, node):
        Mutator.__init__(self)
        SizedDataNumericalEdgeCasesMutator.weight = 2
        self.isFinite = True
        self.name = "SizedDataNumericalEdgeCasesMutator"
        self._peach = peach
        self._dataElementName = node.getFullname()
        self._n = self._getN(node, 50)
        self._range = self._populateValues(node)
        self._currentCount = 0

    def _populateValues(self, node):
        if isinstance(node, Number):
            size = node.size
        elif isinstance(node, Flag):
            size = node.length
            if size < 16:
                size = 8
            elif size < 32:
                size = 16
            elif size < 64:
                size = 32
            else:
                size = 64
        else:
            size = 64  # In the case of strings or blobs
        nums = []
        try:
            if size < 16:
                gen = BadNumbers8()
            else:
                gen = BadNumbers16(None, self._n)
            # Only if we are testing large memory
            #gen = BadNumbers24(None, self._n)
            #gen = BadNumbers32(None, self._n)
            #gen = BadNumbers(None, self._n)
            while True:
                nums.append(int(gen.getValue()))
                gen.next()
        except:
            pass
        return nums

    def _getN(self, node, n):
        for c in node.hints:
            if c.name == ('{}-N'.format(self.name)):
                try:
                    n = int(c.value)
                except:
                    raise PeachException("Expected numerical value for Hint "
                                         "named [{}]".format(c.name))
        return n

    def next(self):
        self._currentCount += 1
        if self._currentCount >= len(self._range):
            raise MutatorCompleted()

    def getCount(self):
        return len(self._range)

    @staticmethod
    def supportedDataElement(node):
        # This will pick up both numbers or strings, etc that have a size-of
        # relation.
        if isinstance(node, DataElement) and node._HasSizeofRelation(node) \
                and node.isMutable:
            return True
        return False

    def sequentialMutation(self, node):
        self.changedName = node.getFullnameInDataModel()
        self._performMutation(node, self._range[self._currentCount])

    def randomMutation(self, node, rand):
        self.changedName = node.getFullnameInDataModel()
        count = rand.choice(self._range)
        self._performMutation(node, count)

    def _performMutation(self, node, count):
        """
        Perform array mutation using count
        """
        relation = node._GetSizeofRelation()
        nodeOf = relation.getOfElement()
        size = int(node.getInternalValue())
        # Keep size indicator the same
        node.value = node.getValue()
        node.currentValue = node.getInternalValue()
        n = count
        if n == 0:
            nodeOf.value = ""
        elif n < size:
            nodeOf.value = nodeOf.getValue()[:n]
        elif size == 0:
            nodeOf.value = "A" * n
        else:
            nodeOf.value = (nodeOf.getValue() * ((n / size) + 1))[:n]

        # Verify things worked out okay
        #assert(size == long(node.getInternalValue()) and n == len(nodeOf.getValue()))
