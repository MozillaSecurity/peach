# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
import struct
from types import *
from Peach import generator, group
from Peach.generator import *

#__all__ = ['Incrementor', 'PerCallIncrementor', 'PerRoundIncrementor']

class Incrementor(generator.Generator):
    """
    Increment a value by another value each round. For example,
    one could set 1 as an initial value with an incrementor of 1.
    """

    _roundCount = 0
    _value = None
    _incrementor = None
    _currentValue = None
    _formatString = None
    _maxValue = None
    _maxIterations = None
    _packString = None

    def __init__(self, group=None, value=1, incrementor=1, formatString=None,
                 maxValue=None, maxIterations=None, packString=None):
        """
        @type	group: Group
        @param	group: Group this generator works with
        @type	value: number
        @param	value: Number to increment
        @type	incrementor: number
        @param	incrementor: Increment amount (can be negative), default is 1
        @type	formatString: string
        @param	formatString: Format string for value (optional)
        @type	maxValue: number
        @param	maxValue: Maximum value (optional, default None)
        @type	maxIterations: number
        @param	maxIterations: Maximum number of times to increment
                value (optional, default None)
        @type	packString: string
        @param	packString: Pack format string.  Note that use of this
                option will override formatString. (optional, default None)
        """
        Generator.__init__(self)
        self._value = value
        self._incrementor = incrementor
        self._formatString = formatString
        self._maxValue = maxValue
        self._maxIterations = maxIterations
        self._packString = packString
        self.setGroup(group)

    def next(self):
        self._roundCount += 1

        if self._currentValue is None:
            self._currentValue = self._value
        else:
            self._currentValue += self._incrementor

        if self._maxValue:
            if self._currentValue > self._maxValue:
                raise generator.GeneratorCompleted('Generators.Incrementor: maxValue')
        if self._maxIterations:
            if self._roundCount > self._maxIterations:
                raise generator.GeneratorCompleted('Generators.Incrementor: maxIterations')

    def reset(self):
        self._roundCount = 0
        self._currentValue = None

    def getRawValue(self):
        if self._currentValue is None:
            self._currentValue = self._value

        ret = None

        if self._packString is not None:
            ret = struct.pack(self._packString, self._currentValue)
        else:
            if self._formatString is None:
                retType = type(self._currentValue)
                if retType is IntType:
                    ret = "%d" % self._currentValue
                elif retType is FloatType:
                    ret = "%f" % self._currentValue
                elif retType is LongType:
                    ret = "%d" % self._currentValue
            else:
                ret = self._formatString % self._currentValue

        return ret

    def setValue(self, value):
        """
        Set value to increment.

        @type	value: number
        @param	value: Number to increment
        """
        self._value = value

    @staticmethod
    def unittest():
        g = group.GroupFixed(5)
        inc = Incrementor(g, 1, 1)

        try:
            while g.next():
                print(inc.getValue())
        except group.GroupCompleted:
            pass

        g = group.GroupFixed(5)
        inc = Incrementor(g, 1, 10, "<<%d>>")

        try:
            while g.next():
                print(inc.getValue())
        except group.GroupCompleted:
            pass

        g = group.GroupFixed(5)
        inc = Incrementor(g, 1, 0.212673, "[[%0.2f]]")

        try:
            while g.next():
                print(inc.getValue())
        except group.GroupCompleted:
            pass


class PerCallIncrementor(generator.Generator):
    """
    Each call to getValue will increment.  Usefull to make a string
    unique accross fuzz.
    """

    _incrementor = None

    def __init__(self, group=None, value=1, incrementor=1, formatString=None):
        """
        @type	group: Group
        @param	group: Group this generator works with
        @type	value: number
        @param	value: Number to increment
        @type	incrementor: number
        @param	incrementor: Amount to increment
        @type	formatString: string
        @param	formatString: Format string for value (optional)
        """
        generator.Generator.__init__(self)
        self._incrementor = Incrementor(group, value, incrementor, formatString)

    def next(self):
        raise generator.GeneratorCompleted('PerCallIncrementor')

    def reset(self):
        self._incrementor.reset()

    def getRawValue(self):
        ret = self._incrementor.getRawValue()
        self._incrementor.next()
        return ret

    def setValue(self, value):
        """
        Set value to increment.

        @type	value: number
        @param	value: Number to increment
        """
        self._incrementor.setValue(value)

    @staticmethod
    def unittest():
        g = group.GroupFixed(5)
        inc = PerCallIncrementor(g, 1, 0.212673, "[[%0.2f]]")

        try:
            while g.next():
                print(inc.getValue())
                print(inc.getValue())
                print(inc.getValue())
        except group.GroupCompleted:
            pass


class PerRoundIncrementor(generator.Generator):
    """
    Each round we increment. Has it's uses :)
    """

    _incrementor = None

    def __init__(self, value=1, incrementor=1, formatString=None):
        """
        @type	value: number
        @param	value: Number to increment
        @type	incrementor: number
        @param	incrementor: Amount to increment
        @type	formatString: string
        @param	formatString: Format string for value (optional)
        """
        self._incrementor = Incrementor(None, value, incrementor, formatString)

    def next(self):
        self._incrementor.next()
        raise generator.GeneratorCompleted('PerCallIncrementor')

    def reset(self):
        self._incrementor.reset()

    def getRawValue(self):
        return self._incrementor.getRawValue()

    def setValue(self, value):
        """
        Set value to increment.

        @type	value: number
        @param	value: Number to increment
        """
        self._incrementor.setValue(value)

    @staticmethod
    def unittest():
        g = group.GroupFixed(5)
        inc = PerCallIncrementor(g, 1, 0.212673, "[[%0.2f]]")
        try:
            while g.next():
                print(inc.getValue())
                print(inc.getValue())
                print(inc.getValue())
        except group.GroupCompleted:
            pass
