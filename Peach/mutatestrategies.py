# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from Peach.mutator import MutatorCompleted
from Peach.Utilities.common import setAttributesFromParams


class MutationStrategy(object):
    """
    Mutation strategies control how fuzzing occurs, weather that be changing
    each field sequentially or randomly selecting 5 fields to change each test
    case.
    Mutation strategies are implemented by overriding event handlers and using
    them to affect the state machine, data models, etc.
    """

    DefaultStrategy = None

    def __init__(self, node, parent):
        self.parent = parent  # This will be a <Test> object
        setAttributesFromParams(node)

    def isFinite(self):
        """
        Will this mutation strategy ever end?
        """
        return True

    def getCount(self):
        """
        Return the number of test cases.
        """
        return None

    def next(self):
        """
        Go to next test sequence. Throws MutatorCompleted when we are done.
        """
        raise MutatorCompleted()

    def currentMutator(self):
        """
        Return the current Mutator in use.
        """
        pass

    def onTestCaseStarting(self, test, count, stateEngine):
        """
        Called as we start a test case.

        :param test: current Test being run
        :type test: Test
        :param count: current test number
        :type count: int
        :param stateEngine: StateEngine instance in use
        :type stateEngine: StateEngine
        """
        pass

    def onTestCaseFinished(self, test, count, stateEngine):
        """
        Called as we exit a test case

        :param test: current Test being run
        :type test: Test
        :param count: current test number
        :type count: int
        :param stateEngine: StateEngine instance in use
        :type stateEngine: StateEngine
        """
        pass

    def onFaultDetected(self, test, count, stateEngine, results, actionValues):
        """
        Called if a fault was detected during our current test case.

        :param test: current Test being run
        :type test: Test
        :param count: current test number
        :type count: int
        :param stateEngine: StateEngine instance in use
        :type stateEngine: StateEngine
        :param results: monitor results
        :type results: dict
        :param actionValues: values used to perform test
        :type actionValues: dict
        """
        pass

    def onStateMachineStarting(self, stateEngine):
        """
        Called as we enter the state machine.

        :param stateEngine: StateEngine instance in use
        :type stateEngine: StateEngine
        """
        pass

    def onStateMachineFinished(self, stateEngine):
        """
        Called as we exit the state machine.

        :param stateEngine: StateEngine instance in use
        :type stateEngine: StateEngine
        """
        pass

    def onStateStarting(self, stateEngine, state):
        """
        Called as we enter a new state.

        :param stateEngine: StateEngine instance in use
        :type stateEngine: StateEngine
        :param state: State
        :type state: current state
        """
        pass

    def onStateFinished(self, stateEngine, state):
        """
        Called as we exit a state.

        :param stateEngine: StateEngine instance in use
        :type stateEngine: StateEngine
        :param state: State
        :type state: current state
        """
        pass

    def onStateChange(self, currentState, newState):
        """
        Called before state is changed. If result if non-None we can select
        a different state to change to.

        :param currentState: current state
        :type currentState: State
        :param newState: new state we are moving to
        :type newState: State
        :returns: None or a different state instance
        :rtype: State
        """
        return None

    def onActionStarting(self, state, action):
        """
        Called as we enter an action.

        :param state: current state
        :type state: State
        :param action: action we are starting
        :type action: Action
        """
        pass

    def onActionFinished(self, state, action):
        """
        Called as we exit an action.

        :param state: current state
        :type state: State
        :param action: action we are starting
        :type action: Action
        """
        pass

    def onDataModelGetValue(self, action, dataModel):
        """
        Called before getting a value from a data model.

        :param action: action we are starting
        :type action: Action
        :param dataModel: data model we are using
        :type dataModel: DataModel
        """
        pass
