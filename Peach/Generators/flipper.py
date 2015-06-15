# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
import random
import struct
from Peach.generator import *


class SequentialFlipper(SimpleGenerator):
    """
    Sequentially flips bits in a data blob. This is for "random" fuzzing.
    Useful brute forcing, codecs, etc.
    """

    _data = None
    _position = 0

    def __init__(self, group, data):
        """
        @type	data: string
        @param	data: Binary static blob to flip
        """
        SimpleGenerator.__init__(self, group)
        self._data = str(data)  # Could be a unicode string.
        self._len = len(data)
        self._position = 0
        self._bit = 0

    def next(self):
        if self._bit == 7:
            self._position += 1
            self._bit = 0
            if self._position >= self._len:
                self._position -= 1
                self._bit = 7
                raise GeneratorCompleted("all done here")
        else:
            self._bit += 1

    def reset(self):
        self._bit = 0
        self._position = 0

    def getRawValue(self):
        if self._position >= self._len:
            return ""
        data = self._data
        byte = struct.unpack('B', data[self._position])[0]
        mask = 1 << self._bit
        if (byte & mask) >> self._bit == 1:
            mask = 0
            for i in range(8 - self._bit):
                mask |= 1 << i
            mask <<= 1
            if self._bit > 1:
                mask <<= self._bit
                for i in range(self._bit):
                    mask |= 1 << i
            byte &= mask
        else:
            byte |= mask
        packedup = struct.pack("B", byte)
        data = data[:self._position] + packedup + data[self._position + 1:]
        return data


class PartialFlipper(SimpleGenerator):
    """
    Performs flips of 20% of bits in data.
    """

    _data = None
    _position = 0

    def __init__(self, group, data, maxRounds=None):
        """
        @type	data: string
        @param	data: Binary static blob to flip
        @type	maxRounds: int
        @param	maxRounds: optional, override 0.2% with a fixed number
        """
        SimpleGenerator.__init__(self, group)

        self._data = str(data)    # Could be a unicode string.
        self._len = len(data)
        self._position = 0
        self._bit = 0
        self._maxRounds = int((len(data) * 8) * 0.20)
        self._round = 0

        if maxRounds is not None:
            self._maxRounds = maxRounds

    def next(self):
        self._round += 1
        # Exit if we are completed with rounds, or have no data
        # to flip
        if self._round > self._maxRounds or (len(self._data) - 1) < 1:
            raise GeneratorCompleted("all done here")
        self._position = random.randint(0, len(self._data) - 1)
        self._bit = random.randint(0, 7)

    def reset(self):
        self._bit = 0
        self._position = 0
        self._round = 0

    def getRawValue(self):
        if self._position >= self._len:
            return ""
        data = self._data
        byte = struct.unpack('B', data[self._position])[0]
        mask = 1 << self._bit
        if (byte & mask) >> self._bit == 1:
            mask = 0
            for i in range(8 - self._bit):
                mask |= 1 << i
            mask <<= 1
            if self._bit > 1:
                mask <<= self._bit
                for i in range(self._bit):
                    mask |= 1 << i
            byte &= mask
        else:
            byte |= mask
        packedup = struct.pack("B", byte)
        data = data[:self._position] + packedup + data[self._position + 1:]
        return data
