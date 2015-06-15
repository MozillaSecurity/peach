# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
import re
import struct

from Peach import generator
from Peach.generator import *


class Static(generator.Generator):
    """
    Contains a static value that never changes.
    Value can be any form of static data.

    Example:

        >>> gen = Static('Hello world')
        >>> print gen.getValue()
        Hello world

    @see: L{StaticBinary}

    """

    _value = ''

    def __init__(self, value):
        """
        @type	value: string
        @param	value: Static data
        """
        Generator.__init__(self)
        self.setValue(value)

    def getRawValue(self):
        return self._value

    def setValue(self, value):
        """
        Set static value to return.

        @type	value: string
        @param	value: Static data
        @rtype: Static
        @return: self
        """
        self._value = str(value)
        return self

    def next(self):
        raise generator.GeneratorCompleted("STATIC")


class _StaticFromTemplate(Static):
    """
    This Static is for use with Peach 2.0.  The value
    will be gotten from the Template object every time
    """

    def __init__(self, action, node):
        """
        @type	action: Action instance
        @param	action: Action that contains data model
        @type	node: DataElement
        @param	node: Data element to get value from
        """
        Static.__init__(self, None)
        self.action = action
        self.elementName = node.getFullnameInDataModel()

    def getRawValue(self):
        """
        Get the "raw" value which will then get run threw any transformers
        associated with this Generator.

        However, since we are getting the value of a DataElement we don't
        want to get the internal value, we want the actual value.
        """
        node = self.action.template.findDataElementByName(self.elementName)
        return node.getValue()


class _StaticAlwaysNone(Static):
    def __init__(self):
        Static.__init__(self, None)

    def getRawValue(self):
        """
        Get the "raw" value which will then get run threw any transformers
        associated with this Generator.

        However, since we are getting the value of a DataElement we don't
        want to get the internal value, we want the actual value.
        """
        return None


class _StaticCurrentValueFromDom(Static):
    """
    This Static is for use with Peach 2.0.  The value
    will be gotten from the Template object every time
    """

    def __init__(self, obj):
        """
        @type	value: string
        @param	value: String of hex values
        """
        Static.__init__(self, None)
        self.template = obj

    def getRawValue(self):
        return self.template.currentValue


class StaticBinary(Static):
    """
    Contains some binary data.  Can be set by string containing
    several formats of binary data such as " FF FF FF FF " or
    "\xFF \xFF \xFF", etc.

    Example:

        >>> gen = StaticBinary(41414141414141)
        >>>
        >>> print gen.getValue()
        AAAAAAAAA

    """

    # Ordering of regex's can be important as the last
    # regex can falsly match some of its priors.
    _regsHex = (
    re.compile(r"^(\s*\\x([a-zA-Z0-9]{2})\s*)"),
    re.compile(r"^(\s*%([a-zA-Z0-9]{2})\s*)"),
    re.compile(r"^(\s*0x([a-zA-Z0-9]{2})\s*)"),
    re.compile(r"^(\s*x([a-zA-Z0-9]{2})\s*)"),
    re.compile(r"^(\s*([a-zA-Z0-9]{2})\s*)")
    )

    def __init__(self, value):
        """
        @type	value: string
        @param	value: String of hex values
        """
        Static.__init__(self, value)
        self.setValue(value)

    def setValue(self, value):
        """
        Set binary data to be used.

        @type	value: string
        @param	value: String of hex values
        """
        ret = ''

        for i in range(len(self._regsHex)):
            match = self._regsHex[i].search(value)
            if match is not None:
                while match is not None:
                    ret += chr(int(match.group(2), 16))
                    value = self._regsHex[i].sub('', value)
                    match = self._regsHex[i].search(value)
                break

        self._value = ret

    @staticmethod
    def unittest():
        s = StaticBinary('41 41 41 41')
        if s.getValue() != 'AAAA':
            raise Exception('StaticBinary::unittest(): getValue 1 failed')
        s = StaticBinary('0x41 0x41 0x41 0x41')
        if s.getValue() != 'AAAA':
            raise Exception('StaticBinary::unittest(): getValue 2 failed')
        s = StaticBinary('''41 41 41 41''')
        if s.getValue() != 'AAAA':
            raise Exception('StaticBinary::unittest(): getValue 3 failed')
        s = StaticBinary('\\x41 \\x41 \\x41 \\x41')
        if s.getValue() != 'AAAA':
            raise Exception('StaticBinary::unittest(): getValue 2 failed [%s]'
                            % s.getValue())


class _Number(Static):
    """
    Base class for static numerical generators
    """

    _value = None
    _isLittleEndian = None
    _isSigned = None

    def __init__(self, value, isSigned=1, isLittleEndian=1):
        """
        @type	value: number
        @param	value: Value to set
        @type	isSigned: number
        @param	isSigned: 1 for signed, 0 for unsigned
        @type	isLittleEndian: number
        @param	isLittleEndian: 1 for signed, 0 for unsigned
        """

        Generator.__init__(self)
        if isinstance(value, (int, float, long, complex)):
            self._value = value
        else:
            # if value has a null in it '123\0' we error
            # so lets try and remove nulls from the string
            if isinstance(value, basestring):
                value = value.replace("\0", "")

            self._value = int(value)

        self._isSigned = isSigned
        self._isLittleEndian = isLittleEndian

    def setValue(self, value):
        """
        Set value.

        @type	value: number
        @param	value: Value to set
        """
        self._value = value

    def isSigned(self):
        """
        Check if value should be signed.

        @rtype: number
        @return: 1 for signed, 0 unsigned
        """
        return self._isSigned

    def setSigned(self, isSigned):
        """Set sign of number.

        @type	isSigned: number
        @param	isSigned: 1 is signed, 0 is unsigned.
        """
        self._isSigned = isSigned

    def isLittleEndian(self):
        """
        Get byte ordering.

        @rtype: number
        @return: 1 is little, 0 is big/network.
        """
        return self._isLittleEndian

    def setLittleEndian(self, isLittleEndian):
        """
        Set byte ordering.  Network byte order is
        big endian (false).

        @type	isLittleEndian: number
        @param	isLittleEndian: 1 is little, 0 is big
        """
        self._isLittleEndian = isLittleEndian

    @staticmethod
    def unittest():
        pass


class Int8(_Number):
    """
    Static 8 bit integer.  Can toggle signed/unsigned and also little/big
    endian.  Network byte order is big endian.
    """

    def getRawValue(self):

        packStr = ''

        if self.isLittleEndian() == 1:
            packStr = '<'
        else:
            packStr = '>'

        if self.isSigned() == 1:
            packStr += 'b'
        else:
            packStr += 'B'

        return struct.pack(packStr, self._value)

    @staticmethod
    def unittest():
        s = Int8(255)
        print(s.getValue())


class Int16(_Number):
    """
    Static 16 bit integer.  Can toggle signed/unsigned and also little/big
    endian.  Network byte order is big endian.
    """

    def getRawValue(self):
        packStr = ''

        if self.isLittleEndian() == 1:
            packStr = '<'
        else:
            packStr = '>'

        if self.isSigned() == 1:
            packStr += 'h'
        else:
            packStr += 'H'

        return struct.pack(packStr, self._value)

    @staticmethod
    def unittest():
        s = Int16(2555)
        print(s.getValue())


class Int32(_Number):
    """
    Static 32 bit integer.  Can toggle signed/unsigned and also little/big
    endian.  Network byte order is big endian.
    """

    def getRawValue(self):
        packStr = ''

        if self.isLittleEndian() == 1:
            packStr = '<'
        else:
            packStr = '>'

        if self.isSigned() == 1:
            packStr += 'l'
        else:
            packStr += 'L'

        return struct.pack(packStr, self._value)

    @staticmethod
    def unittest():
        s = Int32(2555555)
        print(s.getValue())


class Int64(_Number):
    """
    Static 64 bit integer.  Can toggle signed/unsigned and also little/big
    endian.  Network byte order is big endian.
    """

    def getRawValue(self):

        packStr = ''

        if self.isLittleEndian() == 1:
            packStr = '<'
        else:
            packStr = '>'

        if self.isSigned() == 1:
            packStr += 'q'
        else:
            packStr += 'Q'

        return struct.pack(packStr, self._value)


class Float(_Number):
    """
    Static 4 bit floating point number.  Can toggle little/big endian.
    Network byte order is big endian.
    """

    def getRawValue(self):

        packStr = ''

        if self.isLittleEndian() == 1:
            packStr = '<'
        else:
            packStr = '>'

        packStr += 'f'

        return struct.pack(packStr, self._value)

    @staticmethod
    def unittest():
        s = Float(1.2251)
        print(s.getValue())


class Double(_Number):
    """
    Static 8 bit floating point number.  Can toggle little/big endian.
    Network byte order is big endian.
    """

    def getRawValue(self):

        packStr = ''

        if self.isLittleEndian() == 1:
            packStr = '<'
        else:
            packStr = '>'

        packStr += 'd'

        return struct.pack(packStr, self._value)

    @staticmethod
    def unittest():
        s = Double(1.23456789)
        print(s.getValue())
