# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
import struct

import static
from Peach.generator import *
from Peach.Generators.dictionary import *
from Peach.Generators.static import *
from Peach.Generators.data import *
from Peach.Generators.repeater import *
from Peach.Generators.block import *
from Peach.group import *
from Peach.Generators import constants
import Peach.Transformers.Type.Integer


class BadStrings(SimpleGenerator):
    """
    Generates various string tests. Examples of data generated:

        - Variations on format strings using '%n'
        - Long string
        - Empty string
        - Extended ASCII
        - Common bad ASCII (' " < >)
        - All numbers
        - All letters
        - All spaces
        - etc.
    """

    values = constants.StringMutator

    def __init__(self, group=None):
        SimpleGenerator.__init__(self, group)
        self._generator = List(None, self.values)


class BadTime(SimpleGenerator):
    """
    Test cases for HTTP-Date type
    """

    def __init__(self, group=None):
        SimpleGenerator.__init__(self, group)

        groupSeq = [Group(), Group(), Group()]

        self._generator = GeneratorList2(
            None,
            [
                groupSeq[0],
                groupSeq[1],
                groupSeq[2],
            ],
            [
                Block([
                 GeneratorList(groupSeq[0], [
                     Static('08'),
                     BadStrings(),
                     BadNumbers(),
                     Static('08')
                 ]),
                 Static(':01:01')
                ]),
                Block([
                 Static('08:'),
                 GeneratorList(groupSeq[1], [
                     Static('08'),
                     BadStrings(),
                     BadNumbers(),
                     Static('08')
                 ]),
                 Static(':01')
                ]),
                Block([
                 Static('08:01'),
                 GeneratorList(groupSeq[2], [
                     Static('08'),
                     BadStrings(),
                     BadNumbers(),
                     Static('08')
                 ])
                ])
            ])


class BadDate(SimpleGenerator):
    """
    [BETA] Generates a lot of funky date's. This Generator is still missing
    a lot of test cases.

        - Invalid month, year, day
        - Mixed up stuff
        - Crazy odd date formats
    """

    _strings = [
        '1/1/1',
        '0/0/0',
        '0-0-0',
        '00-00-00',
        '-1/-1/-1',
        'XX/XX/XX',
        '-1-1-1-1-1-1-1-1-1-1-1-',
        'Jun 39th 1999',
        'June -1th 1999',

        # ANSI Date formats
        '2000',
        '1997',
        '0000',
        '0001',
        '9999',

        '0000-00',
        '0000-01',
        '0000-99',
        '0000-13',
        '0001-00',
        '0001-01',
        '0001-99',
        '0001-13',
        '9999-00',
        '9999-01',
        '9999-99',
        '9999-13',

        '0000-00-00',
        '0000-01-00',
        '0000-99-00',
        '0000-13-00',
        '0001-00-00',
        '0001-01-00',
        '0001-99-00',
        '0001-13-00',
        '9999-00-00',
        '9999-01-00',
        '9999-99-00',
        '9999-13-00',
        '0000-00-01',
        '0000-01-01',
        '0000-99-01',
        '0000-13-01',
        '0001-00-01',
        '0001-01-01',
        '0001-99-01',
        '0001-13-01',
        '9999-00-01',
        '9999-01-01',
        '9999-99-01',
        '9999-13-01',
        '0000-00-99',
        '0000-01-99',
        '0000-99-99',
        '0000-13-99',
        '0001-00-99',
        '0001-01-99',
        '0001-99-99',
        '0001-13-99',
        '9999-00-99',
        '9999-01-99',
        '9999-99-99',
        '9999-13-99',
    ]

    def __init__(self, group=None):
        SimpleGenerator.__init__(self, group)
        self._generator = List(None, self._strings)

    @staticmethod
    def unittest():
        g = BadDate(None)
        if g.getValue() != '1/1/1':
            raise Exception("BadDate unittest failed #1")
        g.next()
        if g.getValue() != '0/0/0':
            raise Exception("BadDate unittest failed #2")
        print("BadDate okay")


class NumberVariance(Generator):
    """
    Generate a range of numbers from (number - variance) to (number + variance).

    Example:

        >>> gen = NumberVariance(None, 10, 5)
        >>> print gen.getValue()
        5
        >>> gen.next()
        >>> gen.getValue()
        6
        >>> gen.next()
        >>> gen.getValue()
        7
        >>> gen.next()
        >>> gen.getValue()
        8
        >>> gen.next()
        >>> gen.getValue()
        9
        >>> gen.next()
        >>> gen.getValue()
        10
        >>> gen.next()
        >>> gen.getValue()
        11
        >>> gen.next()
        >>> gen.getValue()
        12
        >>> gen.next()
        >>> gen.getValue()
        13
        >>> gen.next()
        >>> gen.getValue()
        14
        >>> gen.next()
        >>> gen.getValue()
        15
    """

    def __init__(self, group, number, variance, min=None, max=None):
        """
        Min and max can be used to limit the produced numbers.

        When using a generator's value will be gotten on the first call to
        our .getRawValue/getValue methods that occur after a reset().

        @type	group: Group
        @param	group: Group to use
        @type	number: Number or Generator
        @param	number: Number to change
        @type	variance: + and - change to give range
        @param	min: Number
        @type	min: Minimum allowed number
        @param	max: Number
        @type	max: Maximum allowed number
        """

        Generator.__init__(self)
        self.setGroup(group)

        if str(type(number)) != "<type 'int'>" and str(type(number)) != "<type 'long'>":
            self._generator = number
            self._number = None
            self._isGenerator = True
        else:
            self._generator = None
            self._number = number
            self._isGenerator = False

        # Max range of values
        self._variance = int(variance)
        self._totalVariance = (self._variance * 2) + 1

        # Min and Max value to be generated
        self._minAllowed = min
        self._maxAllowed = max

        # Current index into range of values
        self._current = 0
        self._currentRange = None

        # Calculate this upfront as well to make sure
        # our iteration count is correct!
        if self._isGenerator:
            num = int(self._generator.getValue())
        else:
            num = int(self._number)

        if (num - self._variance) < (num + self._variance):
            min = num - self._variance
            max = num + self._variance
        else:
            max = num - self._variance
            min = num + self._variance

        if self._minAllowed is not None and min < self._minAllowed:
            min = self._minAllowed

        if self._maxAllowed is not None and max > self._maxAllowed:
            max = self._maxAllowed

        self._currentRange = range(min, max)

    def next(self):
        self._current += 1
        if self._current > self._totalVariance:
            raise GeneratorCompleted("NumberVariance 1")

        if self._currentRange is not None and self._current >= len(self._currentRange):
            raise GeneratorCompleted("NumberVariance 2")

    def getRawValue(self):
        # Always get the value from the generator.  In the case of
        # a BlockSize generator this can change when we are recursing

        if self._isGenerator:
            num = int(self._generator.getValue())
        else:
            num = int(self._number)

        if (num - self._variance) < (num + self._variance):
            min = num - self._variance
            max = num + self._variance
        else:
            max = num - self._variance
            min = num + self._variance

        if self._minAllowed is not None and min < self._minAllowed:
            min = self._minAllowed

        if self._maxAllowed is not None and max > self._maxAllowed:
            max = self._maxAllowed

        self._currentRange = range(min, max)

        try:
            #print "NumberVariance.getRawValue(): [%d-%d:%d:%d] Returning %d" % (min, max, self._current, len(self._currentRange), self._currentRange[self._current])
            return str(self._currentRange[self._current])
        except:
            #print "NumberVariance.getRawValue(): Returning %d" % self._currentRange[-1]
            return str(self._currentRange[-1])


    def reset(self):
        self._current = 0

    @staticmethod
    def unittest():
        gen = NumberVariance(None, 10, 5)
        for cnt in range(5, 15):
            if cnt != gen.getValue():
                raise Exception("NumberVariance broken %d != %d" % (cnt, gen.getValue()))

        print("NumberVariance OK!")


class NumbersVariance(SimpleGenerator):
    """
    Performs a L{NumberVariance} on a list of numbers.  This is a specialized
    version of L{NumberVariance} that takes an array of numbers to perform a
    variance on instead of just a single number.

    Example:

        >>> gen = NumbersVariance(None, [1,10], 1)
        >>> gen.getValue()
        0
        >>> gen.next()
        >>> gen.getValue()
        1
        >>> gen.next()
        >>> gen.getValue()
        2
        >>> gen.next()
        >>> gen.getValue()
        9
        >>> gen.next()
        >>> gen.getValue()
        10
        >>> gen.next()
        >>> gen.getValue()
        11


    @see: L{NumberVariance}

    """

    def __init__(self, group, numbers, variance):
        """
        @type	group: Group
        @param	group: Group to use
        @type	numbers: Array of numbers
        @param	numbers: Numbers to change
        @type	variance: + and - change to give range
        """

        Generator.__init__(self)
        self.setGroup(group)

        gens = []

        for n in numbers:
            gens.append(NumberVariance(None, n, variance))

        self._generator = GeneratorList(group, gens)

    @staticmethod
    def unittest():
        raise Exception("NumbersVariance needs a unittest")


class BadNumbersAsString(SimpleGenerator):
    """
    [DEPRICATED] Use L{BadNumbers} instead.

    @see: Use L{BadNumbers} instead.
    @depricated
    @undocumented
    """

    _ints = [
        0,
        -128, # signed 8
        127,
        255, # unsigned 8
        -32768, # signed 16
        32767,
        65535, # unsigned 16
        -2147483648, # signed 32
        2147483647,
        4294967295, # unisnged 32
        -9223372036854775808, # signed 64
        9223372036854775807,
        18446744073709551615, # unsigned 64
        #-170141183460469231731687303715884105728,	# signed 128
        #170141183460469231731687303715884105727,	# signed 128
        #340282366920938463463374607431768211455,	# unsigned 128
    ]

    def __init__(self, group=None, N=50):
        SimpleGenerator.__init__(self, group)
        self._generator = WithDefault(None, 10, NumbersVariance(None, self._ints, N))

    def getRawValue(self):
        try:
            val = self._generator.getValue()

        except OverflowError:
            # Wow, that sucks!
            print("BadNumbersAsString(): OverflowError spot 1!")
            return str(0)

        return str(val)


class BadNumbers8(SimpleGenerator):
    """
    Generate numbers that may trigger integer overflows for
    both signed and unsigned numbers.  Under the hood this generator
    performs a L{NumbersVariance} on the boundry numbers for:

        - int8 (0, -128, 127)
        - unsigned int8 (255)

    @see: L{BadNumbers}, L{NumbersVariance}, L{BadUnsignedNumbers}, L{BadPositiveNumbers}
    """

    _ints = [
        0,
        -128, # signed 8
        127,
        255, # unsigned 8
    ]

    def __init__(self, group=None):
        SimpleGenerator.__init__(self, group)
        self._generator = List(None, range(0, 255))

    def getRawValue(self):
        try:
            val = self._generator.getValue()

        except OverflowError:
            # Wow, that sucks!
            print("BadNumbersAsString8(): OverflowError spot 1!")
            return str(0)

        return str(val)


class BadNumbers16(SimpleGenerator):
    """
    Generate numbers that may trigger integer overflows for
    both signed and unsigned numbers.  Under the hood this generator
    performs a L{NumbersVariance} on the boundry numbers for:

        - int8 (0, -128, 127)
        - unsigned int8 (255)
        - int16 (-32768, 32767)
        - unsigned int16 (65535)

    @see: L{BadNumbers}, L{NumbersVariance}, L{BadUnsignedNumbers}, L{BadPositiveNumbers}
    """

    _ints = [
        0,
        -128, # signed 8
        127,
        255, # unsigned 8
        -32768, # signed 16
        32767,
        65535    # unsigned 16
    ]

    def __init__(self, group=None, N=50):
        SimpleGenerator.__init__(self, group)
        self._generator = WithDefault(None, 10, NumbersVariance(None, self._ints, N))

    def getRawValue(self):
        try:
            val = self._generator.getValue()

        except OverflowError:
            # Wow, that sucks!
            print("BadNumbersAsString16(): OverflowError spot 1!")
            return str(0)

        return str(val)


class BadNumbers24(SimpleGenerator):
    """
    Generate numbers that may trigger integer overflows for
    both signed and unsigned numbers.  Under the hood this generator
    performs a L{NumbersVariance} on the boundry numbers for:

        - int8 (0, -128, 127)
        - unsigned int8 (255)
        - int16 (-32768, 32767)
        - unsigned int16 (65535)
        - int24 (-8388608, 8388607 )
        - unsigned int24 (16777216)

    @see: L{BadNumbers}, L{NumbersVariance}, L{BadUnsignedNumbers}, L{BadPositiveNumbers}
    """

    _ints = [
        0,
        -128, # signed 8
        127,
        255, # unsigned 8
        -32768, # signed 16
        32767,
        65535, # unsigned 16
        -8388608,
        8388607,
        16777216 # unisnged 24
    ]

    def __init__(self, group=None, N=50):
        SimpleGenerator.__init__(self, group)
        self._generator = WithDefault(None, 10, NumbersVariance(None, self._ints, N))

    def getRawValue(self):
        try:
            val = self._generator.getValue()

        except OverflowError:
            # Wow, that sucks!
            print("BadNumbersAsString16(): OverflowError spot 1!")
            return str(0)

        return str(val)


class BadNumbers32(SimpleGenerator):
    """
    Generate numbers that may trigger integer overflows for
    both signed and unsigned numbers.  Under the hood this generator
    performs a L{NumbersVariance} on the boundry numbers for:

        - int8 (0, -128, 127)
        - unsigned int8 (255)
        - int16 (-32768, 32767)
        - unsigned int16 (65535)
        - int32 (-2147483648, 2147483647)
        - unsigned int32 (4294967295)

    @see: L{BadNumbers}, L{NumbersVariance}, L{BadUnsignedNumbers}, L{BadPositiveNumbers}
    """

    _ints = [
        0,
        -128, # signed 8
        127,
        255, # unsigned 8
        -32768, # signed 16
        32767,
        65535, # unsigned 16
        2147483647,
        4294967295, # unisnged 32
    ]

    def __init__(self, group=None, N=50):
        SimpleGenerator.__init__(self, group)
        self._generator = WithDefault(None, 10, NumbersVariance(None, self._ints, N))

    def getRawValue(self):
        try:
            val = self._generator.getValue()

        except OverflowError:
            # Wow, that sucks!
            print("BadNumbersAsString16(): OverflowError spot 1!")
            return str(0)

        return str(val)


class BadNumbers(BadNumbersAsString):
    """
    Generate numbers that may trigger integer overflows for
    both signed and unsigned numbers.  Under the hood this generator
    performs a L{NumbersVariance} on the boundry numbers for:

        - int8 (0, -128, 127)
        - unsigned int8 (255)
        - int16 (-32768, 32767)
        - unsigned int16 (65535)
        - int32 (-2147483648, 2147483647)
        - unsigned int32 (4294967295)
        - int64 (-9223372036854775808, 9223372036854775807)
        - unsigned int64 (18446744073709551615)

    @see: L{BadNumbers16}, L{NumbersVariance}, L{BadUnsignedNumbers}, L{BadPositiveNumbers}
    """
    pass


class BadPositiveNumbers(SimpleGenerator):
    """
    Generate positive numbers that may trigger integer overflows for
    both signed and unsigned numbers.  Under the hood this generator
    performs a L{NumbersVariance} on the boundry numbers for:

        - int8 (0, 127)
        - unsigned int8 (255)
        - int16 (32767)
        - unsigned int16 (65535)
        - int32 (2147483647)
        - unsigned int32 (4294967295)
        - int64 (9223372036854775807)
        - unsigned int64 (18446744073709551615)

    @see: L{BadNumbers16}, L{NumbersVariance}, L{BadUnsignedNumbers}, L{BadPositiveNumbers}
    """

    _ints = [
        50, # Don't want any negative numbers
        127,
        255, # unsigned 8
        32767,
        65535, # unsigned 16
        2147483647,
        4294967295, # unisnged 32
        9223372036854775807,
        18446744073709551615, # unsigned 64
    ]

    def __init__(self, group=None):
        SimpleGenerator.__init__(self, group)
        self._generator = WithDefault(None, 10, NumbersVariance(None, self._ints, 50))

    def getRawValue(self):
        try:
            val = self._generator.getValue()

            if val < 0:
                val = 0

        except OverflowError:
            # Wow, that sucks!
            print("BadPositiveNumbers(): OverflowError spot 1!")
            return str(0)

        return str(val)


class BadPositiveNumbersSmaller(SimpleGenerator):
    """
    Generate positive numbers that may trigger integer overflows for
    both signed and unsigned numbers.  Under the hood this generator
    performs a L{NumbersVariance} on the boundry numbers for:

        - int8 (0, 127)
        - unsigned int8 (255)
        - int16 (32767)
        - unsigned int16 (65535)
        - int32 (2147483647)
        - unsigned int32 (4294967295)
        - int64 (9223372036854775807)
        - unsigned int64 (18446744073709551615)

    @see: L{BadNumbers16}, L{NumbersVariance}, L{BadUnsignedNumbers}, L{BadPositiveNumbers}
    """

    _ints = [
        50, # Don't want any negative numbers
        127,
        255, # unsigned 8
        32767,
        65535, # unsigned 16
    ]

    def __init__(self, group=None):
        SimpleGenerator.__init__(self, group)
        self._generator = WithDefault(None, 10, NumbersVariance(None, self._ints, 50))

    def getRawValue(self):
        try:
            val = self._generator.getValue()

            if val < 0:
                val = 0

        except OverflowError:
            # Wow, that sucks!
            print("BadPositiveNumbers(): OverflowError spot 1!")
            return str(0)

        return str(val)


class BadUnsignedNumbers(SimpleGenerator):
    """
    Generate numbers that may trigger integer overflows for
    both signed and unsigned numbers.  Under the hood this generator
    performs a L{NumbersVariance} on the boundry numbers for:

        - unsigned int8  (0, 255)
        - unsigned int16 (65535)
        - unsigned int32 (4294967295)
        - unsigned int64 (18446744073709551615)

    @see: L{BadNumbers16}, L{NumbersVariance}, L{BadUnsignedNumbers}, L{BadPositiveNumbers}
    """

    _ints = [
        50,
        255,
        65535,
        4294967295,
        18446744073709551615,
    ]

    def __init__(self, group=None):
        SimpleGenerator.__init__(self, group)
        self._generator = WithDefault(None, 10, NumbersVariance(None, self._ints, 50))

    def getRawValue(self):
        try:
            val = self._generator.getValue()

            if val < 0:
                val = 0

        except OverflowError:
            # Wow, that sucks!
            print("BadUnsignedNumbers(): OverflowError spot 1!")
            return str(0)

        return str(val)


class BadUnsignedNumbers16(SimpleGenerator):
    """
    Generate numbers that may trigger integer overflows for
    both signed and unsigned numbers.  Under the hood this generator
    performs a L{NumbersVariance} on the boundry numbers for:

        - unsigned int8  (0, 255)
        - unsigned int16 (65535)

    @see: L{BadNumbers16}, L{NumbersVariance}, L{BadUnsignedNumbers}, L{BadPositiveNumbers}
    """

    _ints = [
        50,
        255,
        65535,
    ]

    def __init__(self, group=None):
        SimpleGenerator.__init__(self, group)
        self._generator = WithDefault(None, 10, NumbersVariance(None, self._ints, 50))

    def getRawValue(self):
        try:
            val = self._generator.getValue()

            if val < 0:
                val = 0

        except OverflowError:
            # Wow, that sucks!
            print("BadUnsignedNumbers(): OverflowError spot 1!")
            return str(0)

        return str(val)


class BadIpAddress(SimpleGenerator):
    """
    [BETA] Generate some bad ip addresses.  Needs work
    should also implement one for ipv6.
    """

    def __init__(self, group=None):
        SimpleGenerator.__init__(self, group)
        self._groupA = Group()
        self._groupB = Group()
        self._generator = GeneratorList(None, [
            Static('10.10.10.10'),

            GeneratorList2(None, [
                self._groupA,
                self._groupB
            ], [
                               GeneratorList(self._groupA, [
                                   List(None, [
                                       '0', '0.', '1.', '1.1', '1.1.1', '1.1.1.1.',
                                       '.1', '.1.1.1', '.1.1.1.1',
                                       '1.1.1.1\0AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA',
                                       '0.0.0.0',
                                       '127.0.0.1',
                                       '255.255.255',
                                       '0.0.0.0',
                                       '256.256.256',
                                       '-1.-1.-1.-1',
                                       'FF.FF.FF',
                                       '\0.\0.\0.\0',
                                       '\01.\01.\01.\01',
                                       '\00.\00.\00.\00',
                                       '1\0.1\0.1\0.1\0',
                                       '1\0.\01\0.\01\0.\01\0',
                                       '0\0.\00\0.\00\0.\00\0',
                                       '999.999.999'
                                   ]),

                                   Block2([
                                       BadNumbersAsString(),
                                       Static('.'),
                                       BadNumbersAsString(),
                                       Static('.'),
                                       BadNumbersAsString(),
                                       Static('.'),
                                       BadNumbersAsString()
                                   ])
                               ]),

                               Block([
                                   Repeater(self._groupB, Static('120.'), 1, 20),
                                   Static('1')
                               ]),
                           ], 'BadIpAddress-Sub'),

            Static('10.10.10.10')
        ], 'BadIpAddress')


class TopLevelDomains(SimpleGenerator):
    """
    Top-level domain names in upper case. List current as of 12/06/2006.
    Includes country's.
    """

    def __init__(self, group=None):
        SimpleGenerator.__init__(self, group)
        self._generator = List(None, [
            'com',
            'AC', 'AD', 'AE', 'AERO', 'AF', 'AG', 'AI', 'AL', 'AM', 'AN',
            'AO', 'AQ', 'AR', 'ARPA', 'AS', 'AT', 'AU', 'AW', 'AX', 'AZ',
            'BA', 'BB', 'BD', 'BE', 'BF', 'BG', 'BH', 'BI', 'BIZ', 'BJ',
            'BM', 'BN', 'BO', 'BR', 'BS', 'BT', 'BV', 'BW', 'BY', 'BZ',
            'CA', 'CAT', 'CC', 'CD', 'CF', 'CG', 'CH', 'CI', 'CK', 'CL',
            'CM', 'CN', 'CO', 'COM', 'COOP', 'CR', 'CU', 'CV', 'CX', 'CY',
            'CZ', 'DE', 'DJ', 'DK', 'DM', 'DO', 'DZ', 'EC', 'EDU', 'EE',
            'EG', 'ER', 'ES', 'ET', 'EU', 'FI', 'FJ', 'FK', 'FM', 'FO',
            'FR', 'GA', 'GB', 'GD', 'GE', 'GF', 'GG', 'GH', 'GI', 'GL',
            'GM', 'GN', 'GOV', 'GP', 'GQ', 'GR', 'GS', 'GT', 'GU', 'GW',
            'GY', 'HK', 'HM', 'HN', 'HR', 'HT', 'HU', 'ID', 'IE', 'IL',
            'IM', 'IN', 'INFO', 'INT', 'IO', 'IQ', 'IR', 'IS', 'IT', 'JE',
            'JM', 'JO', 'JOBS', 'JP', 'KE', 'KG', 'KH', 'KI', 'KM', 'KN',
            'KR', 'KW', 'KY', 'KZ', 'LA', 'LB', 'LC', 'LI', 'LK', 'LR',
            'LS', 'LT', 'LU', 'LV', 'LY', 'MA', 'MC', 'MD', 'MG', 'MH',
            'MIL', 'MK', 'ML', 'MM', 'MN', 'MO', 'MOBI', 'MP', 'MQ', 'MR',
            'MS', 'MT', 'MU', 'MUSEUM', 'MV', 'MW', 'MX', 'MY', 'MZ', 'NA',
            'NAME', 'NC', 'NE', 'NET', 'NF', 'NG', 'NI', 'NL', 'NO', 'NP',
            'NR', 'NU', 'NZ', 'OM', 'ORG', 'PA', 'PE', 'PF', 'PG', 'PH',
            'PK', 'PL', 'PM', 'PN', 'PR', 'PRO', 'PS', 'PT', 'PW', 'PY',
            'QA', 'RE', 'RO', 'RU', 'RW', 'SA', 'SB', 'SC', 'SD', 'SE',
            'SG', 'SH', 'SI', 'SJ', 'SK', 'SL', 'SM', 'SN', 'SO', 'SR',
            'ST', 'SU', 'SV', 'SY', 'SZ', 'TC', 'TD', 'TF', 'TG', 'TH',
            'TJ', 'TK', 'TL', 'TM', 'TN', 'TO', 'TP', 'TR', 'TRAVEL', 'TT',
            'TV', 'TW', 'TZ', 'UA', 'UG', 'UK', 'UM', 'US', 'UY', 'UZ',
            'VA', 'VC', 'VE', 'VG', 'VI', 'VN', 'VU', 'WF', 'WS', 'YE',
            'YT', 'YU', 'ZA', 'ZM', 'ZW'
        ])


class BadHostname(BadStrings):
    """
    [BETA] Crazy hostnames.
    """

    def __init__(self, group=None):
        SimpleGenerator.__init__(self, group)
        self._generator = GeneratorList(None, [
            Static('localhost'),
            BadStrings(),
            Repeater(None, Static('A'), 1, 1000),
            Repeater(None, Static('A'), 100, 100),
            Repeater(None, Static('A.'), 5, 100),
            Repeater(None, Static('.'), 1, 10),
            Repeater(None, Static('.'), 20, 20),
            Block2([
                Repeater(None, Static('A'), 5, 20),
                Static('.'),
                Repeater(None, Static('A'), 5, 20),
                Static('.'),
                Repeater(None, Static('A'), 5, 20)
            ]),
            Block2([
                Static('AAAA.'),
                TopLevelDomains()
            ]),
            Static('localhost')
        ])


class BadPath(BadStrings):
    """
    [BETA] Path generation fun!
    """

    def __init__(self, group=None):
        SimpleGenerator.__init__(self, group)
        self._generator = GeneratorList(None, [
            Static('A'),
            Repeater(None, Static('.'), 1, 1000),
            Repeater(None, Static('\\'), 1, 1000),
            Repeater(None, Static('/'), 1, 1000),
            Repeater(None, Static(':'), 1, 1000),
            Repeater(None, Static('../'), 1, 1000),
            Repeater(None, Static('..\\'), 1, 1000),
            Repeater(None, Static('*\\'), 10, 100),
            Repeater(None, Static('*/'), 10, 100),
            Repeater(None, Static('//\\'), 10, 100),
            Repeater(None, Static('//..\\..'), 10, 100),
            Repeater(None, Static('aaa//'), 10, 100),
            Repeater(None, Static('aaa\\'), 10, 100),
            Block2([
                BadStrings(),
                Static(':\\')
            ]),
            Block2([
                BadStrings(),
                Static(':/')
            ]),
            Block2([
                Static('\\\\'),
                BadStrings(),
            ]),
            Block2([
                Static('./'),
                BadStrings()
            ]),
            Block2([
                Static('/'),
                BadStrings(),
                Static('/')
            ]),
            Static('A')
        ])


class BadFilename(BadStrings):
    """
    Lots of bad file names.
    """

    def __init__(self, group=None):
        SimpleGenerator.__init__(self, group)
        self._generator = GeneratorList(None, [
            Static('Peach.txt'),
            BadStrings(),
            Block2([
                BadStrings(),
                Static('.'),
                BadStrings()
            ]),
            Block2([
                Static("."),
                BadStrings()
            ]),
            Block2([
                BadStrings(),
                Static('.')
            ]),
            Repeater(None, Static('.'), 1, 1000),
            Repeater(None, Static("a.a"), 1, 1000),
            Block2([
                Static("A."),
                Repeater(None, Static('A'), 1, 1000)
            ]),
            Block2([
                Repeater(None, Static('A'), 1, 1000),
                Static('.A')
            ]),
            Block2([
                Static('AAAA'),
                Repeater(None, Static('.doc'), 1, 1000)
            ]),
            Block2([
                Repeater(None, Static('A'), 10, 100),
                Static('.'),
                Repeater(None, Static('A'), 10, 100)
            ]),
            Static('Peach.txt'),
        ])


class _AsInt(SimpleGenerator):
    """
    Base class for AsIntXX functions that implements logic to skip values
    that are the same.
    """

    _last = None
    _inMe = 0

    def _getValue(self):
        return self._transformer.encode(self._generator.getValue())

    def next(self):
        """
        Our implementation of next will return skip
        values that are the same as the last value generated.

        This is done because packing larger numbers down can
        result in the same value lots of times.
        """

        self._generator.next()
        cur = self._getValue()

        while cur == self._last:
            # Skip till we have something different
            try:
                self._generator.next()
            except GeneratorCompleted:
                break

            cur = self._getValue()

        self._last = cur

    def reset(self):
        SimpleGenerator.reset(self)
        cur = None

    def getRawValue(self):
        return self._generator.getValue()


class AsInt8(_AsInt):
    """
    Cause generated value to be an 8 bit number.
    """

    def __init__(self, group, generator, isSigned=1, isLittleEndian=1):
        """
        @type	isSigned: number
        @param	isSigned: 1 for signed, 0 for unsigned
        @type	isLittleEndian: number
        @param	isLittleEndian: 1 for little, 0 for big
        """
        SimpleGenerator.__init__(self, group)
        self._generator = generator
        self.setTransformer(Peach.Transformers.Type.Integer.AsInt8(isSigned, isLittleEndian))


class AsInt16(_AsInt):
    """
    Cause generated value to be a 16 bit number
    """

    def __init__(self, group, generator, isSigned=1, isLittleEndian=1):
        """
        @type	isSigned: number
        @param	isSigned: 1 for signed, 0 for unsigned
        @type	isLittleEndian: number
        @param	isLittleEndian: 1 for little, 0 for big
        """
        SimpleGenerator.__init__(self, group)
        self._generator = generator
        self.setTransformer(Peach.Transformers.Type.Integer.AsInt16(isSigned, isLittleEndian))


class AsInt24(_AsInt):
    """
    Cause generated value to be a 24 bit number (don't ask)
    """

    def __init__(self, group, generator, isSigned=1, isLittleEndian=1):
        """
        @type	isSigned: number
        @param	isSigned: 1 for signed, 0 for unsigned (we ignore this)
        @type	isLittleEndian: number
        @param	isLittleEndian: 1 for little, 0 for big
        """
        SimpleGenerator.__init__(self, group)
        self._generator = generator
        self.setTransformer(Peach.Transformers.Type.Integer.AsInt24(isSigned, isLittleEndian))


class AsInt32(_AsInt):
    """
    Cause generated value to be a 32 bit number
    """

    def __init__(self, group, generator, isSigned=1, isLittleEndian=1):
        """
        @type	isSigned: number
        @param	isSigned: 1 for signed, 0 for unsigned
        @type	isLittleEndian: number
        @param	isLittleEndian: 1 for little, 0 for big
        """
        SimpleGenerator.__init__(self, group)
        self._generator = generator
        self.setTransformer(Peach.Transformers.Type.Integer.AsInt32(isSigned, isLittleEndian))


class AsInt64(_AsInt):
    """
    Cause generated value to be a 64 bit number
    """

    def __init__(self, group, generator, isSigned=1, isLittleEndian=1):
        """
        @type	isSigned: number
        @param	isSigned: 1 for signed, 0 for unsigned
        @type	isLittleEndian: number
        @param	isLittleEndian: 1 for little, 0 for big
        """
        SimpleGenerator.__init__(self, group)
        self._generator = generator
        self.setTransformer(Peach.Transformers.Type.Integer.AsInt64(isSigned, isLittleEndian))


class WithDefault(SimpleGenerator):
    """
    Wrapps a Generator and makes the first and last value be a default value.
    """

    def __init__(self, group, default, generator):
        """
        @type	default: Python primitive or Generator
        @param	default: Default value
        @type	generator: Generator
        @param	generator: Generator to wrap
        """
        SimpleGenerator.__init__(self, group)
        # If the user passed us a generator as our default value, get the
        # first value out of it and use it.
        if str(type(default)) == "<type 'instance'>" and hasattr(default, "getValue"):
            self._default = default
        else:
            self._default = Static(str(default))

        self._generator = GeneratorList(None, [
            self._default,
            generator,
            self._default,
        ])

    def setDefaultValeu(self, data):
        """
        Set the default value, assumes we have a static or
        some other generator that exposes a "setValue()" method
        """
        self._default.setValue(data)


class BadDerEncodedOctetString(Generator):
    """
    Performs DER encoding of an octet string with incorrect lengths.
    """

    def __init__(self, group, generator):
        """
        @type	group: Group
        @param	group: Group
        @type	generator: Generator
        @param	generator: Generator that produces strings that will have bad
        DER encodings done on 'em
        """

        Generator.__init__(self)
        self.setGroup(group)
        self._generator = generator
        self._setupNextValue()

    def _setupNextValue(self):
        self._string = self._generator.getValue()
        self._variance = GeneratorList(None, [
            Static(len(self._string)),
            NumberVariance(None, len(self._string), 20, 0),
            Static(len(self._string)),
        ])

    def next(self):
        try:
            self._variance.next()
        except GeneratorCompleted:
            self._generator.next()
            self._setupNextValue()

    def reset(self):
        self._variance.reset()

    def getRawValue(self):
        val = '\x04'
        length = self._variance.getValue()
        if length < 255:
            val += struct.pack("B", length)
        elif length < 65535:
            val += '\x82'
            val += struct.pack("H", length)
        elif length < 4294967295:
            val += '\x83'
            val += struct.pack("I", length)
        elif length < 18446744073709551615:
            val += '\x84'
            val += struct.pack("L", length)
        else:
            raise Exception("Length way to big for us %d" % length)
        return val + self._string


class BadBerEncodedOctetString(BadDerEncodedOctetString):
    """
    Performs BER encoding of an octect string with incorrect lengths.
    """
    pass

##
### Random strings
##_randStrings = []
##for i in range(100):
##    s = u''
##    for x in range(random.choice(range(10, 100))):
##        s += random.choice(BadStrings._stringChars)
##    
##    _randStrings.append(s)
##
##_generator = GeneratorList(None, [
##    List(None, BadStrings._strings),
##    List(None, _randStrings),
##    Repeater(None, Static(u"A"), 10, 200),
##    Repeater(None, Static(u"A"), 127, 100),
##    Repeater(None, Static(u"A"), 1024, 10),
##    Repeater(None, Static(u"\x41\0"), 10, 200),
##    Repeater(None, Static(u"\x41\0"), 127, 100),
##    Repeater(None, Static(u"\x41\0"), 1024, 10),
##    
##    Block2([
##        Static(u'\0\0'),
##        Static(u'A'*7000)
##        ]),
##    
##    Block2([
##        Static(u'%00%00'),
##        Static(u'A'*7000)
##        ]),
##    
##    BadNumbers(),
##    ])
##
##print "\tbadStrings = ["
##
##try:
##	while True:
##		s = _generator.getValue()
##		print "\t\t%s," % repr(unicode(s))
##		_generator.next()
##except:
##    pass
##
##print "\t\t]"
