# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
import random

from Peach.fixup import Fixup


class EvenNumber(Fixup):

    def __init__(self, ref):
        Fixup.__init__(self)
        self.ref = ref

    def fixup(self):
        ref = self.context.findDataElementByName(self.ref)
        stuff = ref.getValue()
        if stuff is None:
            raise Exception("Error: EvenNumberFixup was unable to locate "
                            "[{}]".format(self.ref))
        return stuff if stuff % 2 == 0 else stuff + 1


class SequenceIncrementFixup(Fixup):
    """
    Allows a field to emit a sequential value without adding additional test
    cases. This is useful for sequence numbers common in network protocols.
    """

    num = 1

    def __init__(self):
        Fixup.__init__(self)

    def fixup(self):
        SequenceIncrementFixup.num += 1
        return SequenceIncrementFixup.num


class SequenceRandomFixup(Fixup):
    """
    Allows a field to emit a random value without adding additional test cases.
    This is useful for sequence numbers common in network protocols.
    """

    def __init__(self):
        random.seed()
        Fixup.__init__(self)

    def fixup(self):
        return random.randint(0, (1 << self.context.size) - 1)
