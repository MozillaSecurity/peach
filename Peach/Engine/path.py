# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from Peach.Engine.common import *

#Deactivate strategies
#from Peach.strategy import *
class _Path(object):
    def __init__(self, domPath):
        self.stateName = domPath.ref
        self.stop = domPath.stop


class PathFinder(object):
    def __init__(self, stateMachine):
        if stateMachine is None:
            raise PathException("PathFinder:: parameter 'stateMachine' cannot be None")

        self.stateMachine = stateMachine
        self.index = 0
        self.paths = None

    def firstPath(self):
        firstPath = None
        if len(self.getRoute()) > 0:
            firstPath = self.getRoute()[0]

        return firstPath

    def lastPath(self):
        lastPath = None
        if len(self.getRoute()) > 0:
            lastPath = self.getRoute()[-1]

        return lastPath

        #lastPath = [path for path in self.getRoute() if path.stop == True]
        #if len(lastPath) > 0:
        #    return lastPath[0].ref

        #if len(self.getRoute())>0:
        #    return self.getRoute()[-1]

    def canMove(self):
        return self.index < len(self.getRoute())

    def next(self):
        if not self.canMove():
            raise PathException("PathFinder:: End of paths reached :: unable to move to next path")

        nextPath = self.getRoute()[self.index]
        self.index += 1
        return nextPath

    def current(self):
        if self.index == 0:
            return None

        return self.getRoute()[self.index - 1]

    def reset(self):
        self.index = 0

    def getRoute(self):
        if not self.paths:
            self.paths = [_Path(p) for p in self.stateMachine.getRoute()]

        return self.paths


'''
@note: this part will be implemented soon to add Strategy functionality

class PathFinderWithStrategy(PathFinder):
	
	def __init__(self, stateMachine):
		PathFinder.__init__(self, stateMachine)
		self.strategyColl = self._getStrategyCollection()
	
	def getRoute(self):
		return self.strategyColl.getRoute()
	
	#Returns the collection of strategies that are defined in XML
	#If no strategy is declared then default one(staticStrategy) will be used.
	
	
	def _getStrategyCollection(self):
		coll = StrategyCollection()
		factory = StrategyFactory()
		routeDescriptor = RouteDescriptor()
		for child in self.stateMachine:
			if child.elementType == 'path':
				routeDescriptor.addPath(child)
				
			elif child.elementType == 'strategy':
				if not routeDescriptor.hasNextSingle():
					PeachException("At least one Path must be defined previous to a Strategy!")

				strategy = factory.createStrategy(self.stateMachine, routeDescriptor, child.classStr, child.params)
				coll.addStrategy(strategy)
				
				#renew routeDescriptor since it is used by this strategy
				routeDescriptor = RouteDescriptor()
		
		
		if routeDescriptor.hasNextSingle() or routeDescriptor.hasNextPair():
			# create default strategy
			strategy =  factory.createStrategy(self.stateMachine, routeDescriptor)
			coll.addStrategy(strategy)
			
		return coll 
'''


class PathValidator(object):
    def __init__(self, pathFinder, validationMutator):
        if pathFinder is None:
            raise PathException("PathValidator: parameter 'pathFinder' must be assigned")

        self.pathFinder = pathFinder
        self.validationMutator = validationMutator

    def validate(self):
        # Reset pathFinder to guarantee
        self.pathFinder.reset()

        # Do we have a path declared in XML?
        if not self.pathFinder.canMove():
            raise PathException(
                "PathValidator: No path definition found for the stateMachine[%s]." % self.pathFinder.stateMachine.name)

        # Okay then check if stateMachine's initialState is the same
        # with the first path reference or not!
        if self.pathFinder.firstPath().stateName != self.pathFinder.stateMachine.initialState:
            raise PathException(
                "PathValidator: Initial state name[%s] of the StateMachine[%s] must be the same with the first path reference[%s]." % (
                    self.pathFinder.stateMachine.initialState, self.pathFinder.stateMachine.name,
                    self.pathFinder.firstPath()))

        # Check if final state contains Choice node or not
        # if it is then basically we don't know what to do
        # raise an exception
        lastPath = self.pathFinder.lastPath()
        if not lastPath.stop:
            lastState = self.pathFinder.stateMachine.findStateByName(lastPath.stateName)
            if lastState.getChoice() is not None:
                raise PathException(
                    "PathValidator: Invalid path definition. Final state[%s] must not contain Choice element." % lastState.name)

        # Validate state transition references
        thisState = self.pathFinder.next()
        while self.pathFinder.canMove():
            nextState = self.pathFinder.next()

            if not self._isNextState(thisState.stateName, nextState.stateName):
                raise PathException(
                    "PathValidator: Invalid path definition at StateMachine[%s]. State[%s] does not contain state[%s] in its choice list." % (
                        self.pathFinder.stateMachine.name, thisState.stateName, nextState.stateName))

            # Advancing to the next state so equate thisState to nextState
            thisState = nextState

        # Now check traced route
        self.pathFinder.reset()

        if len(self.validationMutator.states) < len(self.pathFinder.getRoute()):
            raise PeachException(
                "Invalid path. StateMachine[%s] violated path definition declared in XML file." % self.pathFinder.stateMachine.name)

        while self.pathFinder.canMove():
            currPath = self.pathFinder.next()
            if currPath.stateName != self.validationMutator.states[self.pathFinder.index - 1]:
                raise PeachException(
                    "Invalid path. StateMachine[%s] violated path definition declared in XML file." % self.pathFinder.stateMachine.name)
                #elif currPath.stop and (len(mutator.states) > stateEngine.pathFinder.index):
                #	raise PeachException("Invalid path. StateMachine[%s] must stop at the State[%s]." % (stateMachine.name, currPath.ref))

                # Clear ;)

    def _isNextState(self, stateName, nextStateName):
        ret = False
        state = self.pathFinder.stateMachine.findStateByName(stateName)
        choice = state.getChoice()
        if choice is not None:
            if choice.findActionByRef(nextStateName) is not None:
                ret = True
        else:
            # Basically if we have only one changeState action
            # then we already know the nextState
            actions = [action for action in state if action.elementType == 'action' and action.type == 'changeState']
            if len(actions) == 1:
                ret = (actions[0].ref == nextStateName)

            if len(actions) < 1 or not ret:
                raise PathException(
                    "PathValidator: State[%s] must have only one changeState action referenced to state[%s] or explicitly declare a choice list containing a path reference to state[%s]" % (
                        stateName, nextStateName, nextStateName))

        return ret


class PathException(object):
    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return self.msg

# end
