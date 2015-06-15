# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
import sys
import random
import hashlib

from Peach.Generators.data import BadPositiveNumbersSmaller
from Peach.mutator import *


class ArrayVarianceMutator(Mutator):
    """
    Change the length of arrays to count - N to count + N.
    """

    def __init__(self, peach, node, name="ArrayVarianceMutator"):
        Mutator.__init__(self)
        #: Weight to be chosen randomly
        ArrayVarianceMutator.weight = 2
        if not ArrayVarianceMutator.supportedDataElement(node):
            raise Exception("ArrayVarianceMutator created with bad node.")
        self.isFinite = True
        self.name = name
        self._peach = peach
        self._n = self._getN(node, 50)
        self._arrayCount = node.getArrayCount()
        self._minCount = self._arrayCount - self._n
        self._maxCount = self._arrayCount + self._n
        self.changedName = ""
        self._minCount = 0 if self._minCount < 0 else self._minCount
        self._currentCount = self._minCount

    def _getN(self, node, n):
        """
        Gets N by checking node for hint or returning default.
        """
        for c in node.hints:
            if c.name == ('{}-N'.format(self.name)):
                try:
                    n = int(c.value)
                except:
                    raise PeachException("Expected numerical value for Hint "
                                         "named [{}]".format(c.name))
        return n

    def next(self):
        """
        Go to next mutation. When this is called the state machine is updated
        as needed.
        """
        self._currentCount += 1
        if self._currentCount > self._maxCount:
            raise MutatorCompleted()

    def getCount(self):
        return self._maxCount - self._minCount

    @staticmethod
    def supportedDataElement(e):
        """
        Returns true if element is supported by this mutator.
        """
        if isinstance(e, DataElement) and \
                e.isArray() and \
                e.arrayPosition == 0 and \
                e.isMutable:
            return True
        return False

    def sequentialMutation(self, node):
        """
        Perform a sequential mutation.
        """
        self.changedName = node.getFullnameInDataModel()
        self._performMutation(node, self._currentCount)

    def randomMutation(self, node, rand):
        """
        Perform a random mutation.
        """
        self.changedName = node.getFullnameInDataModel()
        count = rand.randint(self._minCount, self._maxCount)
        self._performMutation(node, count)

    def _performMutation(self, node, count):
        """
        Perform array mutation using count.
        """
        n = count
        arrayHead = node
        # TODO: Support zero array elements!
        if n == 0:
            ## Remove all
            #for i in xrange(self._arrayCount - 1, -1, -1):
            #	obj = arrayHead.getArrayElementAt(i)
            #	if obj == None:
            #		raise Exception("Couldn't locate item at pos %d (max "
            #                       "of %d)" % (i, self._arrayCount))
            #
            #	obj.parent.__delitem__(obj.name)
            pass
        elif n < self._arrayCount:
            # Remove some items
            for i in range(self._arrayCount - 1, n - 1, -1):
                obj = arrayHead.getArrayElementAt(i)
                if obj is None:
                    raise Exception("Could not locate item at pos {} (max "
                                    "of {})".format((i, self._arrayCount)))
                obj.parent.__delitem__(obj.name)
            #assert(arrayHead.getArrayCount() == n)
        elif n > self._arrayCount:
            # Add some items
            headIndex = arrayHead.parent.index(arrayHead)
            # Faster, but getValue() might not be correct.
            obj = arrayHead.getArrayElementAt(arrayHead.getArrayCount() - 1)
            try:
                obj.value = obj.getValue() * (n - self._arrayCount)
                obj.arrayPosition = n - 1
            except MemoryError:
                # Catch out of memory errors
                pass
            ### Slower but reliable (we hope)
            #for i in xrange(self._arrayCount, n):
            #	obj = arrayHead.copy(arrayHead)
            #	obj.arrayPosition = i
            #	arrayHead.parent.insert(headIndex+i, obj)

            #print arrayHead.getArrayCount(), n
            #assert(arrayHead.getArrayCount() == n)


class ArrayNumericalEdgeCasesMutator(ArrayVarianceMutator):

    _counts = None

    def __init__(self, peach, node):
        ArrayVarianceMutator.__init__(self, peach, node,
                                      "ArrayNumericalEdgeCasesMutator")
        #: Weight to be chosen randomly
        ArrayNumericalEdgeCasesMutator.weight = 2
        if self._counts is None:
            ArrayNumericalEdgeCasesMutator._counts = []
            gen = BadPositiveNumbersSmaller()
            try:
                while True:
                    self._counts.append(int(gen.getValue()))
                    gen.next()
            except:
                pass
        self._minCount = None
        self._maxCount = None
        self._countsIndex = 0
        self._currentCount = self._counts[self._countsIndex]

    def next(self):
        """
        Go to next mutation. When this is called the state machine is updated
        as needed.
        """
        self._countsIndex += 1
        if self._countsIndex >= len(self._counts):
            raise MutatorCompleted()
        self._currentCount = self._counts[self._countsIndex]

    def getCount(self):
        return len(self._counts)

    def randomMutation(self, node, rand):
        """
        Perform a random mutation.
        """
        count = rand.choice(self._counts)
        self._performMutation(node, count)


class ArrayReverseOrderMutator(ArrayVarianceMutator):
    def __init__(self, peach, node):
        ArrayVarianceMutator.__init__(self, peach, node,
                                      "ArrayReverseOrderMutator")

    def next(self):
        raise MutatorCompleted()

    def getCount(self):
        return 1

    def sequentialMutation(self, node):
        self.changedName = node.getFullnameInDataModel()
        self._performMutation(node)

    def randomMutation(self, node):
        self.changedName = node.getFullnameInDataModel()
        self._performMutation(node)

    def _performMutation(self, node):
        arrayHead = node
        headIndex = arrayHead.parent.index(arrayHead)
        items = []
        parent = arrayHead.parent
        try:
            for i in range(self._arrayCount):
                obj = arrayHead.getArrayElementAt(i)
                if obj is not None:
                    items.append(obj)
            for obj in items:
                del parent[obj.name]
            x = 0
            for i in range(len(items) - 1, -1, -1):
                obj = items[i]
                parent.insert(headIndex + x, obj)
                obj.arrayPosition = x
                x += 1
        except:
            print("Exception in ArrayReverseOrderMutator._performMutation")
            print(sys.exc_info())
        assert (self._arrayCount == arrayHead.getArrayCount())


class ArrayRandomizeOrderMutator(ArrayVarianceMutator):
    def __init__(self, peach, node):
        ArrayVarianceMutator.__init__(self, peach, node,
                                      "ArrayRandomizeOrderMutator")
        self._count = 0

    def next(self):
        self._count += 1
        if self._count > self._n:
            raise MutatorCompleted()

    def getCount(self):
        return self._n

    def sequentialMutation(self, node):
        rand = random.Random()
        rand.seed(hashlib.sha512(str(self._count)).digest())
        self.changedName = node.getFullnameInDataModel()
        self._performMutation(node, rand)

    def randomMutation(self, node, rand):
        self.changedName = node.getFullnameInDataModel()
        self._performMutation(node, rand)

    def _performMutation(self, node, rand):
        arrayHead = node
        headIndex = arrayHead.parent.index(arrayHead)
        items = []
        parent = arrayHead.parent
        try:
            for i in range(self._arrayCount):
                obj = arrayHead.getArrayElementAt(i)
                if obj is not None:
                    items.append(obj)
            for obj in items:
                del parent[obj.name]
            rand.shuffle(items)
            for i in range(len(items)):
                obj = items[i]
                parent.insert(headIndex + i, obj)
                obj.arrayPosition = i
        except:
            print("Exception in ArrayRandomizeOrderMutator._performMutation")
            print(sys.exc_info())
        assert (self._arrayCount == arrayHead.getArrayCount())
