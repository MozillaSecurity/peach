# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from Peach.mutator import *
from Peach.Engine.common import *


class DataTreeRemoveMutator(Mutator):
    """
    Remove nodes from data tree.
    """

    def __init__(self, peach, node):
        Mutator.__init__(self)
        self.isFinite = True
        self.name = "DataTreeRemoveMutator"
        self._peach = peach

    def next(self):
        raise MutatorCompleted()

    def getCount(self):
        return 1

    @staticmethod
    def supportedDataElement(e):
        if isinstance(e, DataElement) and e.isMutable:
            return True
        return False

    def sequentialMutation(self, node):
        self.changedName = node.getFullnameInDataModel()
        node.setValue("")

    def randomMutation(self, node, rand):
        self.changedName = node.getFullnameInDataModel()
        node.setValue("")


class DataTreeDuplicateMutator(Mutator):
    """
    Duplicate a node's value starting at 2x through 50x.
    """

    def __init__(self, peach, node):
        Mutator.__init__(self)
        self.isFinite = True
        self.name = "DataTreeDuplicateMutator"
        self._peach = peach
        self._cnt = 2
        self._maxCount = 50

    def next(self):
        self._cnt += 1
        if self._cnt > self._maxCount:
            raise MutatorCompleted()

    def getCount(self):
        return self._maxCount

    @staticmethod
    def supportedDataElement(e):
        if isinstance(e, DataElement) and e.isMutable:
            return True
        return False

    def sequentialMutation(self, node):
        self.changedName = node.getFullnameInDataModel()
        node.setValue(node.getValue() * self._cnt)

    def randomMutation(self, node, rand):
        self.changedName = node.getFullnameInDataModel()
        count = rand.randint(0, self._cnt)
        node.setValue(node.getValue() * count)


class DataTreeSwapNearNodesMutator(Mutator):
    """
    Swap two nodes in the data model that are near each other.
    TODO: Actually move the nodes instead of just the data.
    """

    def __init__(self, peach, node):
        Mutator.__init__(self)
        self.isFinite = True
        self.name = "DataTreeSwapNearNodesMutator"
        self._peach = peach

    def next(self):
        raise MutatorCompleted()

    def getCount(self):
        return 1

    def _moveNext(self, currentNode):
        # Check if we are top dogM
        if currentNode.parent is None or \
                not isinstance(currentNode.parent, DataElement):
            return None
        # Get sibling
        foundCurrent = False
        for node in currentNode.parent:
            if node == currentNode:
                foundCurrent = True
                continue
            if foundCurrent and isinstance(node, DataElement):
                return node
        # Get sibling of parentM
        return self._moveNext(currentNode.parent)

    def _nextNode(self, node):
        nextNode = None
        # Walk down node tree
        for child in node._children:
            if isinstance(child, DataElement):
                nextNode = child
                break
        # Walk over or up if we can
        if nextNode is None:
            nextNode = self._moveNext(node)
        return nextNode

    @staticmethod
    def supportedDataElement(e):
        if isinstance(e, DataElement) and e.isMutable:
            return True
        return False

    def sequentialMutation(self, node):
        self.changedName = node.getFullnameInDataModel()
        nextNode = self._nextNode(node)
        if nextNode is not None:
            v1 = node.getValue()
            v2 = nextNode.getValue()
            node.setValue(v2)
            nextNode.setValue(v1)

    def randomMutation(self, node, rand):
        self.changedName = node.getFullnameInDataModel()
        self.sequentialMutation(node)
