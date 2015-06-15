# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
import traceback
from Peach import generator

#__all__ = ["Group", "GroupFixed", "GroupSequence", "GroupForeachDo"]


class Group(object):
    """
    Groups allow for performing a C{next()} call on a specific set of
    Generators allowing for more complex Fuzzing setups.  This default group
    object will iterate an infinite amount of times.

    Group objects implement the iterator protocol.
    """

    _name = None
    _generators = []
    _identity = ""

    def __init__(self, name=None):
        """
        Create a new Group object.

        @type	name: string
        @param	name: Name of Group object.  Not currently used.
        """
        self._name = name
        self._generators = []

        # For debugging.  This is slow (0.02 sec), if things are slow
        # you can comment this line out safely.
        self._identity = traceback.format_stack()

    def getName(self):
        """
        Get current name of Group.  Not currently used.

        @rtype: string
        @return: name of Group
        """
        return self._name

    def setName(self, name):
        """
        Set name of Group.  Not currently used.

        @type	name: string
        @param	name: Name of Group
        """
        self._name = name

    def addGenerator(self, gen):
        """
        Add Generator to Group.  This should almost never be called
        directly.  Generators will call this when you set there Group.
        However, you can do some crazy stuff by adding a Generator into
        multiple Groups so they iterate themselves in strange ways.

        @type	gen: Generator
        @param	gen: Generator to add
        """
        self._generators.append(gen)

    def addGenerators(self, gens):
        """
        Add Generators to Group.  This should almost never be called
        directly.  Generators will call this when you set there Group.
        However, you can do some crazy stuff by adding a Generator into
        multiple Groups so they iterate themselves in strange ways.

        @type	gens: Array of Generators
        @param	gens: Generatorsto add
        """
        for g in gens:
            self._generators.append(g)

    def removeGenerator(self, gen):
        """
        Remove Generator from Group.

        @type	gen: Generator
        @param	gen: Generator to remove
        """
        self._generators.remove(gen)

    def getAllGenerators(self):
        """
        Returns list of all generators in Group.  This is a reference
        to our internal list so any changes will also affect the Group.

        @rtype: Array
        @return: Returns Array of strings
        """
        return self._generators

    def __iter__(self):
        return self

    def next(self):
        """
        Iterate all Generators to next value.

        From Python docs on next():

        I{The intention of the protocol is that once an iterator's next() method
        raises StopIteration, it will continue to do so on subsequent calls.
        Implementations that do not obey this property are deemed broken. (This
        constraint was added in Python 2.3; in Python 2.2, various iterators are
        broken according to this rule.)}

        For Groups, please use the GroupCompleted exception instead of
        StopIteration (its a subclass).
        """

        # We will continue until all of our generators are
        # returning GeneratorCompleted exceptions

        if len(self._generators) < 1:
            print("Identity of Group: %s" % self._identity)
            raise Exception("Error: Group does not contain any generators.  This is probably not a good thing.")

        done = 1

        for i in range(len(self._generators)):
            try:
                self._generators[i].next()
                done = 0
            except generator.GeneratorCompleted:
                pass

        if done == 1:
            raise GroupCompleted()

    def reset(self):
        """
        Resets all Generators to there initial state.
        """
        for i in self._generators:
            i.reset()


class GroupCompleted(StopIteration):
    """
    Raised when group has completed all iterations.  This exception is a
    sub class of StopIteration.
    """
    pass


class GroupSequence(Group):
    """
    A sequence of groups.  Each group will be iterated until they are
    completed in sequence.

    This is also a container type and can be used as such to gain
    access to the contained groups.

    HINT: If groups param is an integer it will create an array of
          Group() objects of that length that can be accessed using
          the array specifier groupSequence[x].
    """

    def __init__(self, groups=None, name=None):
        """
        Create a GroupSequence object.

        @type	groups: list
        @param	groups: Optional list of Groups to use
        """

        self._slackerCount = 0

        if name is None:
            self._name = ""
        else:
            self._name = name

        self._generators = []

        # Hack allert!
        if str(type(groups)) == "<type 'int'>":
            self._groups = []
            for i in range(groups):
                self._groups.append(Group())

        elif groups is not None:
            self._groups = groups

        else:
            self._groups = []
        self._position = 0
        self._count = 1

    def getNextGroup(self):
        """
        This is a function for slackers that allows access to the next group
        without having to specify an index.

        @rtype: Group
        @return: Returns the next Group in the list
        """
        if self._slackerCount >= len(self._groups):
            raise Exception("GroupSequence: getNextGroup() ran past end of array.")
        self._slackerCount += 1
        return self._groups[self._slackerCount - 1]

    def addNewGroup(self, newGroup=None):
        """
        Will add a new Group to sequence of groups and then return that group.

        @type	newGroup: Group
        @param	newGroup: [optional] Group to append, or if not given add Group()
        @rtype: Group
        @return: Returns appended Group
        """
        if newGroup is None:
            newGroup = Group()

        self._groups.append(newGroup)
        return newGroup

    def append(self, group=None):
        """
        Append a Group.

        @type	group: Group
        @param	group: Group to append
        @rtype: Group
        @return: Returns appended Group
        """
        return self.addNewGroup(group)

    def remove(self, group):
        """
        Remove a Group.

        @type	group: Group
        @param	group: Group to remove
        """
        self._groups.remove(group)

    def next(self):
        if self._position < len(self._groups):
            try:
                self._groups[self._position].next()
                self._count += 1
            except GroupCompleted:
                #sys.stderr.write('%s: GroupSequence.next(): GroupCompleted [%d]\n' % (self._name, self._count))
                self._count = 1
                self._groups[self._position].reset()
                self._position += 1
                if self._position >= len(self._groups):
                    raise GroupCompleted()
        else:
            raise GroupCompleted()

    def reset(self):
        for group in self._groups:
            group.reset()
        self._position = 0


    # Container emulation methods ############################

    def __len__(self):
        return self._groups.__len__()

    def __getitem__(self, key):
        return self._groups.__getitem__(key)

    def __setitem__(self, key, value):
        return self._groups.__setitem(key, value)

    def __delitem__(self, key):
        return self._groups.__delitem__(key)

    def __iter__(self):
        return self._groups.__iter__()

    def __contains__(self, item):
        return self._groups.__contains__(item)


import inspect, pyclbr, random


class GroupForever(Group):
    """
    This group will take a GroupSequence and perform random mutations
    on how generators are incremented.  This group understands that a
    GroupSequence can have other GroupSequences in it.
    """

    def __init__(self, groupSequence):

        self.groupSequence = groupSequence
        self.groups = self._findAllGroups(groupSequence)
        self.count = len(self.groups)

        self._resetAll()
        self._pickStuff()

    def addGroup(self, group):
        self.groups.append(group)

        for g in self._findAllGroups(group):
            self.groups.append(g)

    def _resetAll(self):

        print("len: %d" % len(self.groups))
        for group in self.groups:
            group.reset()

    def _pickStuff(self):
        """Pick some groups to play with
        """

        # Types of mutations
        #
        # 1. Bunch at once
        # 2. A for each

        type = random.randint(0, 1)

        if type == 0:
            # bunch at once
            groupsDo = []
            picks = random.sample(range(self.count), random.randint(0, self.count - 1))
            for pick in picks:
                groupsDo.append(self.groups[pick])

            self.currentGroup = GroupSequence(groupsDo, "GroupForever")

        elif type == 1:
            # a for each
            groupEach = groupFor = self.groups[random.randint(0, self.count - 1)]
            groupsDo = []

            picks = random.sample(range(self.count), random.randint(0, self.count - 1))
            for pick in picks:
                groupsDo.append(self.groups[pick])

            try:
                groupsDo.remove(groupEach)
            except:
                pass

            groupDo = GroupSequence(groupsDo, "GroupForever")

            self.currentGroup = GroupForeachDo(groupEach, groupDo)

        else:
            raise Exception("GroupForever._pickStuff(): Should not be here!!")

        self.isCompleted = False

    def _findAllGroups(self, groupSequence):

        if hasattr(groupSequence, 'next') and hasattr(groupSequence, '__iter__'):
            groups = []

            for group in groupSequence:
                if group is None:
                    continue

                groups.append(group)

                if hasattr(group, 'next') and hasattr(group, '__iter__'):
                    for g in self._findAllGroups(group):
                        if g is None:
                            continue

                        groups.append(g)

            return groups

        if hasattr(groupSequence, "getForeachGroup"):
            return [group.getForeachGroup(), group.getDoGroup()]

        return []

    def next(self):

        try:
            self.currentGroup.next()
        except GroupCompleted:
            self._resetAll()
            self._pickStuff()

    def reset(self):
        self._resetAll()
        self._pickStuff()


class GroupFixed(Group):
    """
    Group object with a fixed number of iterations.
    """

    _max = 0
    _current = 0

    def __init__(self, maxIterations=0):
        """
        Create GroupFixed object.

        @type	maxIterations: number
        @param	maxIterations: Maximum number of iterations.
        """
        self._max = maxIterations
        Group.__init__(self)

    def getMaxIterations(self):
        """
        Get the maximum iterations to perform.

        @rtype: number
        @return the maximum iterations
        """
        return self._max

    def setMaxIterations(self, maxIterations):
        """
        Set the maximum iterations to perform.

        @type	maxIterations: number
        @param	maxIterations: Maximum number of iterations.
        """
        self._max = maxIterations

    def next(self):
        if self._current < self._max:
            self._current += 1
            try:
                Group.next(self)
            except generator.GeneratorCompleted:
                raise GroupCompleted("Peach.group.GroupFixed")
        else:
            raise GroupCompleted("Peach.group.GroupFixed")


class GroupForeachDo(Group):
    """
    For each iteration of group A do group B
    """

    #_groupA = None
    #_groupB = None

    def __init__(self, groupA, groupB, verbose=True, name=""):
        """
        For each iteration of group A do group B

        @type	groupA: Group
        @param	groupA: The for each of group
        @type	groupB: Group
        @param	groupB: The Do group
        @type	verbose: Boolean
        @param	verbose: [optional] Control printing of group completed message, enabled by default.
        """
        self._generators = []
        self._groupA = groupA
        self._groupB = groupB
        self._count = 1
        self._name = name
        self._verbose = verbose
        self._isCompleted = False

    def next(self):

        if self._isCompleted:
            raise GroupCompleted("We are done")

        try:
            self._groupB.next()
            self._count += 1
        except GroupCompleted:
            if self._verbose:
                print("%s: GroupForeachDo.GroupCompleted -- [%d]" % (self._name, self._count))

            self._count = 1
            self._groupB.reset()

            try:
                self._groupA.next()
            except GroupCompleted:
                self._isCompleted = True

    def reset(self):
        self._groupA.reset()
        self._groupB.reset()
        self._count = 1
        self._isCompleted = False

    def getForeachGroup(self):
        """
        Returns the For each group
        """
        return self._groupA

    def getDoGroup(self):
        """
        Returns the Do group
        """
        return self._groupB
