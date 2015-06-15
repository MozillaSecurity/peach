# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


class Generator(object):
    """
    Generators generate data. Examples of generators could be a static string
    or integer, a string repeater, etc. Generators can be "incremented" by
    calling C{next()} to produce the next variant of data. Generators can be
    fairly complex, combining sub-generators to build things like packets.

    Generators support the iterator protocol and can be used as such.

    When building a Generator one should keep in mind that the value from a
    generator could be asked for more then once per "round". Also it is
    recommended that you use the default C{getValue()} implementation and
    override the C{getRawValue()} method instead.

    @see: L{SimpleGenerator}
    """

    def __init__(self):
        """Base constructor, please call me!"""
        self._group = None
        self._transformer = None
        self._identity = None  # Stack-trace of were we came from
        self._name = None

        # For debugging.
        # This is slow (0.02 sec), sometimes this init function can get called
        # like 50K times during initialization of a large fuzzing object tree!
        # self._identity = traceback.format_stack()

    def identity(self):
        """Who are we and were do we come from?"""
        return self._identity

    def __iter__(self):
        """
        Return iterator for Generator object. This is always the Generator
        object  itself.

        @rtype: Generator
        @return: Returns iterator, this is always self.
        """
        return self

    def next(self):
        """For Generators, please use the GeneratorCompleted exception instead
        of StopIteration (its a subclass)."""
        raise GeneratorCompleted("Peach.generator.Generator")

    def getValue(self):
        """Return data, passed through a transformer if set.

        @rtype: string
        @return: Returns generated data
        """
        if self._transformer is not None:
            return self._transformer.encode(self.getRawValue())
        return self.getRawValue()

    def getRawValue(self):
        """Return raw value without passing through transformer if set.

        @rtype: string
        @return: Data before transformations
        """
        return None

    def getGroup(self):
        """Get the group this Generator belongs to. Groups are used to
        increment sets of Generators.

        @rtype: Group
        @return: Returns Group this generator belongs to
        """
        return self._group

    def setGroup(self, group):
        """
        Set the group this Generator belongs to. This function will
        automatically add the Generator into the Group. Groups are used to
        increment sets of Generators.

        @type	group: Group
        @param	group: Group this generator belongs to
        """
        self._group = group
        if self._group is not None:
            self._group.addGenerator(self)

    def getTransformer(self):
        """
        Get transformer (if set). Transformers are used to transform data in
        some way (such as HTML encoding, etc).

        @rtype: Transformer
        @return: Current transformer or None
        """
        return self._transformer

    def setTransformer(self, trans):
        """
        Set transformer. Transformers are used to transform data in some way
        (such as HTML encoding, etc).

        @type	trans: Transformer
        @param	trans: Transformer to run data through
        @rtype: Generator
        @return: self
        """
        self._transformer = trans
        return self

    def reset(self):
        """Called to reset the generator to its initial state."""
        pass

    def getName(self):
        """Get the name of this generator. Useful for debugging."""
        return self._name

    def setName(self, name):
        """
        Set the name of this generator. Useful for debugging complex data
        generators. Stack-traces may end up in a generator creation statement
        giving limited feedback on which generator in an array might be causing
        the problem.

        @type	name: string
        @param	name: Name of generator
        """
        self._name = name


class SimpleGenerator(Generator):
    """
    A simple generator contains another, possibly complex generator statement.
    Useful when breaking things apart for reuse.

    To use, simply create a class that contains a _generator:

        class MySimpleGenerator(SimpleGenerator):
            def __init__(self, group = None):
                SimpleGenerator.__init__(self, group)
                self._generator = GeneratorList(None, [
                    Static('AAA'),
                    Repeater(None, Static('A'), 1, 100)
                    ])

    NOTE: Do not set group on you generators unless they will not be
    incremented by self._generator.next().
    """

    def __init__(self, group=None):
        """
        @type	group: Group
        @param	group: Group to use
        """
        Generator.__init__(self)
        self.setGroup(group)
        self._generator = None

    def next(self):
        self._generator.next()

    def getRawValue(self):
        return self._generator.getValue()

    def reset(self):
        self._generator.reset()


class GeneratorCompleted(StopIteration):
    """
    Exception indicating that the generator has completed all permutations of
    its data.
    """
    pass
