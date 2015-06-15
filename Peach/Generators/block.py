# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from Peach import generator, group
from Peach.Generators.repeater import *
from Peach.Generators.incrementor import Incrementor
import random

#__all__ = ["Block", "BlockSize", "Block2"]

class Block(generator.Generator):
    """
    Block is a set of Generators in a specific order who's values are combined
    into a block of data.  The L{BlockSize} generator can be used to output
    the size of the block or other generators.

    Example:

      >>> gen = Block([
      ...  Static('Hello'),
      ...  Static(' '),
      ...  Static('World')
      ...  ])
      >>> print gen.getValue()
      Hello World

    @note: This type of block will not call .next() on the generators it
    contains.  See L{Block2} or L{Block3} for that.

    @note: Do not use with L{DictionaryList} generator.  Will cause
    infinitlooping since the .next() is never called on sub generators.

    @see: L{MultiBlock}, L{Block2}, L{Block3}, L{BlockSize}, L{MultiBlockCount}
    """

    def __init__(self, generators=None):
        """
        @type	generators: List
        @param	generators: List of generators
        @type	alignment: Integer
        @param	alignment: How to align block.  Just like with a struct.
        """

        generator.Generator.__init__(self)

        self._inGetValue = 0
        self._inRawValue = 1
        self._generators = None

        if generators is None:
            self._generators = []
        else:
            self._generators = generators

    def next(self):
        """
        Note: We arn't going to next on any of the sub
        generators.  This is left to the group or whatever todo.
        """
        pass

    def reset(self):
        """
        Even though we don't propogate .next calls we should
        reset things.
        """
        for g in self._generators:
            g.reset()

    def getValue(self):
        self._inGetValue = 1
        ret = ''

        for i in range(len(self._generators)):
            try:
                ret += str(self._generators[i].getValue())
            except TypeError as e:
                print("\nPeach.block.Block: Caught type error, here is identification information")
                print(e)
                print("self._generators[i].getName(): %s" % self._generators[i].getName())
                if self._generators[i].identity() is not None:
                    print("self._generators[i].identity: (%s) =====" % self._generators[i])
                    for p in self._generators[i].identity():
                        print(p)
                    print("===============")
                else:
                    print("self._generators[i].identity: None!")

                raise e

        if self._transformer is not None:
            return self._transformer.encode(ret)

        self._inGetValue = 0
        return ret

    def getRawValue(self):
        self._inRawValue = 1
        ret = ''

        for i in range(len(self._generators)):
            ret += self._generators[i].getRawValue()

        self._inRawValue = 0
        return ret

    def getSize(self):
        """
        Size of generator after all transformations

        @rtype: number
        @return: size of data generated
        """
        return len(str(self.getValue()))

    def append(self, generator):
        """
        Append a generator to end of list.

        @type	generator: Generator
        @param	generator: Generator to append
        """
        self._generators.append(generator)

    def insert(self, pos, generator):
        """
        Insert generator into list

        @type	generator: Generator
        @param	generator: Generator to insert
        """
        self._generators.insert(pos, generator)

    def remove(self, generator):
        """
        Remove a generator from list

        @type	generator: Generator
        @param	generator: Generator to remove
        """
        self._generators.remove(generator)

    def clear(self):
        """
        Clear list of generators.
        """
        self._generators = []

    def setGenerators(self, generators):
        """
        Set array of generators.

        @type	generators: list
        @param	generators: list of Generator objects
        """
        self._generators = generators

    # Container emulation methods ############################

    def __len__(self):
        return self._generators.__len__()

    def __getitem__(self, key):
        return self._generators.__getitem__(key)

    def __setitem__(self, key, value):
        return self._generators.__setitem(key, value)

    def __delitem__(self, key):
        return self._generators.__delitem__(key)

    def __iter__(self):
        return self._generators.__iter__()

    def __contains__(self, item):
        return self._generators.__contains__(item)


class MultiBlockCount(generator.Generator):
    """
    Generates the number of occurances of a MultiBlock generator.

    Example:

        >>> block = MultiBlock([ Static('12345') ], 0, 100, Static(1))
        >>> blockCount = MultiBlockCount( block )
        >>> print blockCount.getValue()
        1

    @see: L{MultiBlock}
    """

    def __init__(self, block, defaultOccurs=1):
        """
        @type	block: MultiBlock
        @param	block: MultiBlock to get count of
        @type	defaultSize: number
        @param	defaultSize: To avoid recursion this is our occurs (optional)
        """
        generator.Generator.__init__(self)
        self.setBlock(block)
        self._defaultOccurs = defaultOccurs
        self._insideSelf = False
        self._inGetRawValue = False

    def getValue(self):
        """
        Return data, passed through a transformer if set.
        """
        out = self.getRawValue()
        if self._transformer is not None and self._inGetRawValue == 0:
            out = self._transformer.encode(out)

        return out

    def getRawValue(self):
        """
        Returns size of block as string.

        @rtype: string
        @return: size of specified Block
        """

        if self._inGetRawValue or self._block is None:
            return str(self._defaultOccurs)

        # Call getValue to make sure MultiBlock
        # has set occurs to correct value.
        self._inGetRawValue = True
        self._block.getValue()
        self._inGetRawValue = False

        return self._block.occurs

    def getBlock(self):
        """
        Get block object we act on.

        @rtype: Block
        @return: current Block
        """
        return self._block

    def setBlock(self, block):
        """
        Set block we act on.

        @type	block: Block
        @param	block: Block to set.
        """
        self._block = block
        return self


class Block2(Block):
    """
    Specialized type of L{Block} that will call next() on each generator.

    Use this type of block with L{GeneratorList}s.

    Example:

      >>> gen = GeneratorList(None, [
      ...	Block2([
      ...		Static('Hello'),
      ...		Static(' '),
      ...		Repeater(None, Static('World'), 1, 2)
      ...		])
      ...	])
      >>> print gen.getValue()
      Hello World
      >>> gen.next()
      >>> print gen.getValue()
      Hello WorldWorld

    @see: L{Block}, L{Block3}, L{BlockSize}
    """

    def next(self):
        exit = 0
        for i in self._generators:
            try:
                i.next()
                exit = 2
            except:
                if exit < 2:
                    exit = 1
        if exit == 1:
            raise generator.GeneratorCompleted("Block2")

    def reset(self):
        for i in self._generators:
            try:
                i.reset()
            except AttributeError:
                raise Exception("Block2: Attribute Error! %s" % i)


class Block3(Block):
    """
    A Block that takes a group to perform .next() on.  The BlockSize generator
    can be used to output the block size someplace.

    This is a specialized version of Block.  This version will
    call next() the provided Group.  This was added to make complex
    sub-blocks work properly.
    """

    def __init__(self, group, generators):
        """
        @type	group: Group
        @param	group: Group to perform .next() on
        @type	generators: List
        @param	generators: List of generators
        """

        generator.Generator.__init__(self)

        self._nextGroup = group
        self._generators = generators

    def next(self):
        try:
            self._nextGroup.next()
        except group.GroupCompleted:
            raise generator.GeneratorCompleted("Block3")

    def reset(self):
        self._nextGroup.reset()

        for i in self._generators:
            try:
                i.reset()
            except AttributeError:
                raise Exception("Block3: Attribute Error! %s" % i)


class BlockSize(generator.Generator):
    """
    Will generate size of Block or another Generator.  BlockSize can
    can detect recursive calls and provides an optional defaultSize
    that can be set for such cases.

    Example:

        >>> block = Block([ Static('12345') ])
        >>> blockSize = BlockSize( block )
        >>> print blockSize.getValue()
        5

    """

    _inGetRawValue = 0

    def __init__(self, block, defaultSize=1):
        """
        @type	block: Block
        @param	block: Block to get size of
        @type	defaultSize: number
        @param	defaultSize: To avoid recursion this is how big we are
        (optional)
        """
        generator.Generator.__init__(self)
        self._block = None
        self.setBlock(block)
        self._defaultSize = defaultSize
        self._insideSelf = False

    def getValue(self):
        """
        Return data, passed through a transformer if set.
        """
        out = self.getRawValue()
        #print "block.BlockSize::getValue(): out = %s" % out
        if self._transformer is not None and self._inGetRawValue == 0:
            out = self._transformer.encode(out)

        #print "block.BlockSize::getValue(): out = %s" % out
        return out

    def getRawValue(self):
        """
        Returns size of block as string.

        @rtype: string
        @return: size of specified Block
        """

        if self._inGetRawValue == 1:
            # Avoid recursion and return a string
            # that is defaultSize in length
            return str(self._defaultSize)

        self._inGetRawValue = 1
        out = str(len(str(self._block.getValue())))
        self._inGetRawValue = 0
        return out

    def getBlock(self):
        """
        Get block object we act on.

        @rtype: Block
        @return: current Block
        """
        return self._block

    def setBlock(self, block):
        """
        Set block we act on.

        @type	block: Block
        @param	block: Block to set.
        """
        self._block = block
        return self


import random


class BlockRandomizer(generator.SimpleGenerator):
    """
    This block takes a number of sub-blocks or generators
    that it will include or not include in variouse combinations
    and orders.
    """

    def __init__(self, group, okGenerators, notOkGenerators, limit=1024, seed=10312335):
        """
        @type	group: Group
        @param	group: Group to perform .next() on
        @type	okGenerators: Array of Generator objects
        @param	okGenerators: The expected data blocks to mix and match
        @type	notOkGenerators: Array of Generator objects
        @param	notOkGenerators: The unexpected data blocks to mix and match
        @type	limit: Number
        @param	limit: [optional] Limit the number of possible test variations.  Defaults to 1024.
        @type	seed: Number
        @param	seed: [optional] A random number generator is used and can be seeded.  Defaults to 10312335.
        """

        generator.SimpleGenerator.__init__(self, group)

        self._generators = okGenerators
        self._okGenerators = okGenerators
        self._notOkGenerators = notOkGenerators
        self._limit = limit
        self._seed = seed
        self._count = 0
        self._testSet = 1

        random.seed(self._seed)


    def _resetGenerators(self):
        # Reset all the completed generators
        for gen in self._generators:
            try:
                gen.reset()
            except:
                pass

    def next(self):

        if -1 < self._limit <= self._count:
            raise generator.GeneratorCompleted("BlockRandomizer hit its max!")

        done = True
        for gen in self._generators:
            try:
                gen.next()
                done = False
            except:
                pass

        if done:
            self._count += 1
            self.nextTest()

    def copyArray(self, array):
        newArray = []

        for a in array:
            newArray.append(a)

        return newArray

    def inArray(self, array, item):
        for i in array:
            if i == item:
                return True

        return False

    def nextTest(self):

        test = random.randint(1, 4)
        notOk = random.randint(0, 1)

        genOk = self.copyArray(self._okGenerators)
        genNotOk = self.copyArray(self._notOkGenerators)

        if test == 1:
            random.shuffle(genOk)
            self._generators = genOk

        elif test == 2:
            sample = random.sample(genOk, random.randint(1, len(genOk)))
            gens = []

            for g in genOk:

                if self.inArray(sample, g):
                    for i in range(random.randint(1, 20)):
                        g.reset()
                        gens.append(g)

                else:
                    gens.append(g)

            self._generators = gens

        elif test == 3:
            sample1 = random.sample(genOk, random.randint(1, len(genOk) / 2))
            sample2 = random.sample(genNotOk, random.randint(1, len(genNotOk) / 2))

            gens = []
            for g in sample1:
                gens.append(g)
            for g in sample2:
                gens.append(g)

            random.shuffle(gens)

            self._generators = gens

        elif test == 4:
            self._generators = random.sample(genOk, random.randint(1, len(genOk) / 2))

        # Reset all our generators
        self._resetGenerators()

    def reset(self):
        self._generators = self._okGenerators

    def getValue(self):
        self._inGetValue = 1
        ret = ''

        for i in range(len(self._generators)):
            try:
                ret += str(self._generators[i].getValue())
            except TypeError as e:
                print("\nPeach.block.Block: Caught type error, here is identification information")
                print(e)
                print("self._generators[i].getName(): %s" % self._generators[i].getName())
                if self._generators[i].identity() is not None:
                    print("self._generators[i].identity: (%s) =====" % self._generators[i])
                    for p in self._generators[i].identity():
                        print(p)
                    print("===============")
                else:
                    print("self._generators[i].identity: None!")

                raise e

        if self._transformer is not None:
            return self._transformer.encode(ret)

        self._inGetValue = 0
        return ret

    def getRawValue(self):
        self._inRawValue = 1
        ret = ''

        for i in range(len(self._generators)):
            ret += self._generators[i].getRawValue()

        self._inRawValue = 0
        return ret

    def getSize(self):
        """
        Size of generator after all transformations

        @rtype: number
        @return: size of data generated
        """
        return len(self.getValue())


from Peach.Generators.dictionary import List


class MultiBlock(generator.Generator):
    """
    Specialized type of L{Block} that will duplicate itself a certain/random number of times.

    @see: L{Block}, L{MultiBlockCount}
    """

    _seed = 1192315309984

    def __init__(self, group, generators, minOccurs=1, maxOccurs=1, genOccurs=None):
        """
        @type	generators: List
        @param	generators: List of Generator objects
        @type	minOccurs: Number
        @param	minOccurs: Minimum number of times this block can occur, defaults to 1
        @type	maxOccurs: Number
        @param	maxOccurs: Maximum number of times this block can occur, defaults to 1
        @type	genOccurs: Generator
        @param	genOccurs: [Optional] Generator that produces number of occurances
        """
        generator.Generator.__init__(self)
        self.setGroup(group)

        self._block = Block(generators)
        self.minOccurs = minOccurs
        self.maxOccurs = maxOccurs

        if self.minOccurs == 0:
            self.defaultOccurs = 1
        else:
            self.defaultOccurs = self.minOccurs

        # setup a generator to produce our occurs values
        # or accept a generator for this
        if genOccurs is None:

            if self.maxOccurs - self.minOccurs < 255:
                # Produce all occurs
                self.genOccurs = Incrementor(None, self.minOccurs, 1, None, self.maxOccurs)

            else:
                # Produce a random sampling of numbers
                step = (self.maxOccurs - self.minOccurs) / 255
                self.genOccurs = List(None, range(self.minOccurs, self.maxOccurs, step))
                self.genOccurs.getList().insert(0, self.defaultOccurs)
                self.genOccurs.getList().append(self.maxOccurs)

                if self.minOccurs > 0:
                    self.genOccurs.getList().append(self.minOccurs - 1)

                self.genOccurs.getList().append(self.maxOccurs + 1)

        else:
            self.genOccurs = genOccurs

        # Setup our first occurs
        self.occurs = int(self.genOccurs.getValue())

    def setGenOccurs(self, genOccurs):
        self.genOccurs = genOccurs
        self.occurs = int(self.genOccurs.getValue())

    def next(self):
        self.genOccurs.next()
        self.occurs = int(self.genOccurs.getValue())

    def reset(self):
        self.genOccurs.reset()
        self.occurs = int(self.genOccurs.getValue())

    def getRawValue(self):
        return self._block.getRawValue() * self.occurs

    def getSize(self):
        """
        Size of generator after all transformations

        @rtype: number
        @return: size of data generated
        """
        return len(self.getValue())

    def append(self, generator):
        """
        Append a generator to end of list.

        @type	generator: Generator
        @param	generator: Generator to append
        """
        self._block.append(generator)

    def insert(self, pos, generator):
        """
        Insert generator into list

        @type	generator: Generator
        @param	generator: Generator to insert
        """
        self._block.insert(pos, generator)

    def remove(self, generator):
        """
        Remove a generator from list

        @type	generator: Generator
        @param	generator: Generator to remove
        """
        self._block.remove(generator)

    def clear(self):
        """
        Clear list of generators.
        """
        self._block.clear()

    def setGenerators(self, generators):
        """
        Set array of generators.

        @type	generators: list
        @param	generators: list of Generator objects
        """
        self._block.setGenerators(generators)

    # Container emulation methods ############################

    def __len__(self):
        return self._block.__len__()

    def __getitem__(self, key):
        return self._block.__getitem__(key)

    def __setitem__(self, key, value):
        return self._block.__setitem(key, value)

    def __delitem__(self, key):
        return self._block.__delitem__(key)

    def __iter__(self):
        return self._block.__iter__()

    def __contains__(self, item):
        return self._block.__contains__(item)
