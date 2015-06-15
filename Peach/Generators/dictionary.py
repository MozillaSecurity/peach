# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
import static
import struct
from Peach import generator, group
from Peach.group import GroupSequence
from Peach.generator import *
from Peach.Generators.block import Block3
from Peach.Generators.static import *

#__all__ = ['Dictionary', 'GeneratorList', 'GeneratorList2', 'List', 'BinaryList']


class Flags2(SimpleGenerator):
    """
    Define the layout of flags and provide a generator for each.  Each flag
    has a position, length, and generator.  The Flag itself also has a total
    length and byte order (litte or big).  If values generated for each field in
    the flag are masked such as they always fit and do not affect other fields
    in the flag.

    Example:

        >>> gen = Flags2(None, 8, [ [0, 1, Bit()], [4, 1, Bit()], [6, 2, List(None, [0, 1, 2])] ])
        >>> print gen.getValue()
        0
        >>> gen.next()
        >>> print gen.getValue()
        81
        >>> gen.next()
        >>> print gen.getValue()
        145
        >>> gen.next()
        >>> print gen.getValue()
        209

    """

    def __init__(self, group, length, flags, isLittleEndian=True):
        """
        @type	group: Group
        @param	group: Group for this Generator
        @type	length: Integer
        @type	length: Length of flag field, must be 8, 16, 32, or 64.
        @type	flags: Array of Arrays
        @param 	flags: Each sub-array must contain a position (zero based),
                       length (in bits), and a generator.
        """
        SimpleGenerator.__init__(self, group)

        if length % 2 != 0:
            raise Exception("Invalid length argument.  Length must be multiple of 2!")

        for flag in flags:
            if flag[0] > length:
                raise Exception("Flag position larger then length")
            if (flag[0] + flag[1]) > length:
                raise Exception("Flag position + flag length larger then length")

        self.length = length
        self.flags = flags

    # flags needs to contain position and length

    def next(self):
        done = True

        for flag in self.flags:
            try:
                flag[2].next()
                done = False
            except GeneratorCompleted:
                pass

        if done:
            raise GeneratorCompleted("Flags are done")

    def getRawValue(self):
        ret = 0

        for flag in self.flags:
            mask = 0x00 << self.length - (flag[0] + flag[1])

            cnt = flag[0] + flag[1] - 1
            for i in range(flag[1]):
                #print "<< %d" % cnt
                mask |= 1 << cnt
                cnt -= 1

            #print "Mask:",repr(mask)
            flagValue = flag[2].getValue()
            if flagValue is None or flagValue == 'None':
                flagValue = 0

            ret |= mask & (int(flagValue) << flag[0])

        return ret


class Dictionary(generator.Generator):
    """
    Iterates through a collection of values stored in a file.
    Possible uses could be to brute force passwords or try a set of
    known bad values.
    """

    _fileName = None
    _fd = None
    _currentValue = None

    def __init__(self, group, fileName):
        """
        @type	group: Group
        @param	group: Group this Generator belongs to
        @type	fileName: string
        @param	fileName: Name of file use
        """
        Generator.__init__(self)
        self._fileName = fileName
        self.setGroup(group)

    def getFilename(self):
        """
        Get name of file.

        @rtype: string
        @return: name of file
        """
        return self._fileName

    def setFilename(self, filename):
        """
        Set filename.

        @type	filename: string
        @param	filename: Filename to use
        """
        self._fileName = filename

    def next(self):
        if self._fd is None:
            self._fd = open(self._fileName, 'rb')
            if self._fd is None:
                raise Exception('Unable to open', self._fileName)

        oldValue = self._currentValue
        self._currentValue = self._fd.readline()
        if self._currentValue is None or len(self._currentValue) == 0:
            self._currentValue = oldValue
            raise generator.GeneratorCompleted("Dictionary completed for file [%s]" % self._fileName)

        self._currentValue = self._currentValue.rstrip("\r\n")

    def getRawValue(self):
        if self._fd is None:
            self._fd = open(self._fileName, 'rb')
            if self._fd is None:
                raise Exception('Unable to open', self._fileName)

        if self._currentValue is None:
            self._currentValue = self._fd.readline()
            self._currentValue = self._currentValue.rstrip("\r\n")

        return self._currentValue

    def reset(self):
        self._fd = None
        self._currentValue = None

    @staticmethod
    def unittest():
        g = group.Group()
        dict = Dictionary(g, 'samples/dict.txt')

        try:
            while g.next():
                print(dict.getValue())
        except group.GroupCompleted:
            pass

        g.reset()

        try:
            while g.next():
                print(dict.getValue())
        except group.GroupCompleted:
            pass


class List(generator.Generator):
    """
    Iterates through a specified list of values.  When the end of the list is
    reached a generator.GeneratorCompleted exceoption is raised.  Last item
    will be returned until reset is called.

    Example:

        >>> list = List(None, ['1', '2', '3'])
        >>> list.getValue()
        1
        >>> list.next()
        >>> list.getValue()
        2
        >>> list.next()
        >>> list.getValue()
        3

    """

    _list = None
    _curPos = 0

    def __init__(self, group, list=None):
        """
        @type	group: Group
        @param	group: Group this Generator belongs to
        @type	list: list
        @param	list: List of values to iterate through
        """
        Generator.__init__(self)
        self.setGroup(group)
        self._list = list
        self._curPos = 0

        if self._list is None:
            self._list = []

    def reset(self):
        self._curPos = 0

    def next(self):
        self._curPos += 1
        if self._curPos >= len(self._list):
            self._curPos -= 1
            raise generator.GeneratorCompleted("List")

    def getRawValue(self):
        return self._list[self._curPos]

    def getList(self):
        """
        Get current list of values.

        @rtype: list
        @return: Current list of values
        """
        return self._list

    def setList(self, list):
        """
        Set list of values.

        @type	list: list
        @param	list: List of values
        """
        self._list = list

        if self._list is None:
            self._list = []

    @staticmethod
    def unittest():
        g = group.Group()
        list = List(g, ['A', 'B', 'C', 'D'])

        if list.getValue() != 'A':
            raise Exception("List unittest failed 1")
        g.next()
        if list.getValue() != 'B':
            raise Exception("List unittest failed 2")
        g.next()
        if list.getValue() != 'C':
            raise Exception("List unittest failed 3")
        g.next()
        if list.getValue() != 'D':
            raise Exception("List unittest failed 4")

        try:
            g.next()
            raise Exception("List unittest failed 5")
        except group.GroupCompleted:
            pass

        try:
            g.next()
            raise Exception("List unittest failed 5")
        except group.GroupCompleted:
            pass

        if list.getValue() != 'D':
            raise Exception("List unittest failed 6")

        list = List(g, [1, 2, 3, 4, 5])

        try:
            while g.next():
                print(list.getValue())
        except group.GroupCompleted:
            pass


class BinaryList(List):
    """
    Iterates through a specified list of binary values.  When the end
    of the list is reached a generator.GeneratorCompleted exceoption
    is raised.
    """

    _packString = 'b'

    def __init__(self, group, list=None, packString=None):
        """
        @type	group: Group
        @param	group: Group this Generator belongs to
        @type	list: list
        @param	list: List of values to iterate through
        @type	packString: string
        @param	packString: Defaults to 'b'
        """
        Generator.__init__(self)
        List.__init__(self, group, list)
        self._packString = packString

    def getRawValue(self):
        out = self._list[self._curPos]
        if self._packString is not None:
            return struct.pack(self._packString, out)

        return out

    @staticmethod
    def unittest():
        g = group.Group()
        list = BinaryList(g, [0, 1, 2, 3], '>B')

        try:
            while g.next():
                print(list.getValue())
        except group.GroupCompleted:
            pass


class _ArrayList(generator.Generator):
    """Internal helper class"""

    def __init__(self, listOfLists):
        self._listOfLists = listOfLists
        self._pos = 0
        self._block = Block(self._listOfLists[self._pos])

    def getRawValue(self):
        return self._block

    def next(self):
        if (self._pos + 1) >= len(self._listOfLists):
            raise generator.GeneratorCompleted("ArrayList")

        self._pos += 1
        self._block = Block(self._listOfLists[self._pos])

    def reset(self):
        self._pos = 0


import random


class GeneratorChoice(generator.Generator):
    """
    Will choose from a list of Generators.  See use cases below for
    further description of operation:

    Case 1 - minOccurs and maxOccurs are 1.  In this case a single
             generator is selected N times.
    Case 2 - minOccurs is 1 and maxOccurs is 100.  In this case
             N sets of random items are chosen.
    Case 3 - minOccurs is 0 and maxOccurs is 1.  You will always
             get 1 case were 0 items are chosen and 1 case of
             other items chosen

    Currently N == 10.

    """

    def __init__(self, group, minOccurs, maxOccurs, groups, list, n=10, name=None):
        """
        @type	group: Group
        @param	group: Group this Generator belongs to
        @type	list: list
        @param	list: List of Generators to choose frome
        @type	name: string
        @type	name: Name of generator
        """

        generator.Generator.__init__(self)

        self.n = n
        self.minOccurs = minOccurs
        self.maxOccurs = maxOccurs
        self._curPos = 0
        self.setName(name)

        if group is not None:
            self.setGroup(group)

        self._groups = groups
        self._list = list

        if self._list is None or self._groups is None:
            raise Exception("groups and list cannot be None.")

        if len(self._list) != len(self._groups):
            raise Exception("groups and list must have same number of items!")

        if len(self._list) < self.maxOccurs:
            self.maxOccurs = len(self._list)

        # handle case 1 - minOccurs == 1 and maxOccurs == 1
        if self.minOccurs == 1 and self.maxOccurs == 1:

            theGroups = []
            theItems = []

            # select a single generator
            if len(self._list) <= self.n:
                sample = range(len(self._list))
            else:
                sample = random.sample(range(len(self._list)), self.n)

            for n in sample:
                theGroups.append(self._groups[n])
                theItems.append(self._list[n])

            self.generator = GeneratorList2(None, theGroups, theItems)

        # handle case 3 -- minOccurs == 0, maxOccurs == 1
        elif self.minOccurs == 0 and self.maxOccurs == 1:
            theGroups = []
            theItems = []

            if self.maxOccurs - self.minOccurs <= self.n:
                sample = range(self.maxOccurs - self.minOccurs)

            else:
                sample = random.sample(range(len(self._list)), self.n)

            for n in sample:
                theGroups.append(self._groups[n])
                theItems.append(self._list[n])

            self.generator = GeneratorList(None, [
                Static(''),
                GeneratorList2(None, theGroups, theItems)
            ])

        # handle case 2 - minOccurs == 1, maxOccurs == 100
        else:

            theGeneratorLists = []
            sample = None

            if self.maxOccurs - self.minOccurs <= self.n:
                sample = range(self.maxOccurs - self.minOccurs)

            else:
                sample = random.sample(range(self.minOccurs, self.maxOccurs), self.n)

            for n in sample:

                theGroups = []
                theItems = []

                subSample = random.sample(range(len(self._list)), n)
                subSample.sort()

                # remove dups
                old = -1
                newSample = []
                for x in subSample:
                    if x != old:
                        old = x
                        newSample.append(x)

                subSample = newSample
                for x in subSample:
                    theGroups.append(self._groups[x])
                    theItems.append(self._list[x])

                theGeneratorLists.append(Block3(GroupSequence(theGroups), theItems))

            self.generator = GeneratorList(None, theGeneratorLists)

    def next(self):
        self.generator.next()

    def reset(self):
        self.generator.reset()

    def getRawValue(self):
        return self.generator.getValue()


class GeneratorList(generator.Generator):
    """
    Iterates through a specified list of generators.  When the end of the list is
    reached a generator.GeneratorCompleted exceoption is raised.

    NOTE: Generators are incremented by this object so DON'T SET A GROUP ON THEM!

    NOTE: We only increment to next generator in list when the GeneratorCompleted
    exception has been thrown from current generator.  This allows one todo kewl
    things like have 2 static generators, then a dictionary, then a repeater.

    Example:

        >>> gen = GeneratorList(None, [
        ... 	Static('1'),
        ... 	Static('2'),
        ... 	Static('3')
        ... 	])
        >>> print gen.getValue()
        1
        >>> gen.next()
        >>> print gen.getValue()
        2
        >>> gen.next()
        >>> print gen.getValue()
        3
        >>> try:
        ... 	gen.next()	# Will raise GeneraterCompleted exception
        ... except:
        ... 	pass
        >>> print gen.getValue() # notice we get last value again.
        3

    Example:

        >>> gen = GeneratorList(None, [
        ... 	Repeater(None, Static('Peach'), 1, 2),
        ... 	Static('Hello World')
        ... 	])
        >>> print gen.getValue()
        Peach
        >>> gen.next()
        >>> print gen.getValue()
        PeachPeach
        >>> gen.next()
        >>> print gen.getValue()
        Hello World
        >>> try:
        ... 	gen.next()	# Will raise GeneraterCompleted exception
        ... except:
        ... 	pass
        >>> print gen.getValue() # notice we get last value again.
        Hello World

    Bad Example, group set on Generator in list:

        >>> group = Group()
        >>> gen = GeneratorList(group, [
        ... 	Repeater(group, Static('Peach'), 1, 2),
        ... 	Static('Hello World')
        ... 	])
        >>> print gen.getValue()
        Peach
        >>> group.next()
        >>> print gen.getValue()
        Hello World
        >>> try:
        ... 	gen.next()	# Will raise GeneraterCompleted exception
        ... except:
        ... 	pass
        >>> print gen.getValue() # notice we get last value again.
        Hello World

    """

    def __init__(self, group, list, name=None):
        """
        @type	group: Group
        @param	group: Group this Generator belongs to
        @type	list: list
        @param	list: List of Generators to iterate through
        @type	name: string
        @type	name: Name of generator
        """

        Generator.__init__(self)

        self._curPos = 0

        self.setName(name)

        if group is not None:
            self.setGroup(group)

        self._list = list

        if self._list is None:
            self._list = []

    def next(self):
        try:
            self._list[self._curPos].next()
        except generator.GeneratorCompleted:
            #print "Peach.dictionary.GeneratorList2.next(): caught GeneratorCompleted"
            self._curPos += 1

        if self._curPos >= len(self._list):
            self._curPos -= 1
            #print "Peach.dictionary.GeneratorList2.next(): throwing complete exceptions"
            raise generator.GeneratorCompleted("Peach.dictionary.GeneratorList")

    def reset(self):
        self._curPos = 0

        for i in self._list:
            i.reset()

    def getRawValue(self):
        # Use .getValue to make sure we
        # pick up any transformers
        value = self._list[self._curPos].getValue()
        #if value is None:
        #	print "Peach.dictionary.GeneratorList.getRawValue(): getValue() was None"
        #	print "Peach.dictionary.GeneratorList.getRawValue(): Name is %s" % self._list[self._curPos].getName()
        #	print "Peach.dictionary.GeneratorList.getRawValue(): Type is %s" % self._list[self._curPos]

        return value

    def getList(self):
        """
        Get list of Generators.

        @rtype: list
        @return: list of Generators
        """
        return self._list

    def setList(self, list):
        """
        Set list of Generators.

        @type	list: list
        @param	list: List of Generators
        """
        self._list = list

        if self._list is None:
            self._list = []

    @staticmethod
    def unittest():
        g = group.Group()
        list = GeneratorList(g, [static.Static('A'), static.Static('B'), static.Static('C')])

        try:
            while g.next():
                print(list.getValue())
        except group.GroupCompleted:
            pass


class GeneratorList2(GeneratorList):
    """
    Iterates through a specified list of generators (different group control).
    When the end of the list is reached a generator.GeneratorCompleted exceoption
    is raised.

    This generator differs from GeneratorList by allowing one group to
    drive the rounds, but associating different sub groups to each generator.
    When the master group is incremented the group for the current generator is
    also incremented.  This allows more complex control of how generators
    create data.

    NOTE: We only increment to next generator in list when the GeneratorCompleted
    exception has been thrown from current generator.  This allows one todo kewl
    things like have 2 static generators, then a dictionary, then a repeater.

    Example:

        >>> groupA = Group()
        >>> groupBA = Group()
        >>> groupBB = Group()
        >>> groupB = GroupForeachDo(groupBA, groupBB)
        >>>
        >>> gen = GeneratorList2(None, [groupA,	groupB], [
        ... 	Repeater(groupA, Static('A'), 1, 1, 3),
        ... 	Block([
        ... 		List(groupBA, [':', '\\', '/']),
        ... 		Repeater(groupBB, Static('B'), 1, 1, 3)
        ... 		])
        ... 	])
        >>>
        >>> print gen.getValue()
        A
        >>> gen.next()
        >>> gen.getValue()
        AA
        >>> gen.next()
        >>> gen.getValue()
        AAA
        >>> gen.next()
        >>> gen.getValue()
        :B
        >>> gen.next()
        >>> gen.getValue()
        :BB
        >>> gen.next()
        >>> gen.getValue()
        :BBB
        >>> gen.next()
        >>> gen.getValue()
        \B
        >>> gen.next()
        >>> gen.getValue()
        \BB
        >>> gen.next()
        >>> gen.getValue()
        \BBB
        >>> gen.next()
        >>> gen.getValue()
        /B
        >>> gen.next()
        >>> gen.getValue()
        /BB
        >>> gen.next()
        >>> gen.getValue()
        /BBB

    @see: L{GeneratorList}
    """

    #_groupList = None

    def __init__(self, group, groupList=None, list=None, name=None):
        """
        @type	group: Group
        @param	group: Group this Generator belongs to
        @type	groupList: list
        @param	groupList: List of Groups to use on generators
        @type	list: list
        @param	list: List of Generators to iterate through
        @type	name: String
        @param	name: [optional] Name for this Generator.  Used for debugging.
        """
        Generator.__init__(self)
        self.setGroup(group)
        self.generators = self._list = list
        self.groups = self._groupList = groupList
        self.setName(name)
        self._curPos = 0

        if self._list is None:
            self._list = []
        if self._groupList is None:
            self._groupList = []

        self.reset()

    def next(self):
        try:
            self._groupList[self._curPos].next()
        #print "GeneratorList2.next(): ..."
        except group.GroupCompleted:
            #print "GeneratorList2.next(): Next pos [%d]" % self._curPos
            #print "GeneratorList2.next(): %d items in our list" % len(self._list)
            self._curPos += 1
            if self._curPos < len(self._list):
                self._groupList[self._curPos].reset()
        #except:
        #	print "GeneratorList2.next(): Caught some other exception"

        if self._curPos >= len(self._list):
            self._curPos -= 1
            #print "%s: GeneratorList2.next() Completed" % name
            raise generator.GeneratorCompleted("Peach.dictionary.GeneratorList2")

    def setGroups(self, list):
        """
        Set list of Groups.

        @type	list: list
        @param	list: List of Groups
        """
        self._groupList = list

        if self._groupList is None:
            self._groupList = []

    def reset(self):
        self._curPos = 0

        for i in self._list:
            i.reset()

        for i in self._groupList:
            i.reset()

    @staticmethod
    def unittest():
        g = group.Group()
        list = GeneratorList2(g, [static.Static('A'), static.Static('B'), static.Static('C')])

        try:
            while g.next():
                print(list.getValue())
        except group.GroupCompleted:
            pass


class GeneratorListGroupMaster(GeneratorList2):
    """
    Provides a mechanism to create in effect a group of GeneratorList2's that
    will progress and increment together drivin by the master of the group.  This
    Generator is the Group Master generator and controls the slaves of the
    group.

    This generator comes in handy when you have two bits of data that are
    logically linked but in separate places.  An example would be a length of
    data being generated.  Both values are parameters and generated separaetly
    but a test calls for performing different length tests against different
    data being generated (zero length data and 100 bytes of data say) which
    would be a subset of the noramally generated data.

    Example:

        >>> groupNormalBlock = Group()
        >>> groupForeachBlock = Group()
        >>> groupDoLength = Group()
        >>> groupForeachBlockDoLength = GroupForeachDo(groupForeachBlock, groupDoLength)
        >>>
        >>> genBlock = GeneratorListGroupMaster(None, [
        ... 	groupNormalBlock,
        ... 	groupForeachBlockDoLength
        ... 	], [
        ...
        ... 	# Our normal tests
        ... 	GeneratorList(groupNormalBlock, [
        ... 		Static('A'),
        ... 		Static('BB'),
        ... 		]),
        ...
        ... 	# For each of these do all the length tests
        ... 	GeneratorList(groupForeachBlock, [
        ... 		Static(''),
        ... 		Static('PEACH' * 10),
        ... 		]),
        ... 	])
        >>>
        >>> genLength = GeneratorListGroupSlave([
        ...		None,
        ... 	None,
        ... 	], [
        ... 	# generated value for the normal block tests
        ... 	BlockSize(genBlock),
        ...
        ... 	# actual length tests
        ... 	GeneratorList(groupDoLength, [
        ... 		NumberVariance(None, BlockSize(genBlock), 20),
        ... 		BadNumbers(),
        ... 		])
        ... 	], genBlock)
        >>>
        >>> print genBlock.getValue()
        A
        >>> print genLength.getValue()
        1
        >>> genBlock.next()
        >>> print genBlock.getValue()
        BB
        >>> print genLength.getValue()
        2
        >>> genBlock.next()
        >>> print genBlock.getValue()

        >>> print genLength.getValue()
        -20


    """

    _slaves = []
    _completed = False

    def __init__(self, group, groupList, list, slaves=None, name=None):
        """
        @type	group: Group
        @param	group: Group this Generator belongs to
        @type	groupList: list
        @param	groupList: List of Groups to use on generators
        @type	list: list
        @param	list: List of Generators to iterate through
        @type	name: String
        @param	name: [optional] Name for this Generator.  Used for debugging.
        """
        GeneratorList2.__init__(self, group, groupList, list, name)

        if slaves is not None:
            self._slaves = slaves
        else:
            self._slaves = []

    def next(self):

        if self._completed:
            raise generator.GeneratorCompleted("Peach.dictionary.GeneratorListGroupMaster")

        moveNext = True

        # next our current generator
        try:
            self._groupList[self._curPos].next()
            moveNext = False
        except group.GroupCompleted:
            pass

        # next the generator for each of our slaves
        for slave in self._slaves:
            try:
                slave.slaveNext()
                moveNext = False
            except group.GroupCompleted:
                pass

        if moveNext:
            print("GeneratorListGroupMaster.next(): Next pos [%d]" % self._curPos)

            if (self._curPos + 1) >= len(self._list):
                self._completed = True

                # Let the slaves know we are done
                for slave in self._slaves:
                    slave.slaveCompleted()

                raise generator.GeneratorCompleted("Peach.dictionary.GeneratorListGroupMaster")

            # Move us and everyone else to next position
            self._curPos += 1
            for slave in self._slaves:
                slave.slaveNextPosition()

    def reset(self):
        self._completed = False
        self._curPos = 0

        for i in self._list:
            i.reset()

        for i in self._groupList:
            i.reset()

        for slave in self._slaves:
            slave.reset()

    def addSlave(self, slave):
        self._slaves.append(slave)


class GeneratorListGroupSlave(GeneratorList2):
    """
    Provides a mechanism to create in effect a group of GeneratorList2's that
    will progress and increment together drivin by the master of the group.  This
    Generator is the slave of ghr group and is controlled by the master.  More
    then one slave can be part of the group.

    This generator comes in handy when you have two bits of data that are
    logically linked but in separate places.  An example would be a length of
    data being generated.  Both values are parameters and generated separaetly
    but a test calls for performing different length tests against different
    data being generated (zero length data and 100 bytes of data say) which
    would be a subset of the noramally generated data.

    Example:

        >>> groupNormalBlock = Group()
        >>> groupForeachBlock = Group()
        >>> groupDoLength = Group()
        >>> groupForeachBlockDoLength = GroupForeachDo(groupForeachBlock, groupDoLength)
        >>>
        >>> genBlock = GeneratorListGroupMaster(None, [
        ... 	groupNormalBlock,
        ... 	groupForeachBlockDoLength
        ... 	], [
        ...
        ... 	# Our normal tests
        ... 	GeneratorList(groupNormalBlock, [
        ... 		Static('A'),
        ... 		Static('BB'),
        ... 		]),
        ...
        ... 	# For each of these do all the length tests
        ... 	GeneratorList(groupForeachBlock, [
        ... 		Static(''),
        ... 		Static('PEACH' * 10),
        ... 		]),
        ... 	])
        >>>
        >>> genLength = GeneratorListGroupSlave([
        ...		None,
        ... 	None,
        ... 	], [
        ... 	# generated value for the normal block tests
        ... 	BlockSize(genBlock),
        ...
        ... 	# actual length tests
        ... 	GeneratorList(groupDoLength, [
        ... 		NumberVariance(None, BlockSize(genBlock), 20),
        ... 		BadNumbers(),
        ... 		])
        ... 	], genBlock)
        >>>
        >>> print genBlock.getValue()
        A
        >>> print genLength.getValue()
        1
        >>> genBlock.next()
        >>> print genBlock.getValue()
        BB
        >>> print genLength.getValue()
        2
        >>> genBlock.next()
        >>> print genBlock.getValue()

        >>> print genLength.getValue()
        -20

    """

    _master = None
    _completed = False

    def __init__(self, groupList=None, list=None, master=None, name=None):
        """
        @type	group: Group
        @param	group: Group this Generator belongs to
        @type	groupList: list
        @param	groupList: List of Groups to use on generators
        @type	list: list
        @param	list: List of Generators to iterate through
        @type	master: GeneratorListGroupMaster
        @param	master: The master for this groupping.  Will register self with master
        @type	name: String
        @param	name: [optional] Name for this Generator.  Used for debugging.
        """

        if groupList is None:
            groupList = []
        if list is None:
            list = []

        GeneratorList2.__init__(self, None, groupList, list, name)
        self._name = name

        if master is not None:
            master.addSlave(self)

    def next(self):
        if self._completed:
            raise generator.GeneratorCompleted("Peach.dictionary.GeneratorListGroupSlave")

    def slaveNext(self):
        if self._groupList[self._curPos] is not None:
            self._groupList[self._curPos].next()
        else:
            raise group.GroupCompleted("Peach.dictionary.GeneratorListGroupSlave")


    def slaveNextPosition(self):
        print("%s slaveNextPosition" % self._name)
        self._curPos += 1

        if self._curPos >= len(self._list):
            print(self._name)
            raise Exception(
                "%s Ran off end of generator array!!: %d of %d" % (self._name, self._curPos, len(self._list)))

    def slaveCompleted(self):
        self._completed = True

    def reset(self):
        self._completed = False
        self._curPos = 0

        for i in self._list:
            i.reset()

        for i in self._groupList:
            if i is not None:
                i.reset()
