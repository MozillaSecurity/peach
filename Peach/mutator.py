# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from Peach.Engine.dom import *


class MutatorCompleted(Exception):
    """
    At end of available mutations.
    """
    pass


class MutatorError(Exception):
    pass


class Mutator(object):
    """
    A Mutator implements a method of mutating data/state for a Peach fuzzer.
    For example a mutator might change the state flow defined by a Peach
    fuzzer. Another mutator might mutate data based on known relationships.
    Another mutator might perform numerical type tests against fields.
    """
    elementType = "mutator"
    dataTypes = [
        'template',
        'string',
        'number',
        'flags',
        'choice',
        'sequence',
        'blob',
        'block'
    ]
    _random = random.Random()
    weight = 1

    def __init__(self):
        self.name = "Mutator"
        self._count = None
        self.changedName = "N/A"
        self.isFinite = False

    @staticmethod
    def supportedDataElement(node):
        """
        Returns true if element is supported by this mutator.
        """
        return isinstance(node, DataElement) and node.isMutable

    def next(self):
        """
        Go to next mutation. When this is called the state machine is updated
        as needed.
        """
        pass

    def getCount(self):
        """
        If mutator is finite than the total test count can be calculated.
        This calculation cannot occur until after the state machine has been
        run the first time. Once the state machine has been run the count can
        be calculated. This typically occurs in a separate thread as it can
        take some time to calculate. This method will return None until a the
        correct value has been calculated.
        """
        return self._count

    def sequentialMutation(self, node):
        """
        Perform a sequential mutation.
        """
        pass

    def randomMutation(self, node):
        """
        Perform a random mutation.
        """
        pass
