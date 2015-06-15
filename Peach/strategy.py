# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from Engine.common import *


class StrategyError(PeachException):
    """Strategy Exception"""
    pass


class RouteDescriptor(object):
    """Used to describe the route."""

    def __init__(self):
        self.paths = []
        self.index = 0

    def addPath(self, path):
        if path is None:
            raise PeachException("Argument 'path' cannot be None!")
        self.paths.append(path)

    def reset(self):
        self.index = 0

    def clear(self):
        del self.paths[:]

    def hasNextSingle(self):
        """
        This method is handy when there is no pair but only a path.
        """
        return len(self.paths) == 1 and self.index < len(self.paths)

    def nextSingle(self):
        """
        To get the current path.
        """
        if not self.hasNextSingle():
            raise PeachException("End of the route description is reached!")
        self.index += 1
        return self.paths[self.index - 1]

    def hasNextPair(self):
        """
        Returns True when it has two paths more to visit otherwise False.
        """
        return self.index < len(self.paths) - 1

    def nextPair(self):
        """
        Returns the next pair which strategy will find a proper path in
        between. If hasNextPair() returns False then this method completes
        the pair to be returned with a None and yields the result.
        """
        if not self.hasNextPair():
            raise PeachException("End of the route-pairs is reached!")
        self.index += 1
        return [self.paths[self.index - 1], self.paths[self.index]]


class Strategy(object):
    """
    Strategy is an abstract class that is used to define a method to find out
    a route	between start and destination paths.
    """

    def __init__(self, stateMachine, routeDescriptor, params=None):
        self.params = {}
        if params is not None:
            self.params = params
        if routeDescriptor is None:
            raise PeachException("Argument 'routeDescriptor' cannot be None!")
        self.routeDesc = routeDescriptor
        self.stateMachine = stateMachine

    def getRoute(self):
        """
        This method invokes abstract _findRoute method for each pair taken
        from routeDescriptor to obtain a proper route and finally returns
        the route.
        """
        route = []
        while self.routeDesc.hasNextPair():
            start, destination = self.routeDesc.nextPair()
            partialRoute = self._findRoute(start, destination)
            if len(route) == 0:
                route.extend(partialRoute)
            else:
                route.extend(partialRoute[1:])
        if self.routeDesc.hasNextSingle():
            lastPath = self.routeDesc.nextSingle()
            route.extend(self._findRoute(lastPath, None))
        return route

    def _findRoute(self, start, destination):
        """
        This method is used to explore a route(list of paths) in between
        start and destination paths.

        :param start: start path
        :param destination: destination path
        :returns: a list of paths starting with parameter start and ending
                  with parameter destination.
        """
        pass

    def _reset(self):
        """
        Used to reset a strategy especially when re-discovering the route.
        """
        self.routeDesc.reset()


class StrategyCollection(Strategy):
    """
    This class behaves like a proxy between strategies defined in XML file,
    which is used to run all the strategies respectively to produce a
    resultant route.
    """

    def __init__(self):
        Strategy.__init__(self, None, RouteDescriptor())
        self.strategies = []
        self.route = None

    def addStrategy(self, strategy):
        self.strategies.append(strategy)
        # Re-explore the route as we have a new strategy.
        self._reset()

    def getRoute(self):
        if self.route is not None:
            return self.route
        self.route = []
        for strategy in self.strategies:
            self.route.extend(strategy.getRoute())
        return self.route

    def _reset(self):
        self.route = None
        for strategy in self.strategies:
            strategy._reset()


class StrategyFactory(object):
    """
    To centralize the creation of strategies.
    """

    def __init__(self, defStrategy="default.StaticStrategy"):
        self.defStrategy = defStrategy

    def createStrategy(self, stateMachine, routeDescriptor,
                       clazz=None, params=None):
        if clazz is None:
            clazz = self.defStrategy
        try:
            code = clazz + "(stateMachine, routeDescriptor, params)"
            print("StrategyFactory.createStrategy: {}".format(code))
            strategy = eval(code)
            if strategy is None:
                raise PeachException("Unable to create Strategy [{}]"
                                     .format(clazz))
            return strategy
        except:
            raise PeachException("Unable to create Strategy [{}]"
                                 .format(clazz))
