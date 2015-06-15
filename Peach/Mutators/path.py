# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from Peach.mutator import *
from Peach.mutatestrategies import *


class NullMutator(Mutator):
    """
    Does not make any changes to data tree. This is usually the first mutator
    applied to a fuzzing run so the generated data can be verified.
    """

    def __init__(self, peach):
        Mutator.__init__(self)
        self.name = "NullMutator"

    def isFinite(self):
        """
        Some mutators could continue forever, this should indicate.
        """
        return True

    def next(self):
        """
        Go to next mutation. When this is called the state machine is updated
        as needed.
        """
        raise MutatorCompleted()

    def getState(self):
        """
        Return a binary string that contains any information about current
        state of Mutator. This state information should be enough to let the
        same mutator "restart" and continue when setState() is called.
        """
        return ""

    def setState(self, state):
        """
        Set the state of this object. Should put us back in the same place as
        when we said "getState()".
        """
        pass

    def getCount(self):
        return 1

    def getActionValue(self, action):
        if action.template.modelHasOffsetRelation:
            stringBuffer = StreamBuffer()
            action.template.getValue(stringBuffer)
            stringBuffer.setValue("")
            stringBuffer.seekFromStart(0)
            action.template.getValue(stringBuffer)
            return stringBuffer.getValue()
        return action.template.getValue()

    def getActionParamValue(self, action):
        if action.template.modelHasOffsetRelation:
            stringBuffer = StreamBuffer()
            action.template.getValue(stringBuffer)
            stringBuffer.setValue("")
            stringBuffer.seekFromStart(0)
            action.template.getValue(stringBuffer)
            return stringBuffer.getValue()
        return action.template.getValue()

    def getActionChangeStateValue(self, action, value):
        return value


class PathValidationMutator(NullMutator, MutationStrategy):
    """
    This mutator is just used to trace path of each test for path validation
    purposes so this is not an actual Mutator that is used on fuzzing.
    """

    def __init__(self):
        Mutator.__init__(self)
        self.states = []
        self.name = "PathValidationMutator"

    def onStateStarting(self, stateMachine, state):
        self.states.append(state.name)

    def onStateMachineStarting(self, engine):
        pass

    def onStateMachineComplete(self, engine):
        engine.pathFinder.reset()
