# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
import sys

from Peach import generator


class PrintStdout(generator.Generator):
    """
    Logical value of empty string, but will display a value to stdout when
    called. Useful for displaying status messages.
    """

    _msg = None
    _generator = None

    def __init__(self, msg, generator=None):
        """
        @type	msg: string
        @param	msg: Value to output
        @type	generator: Generator
        @param	generator: Generator to wrap
        """
        self._msg = msg
        self._generator = generator

    def getRawValue(self):
        print(self._msg)
        if self._generator:
            return self._generator.getRawValue()
        return ""

    def next(self):
        if self._generator:
            self._generator.next()
        else:
            raise generator.GeneratorCompleted("PrintStdout")


class PrintStderr(generator.Generator):
    """
    Logical value of empty string, but will display a value to stderr when
    called. Useful for displaying status messages.
    """

    _msg = None
    _generator = None

    def __init__(self, msg, generator=None):
        """
        @type	msg: string
        @param	msg: Value to output
        @type	generator: Generator
        @param	generator: Generator to wrap
        """
        self._msg = msg
        self._generator = generator

    def getRawValue(self):
        sys.stderr.write(self._msg + "\n")
        if self._generator:
            return self._generator.getRawValue()
        return ""

    def next(self):
        if self._generator:
            self._generator.next()
        else:
            raise generator.GeneratorCompleted("PrintStderr")
