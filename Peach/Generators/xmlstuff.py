# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
import os
import re
import sys
import struct
from Peach.generator import Generator
from Peach.Generators.dictionary import *
from Peach.Generators.static import *
import Peach.Generators.static


class XmlCreateElements(Generator):
    """
    This generator create XML elements N deep
    """

    _startingDepth = 1
    _increment = 1
    _nodePrefix = Static('PeachFuzz')
    _nodePostfix = None
    _elementAttributs = None
    _currentDepth = 1
    _maxDepth = 1000

    def __init__(self, group, startingDepth=None, increment=None,
                 maxDepth=None, nodePrefix=None, nodePostfix=None,
                 elementAttributes=None):
        """
        @type	group: Group
        @param	group: Group to use
        @type	startingDepth: integer
        @param	startingDepth: How many deep to start at, default 1
        @type	increment: integer
        @param	increment: Incrementor, default 1
        @type	maxDepth: integer
        @param	maxDepth: Max depth, default 1000
        @type	nodePrefix: Generator
        @param	nodePrefix: Node prefix, default is Static('PeachFuzz')
        @type	nodePostfix: Generator
        @param	nodePostfix: Node postfix, default is None
        @type	elementAttributes: Generator
        @param	elementAttributes: Element attributes, default is None
        """
        self.setGroup(group)
        if startingDepth is not None:
            self._startingDepth = startingDepth
        if increment is not None:
            self._increment = increment
        if nodePrefix is not None:
            self._nodePrefix = nodePrefix
        if nodePostfix is not None:
            self._nodePostfix = nodePostfix
        if elementAttributes is not None:
            self._elementAttributes = elementAttributes
        if maxDepth is not None:
            self._maxDepth = maxDepth

    def next(self):
        self._currentDepth += self._increment
        if self._currentDepth > self._maxDepth:
            raise generator.GeneratorCompleted("XmlCreateNodes")

    def getRawValue(self):
        ret = ''

        postFixs = []
        for i in range(self._currentDepth):
            if self._nodePostfix is not None:
                postFixs[i] = self._nodePostfix.getValue()
                if self._elementAttributes is not None:
                    ret += "<%s%s %s>" % (self._nodePrefix.getValue(), postFixs[i],
                                          self._elementAttributes.getValue())
                else:
                    ret += "<%s%s>" % (self._nodePrefix.getValue(), postFixs[i])
            else:
                if self._elementAttributes is not None:
                    ret += "<%s %s>" % (self._nodePrefix.getValue(),
                                        self._elementAttributes.getValue())
                else:
                    ret += "<%s>" % self._nodePrefix.getValue()

        for j in range(self._currentDepth):
            if self._nodePostfix is not None:
                ret += "</%s%s>" % (self._nodePrefix.getValue(), postFixs[i - j])
            else:
                ret += "</%s>" % self._nodePrefix.getValue()

        return ret

    def reset(self):
        self._currentDepth = 1

    @staticmethod
    def unittest():
        expected = '<PeachFuzz1><PeachFuzz2><PeachFuzz3></PeachFuzz3></PeachFuzz2></PeachFuzz1>'
        g = XmlCreateNodes(1, 1)
        g.next()
        g.next()
        g.next()
        if g.getRawValue() != expected:
            print("FAILURE!!! XmlCreateNodes")


class XmlCreateNodes(Generator):
    """
    This generator create XML nodes N deep
    """

    _startingDepth = 1
    _increment = 1
    _nodePrefix = Static('PeachFuzz')
    _currentDepth = 1
    _maxDepth = 1000

    def __init__(self, group, startingDepth, increment, maxDepth, nodePrefix):
        """
        @type	group: Group
        @param	group: Group to use
        @type	startingDepth: integer
        @param	startingDepth: How many deep to start at, default 1
        @type	increment: integer
        @param	increment: Incrementor, default 1
        @type	maxDepth: integer
        @param	maxDepth: Max depth, default 1000
        @type	nodePrefix: Generator
        @param	nodePrefix: Node prefix, default is Static('PeachFuzz')
        """
        self.setGroup(group)
        if startingDepth is not None:
            self._startingDepth = startingDepth
        if increment is not None:
            self._increment = increment
        if nodePrefix is not None:
            self._nodePrefix = nodePrefix
        if maxDepth is not None:
            self._maxDepth = maxDepth

    def next(self):
        self._currentDepth += self._increment
        if self._currentDepth > self._maxDepth:
            raise generator.GeneratorCompleted("XmlCreateNodes")

    def getRawValue(self):
        ret = ''

        for i in range(self._currentDepth):
            ret += "<%s%d>" % (self._nodePrefix.getValue(), i)

        for j in range(self._currentDepth):
            ret += "</%s%d>" % (self._nodePrefix.getValue(), i - j)

        return ret

    def reset(self):
        self._currentDepth = 1

    @staticmethod
    def unittest():
        expected = '<PeachFuzz1><PeachFuzz2><PeachFuzz3></PeachFuzz3></PeachFuzz2></PeachFuzz1>'
        g = XmlCreateNodes(1, 1)
        g.next()
        g.next()
        g.next()
        if g.getRawValue() != expected:
            print("FAILURE!!! XmlCreateNodes")


class XmlParserTests(Generator):
    """
    W3C XML Validation Tests.  This includes
    all sets of tests, invalid, non-well formed, valid and error.

    NOTE: Test files are in samples/xmltests.zip these are the
    latest test cases from W3C as of 02/23/06 for XML.
    """

    def __init__(self, group, testFiles=None):
        """
        @type	group: Group
        @param	group: Group this Generator belongs to
        @type	testFiles: string
        @param	testFiles: Location of test files
        """
        Generator.__init__(self)

        p = None
        if not (hasattr(sys, "frozen") and sys.frozen == "console_exe"):
            p = Peach.Generators.static.__file__[:-10]
        else:
            p = os.path.dirname(os.path.abspath(sys.executable))

        testFiles = os.path.join(p, "xmltests")

        self._generatorList = GeneratorList(group,
                                            [XmlParserTestsInvalid(None, testFiles),
                                             XmlParserTestsNotWellFormed(None, testFiles),
                                             XmlParserTestsValid(None, testFiles)])

    def getRawValue(self):
        return self._generatorList.getRawValue()

    def next(self):
        self._generatorList.next()


class XmlParserTestsGeneric(Generator):
    """
    Base class
    """

    def __init__(self, group, testsFolder, testsFile):
        """
        @type	group: Group
        @param	group: Group this Generator belongs to
        @type	testsFolder: string
        @param	testsFolder: Location of test files
        @type	testsFile: string
        @param	testsFile: File with listing of test files
        """
        Generator.__init__(self)

        self._testsFolder = 'xmltests'
        self._testsFile = 'invalid.txt'
        self._currentValue = None
        self._currentTestNum = 1
        self._currentFilename = None
        self._fdTests = None
        self._fd = None

        self.setGroup(group)
        if testsFile is not None:
            self._testsFile = testsFile
        if testsFolder is not None:
            self._testsFolder = testsFolder


    def next(self):

        if self._fdTests is None:
            fileName = os.path.join(self._testsFolder, self._testsFile)
            self._fdTests = open(fileName, 'rb')

        self._currentFilename = os.path.join(self._testsFolder,
                                             self._fdTests.readline())

        self._currentFilename = self._currentFilename.strip("\r\n")
        if len(self._currentFilename) <= len(self._testsFolder) + 2:
            raise generator.GeneratorCompleted(
                "Peach.Generators.xml.XmlParserTestsInvalid")

        if self._fd is None:
            self._fd = open(self._currentFilename, 'rb')
            if self._fd is None:
                raise Exception('Unable to open', self._currentFilename)

        self._currentValue = self._fd.read()
        self._fd = None

    def getRawValue(self):
        if self._currentValue is None:
            self.next()

        return self._currentValue

    def reset(self):
        self._fd = None
        self._fdTests = None
        self._currentValue = None

    @staticmethod
    def unittest():
        pass


class XmlParserTestsInvalid(XmlParserTestsGeneric):
    """
    W3C XML Validation Tests, invalid set only.

    NOTE: Test files are in samples/xmltests.zip these are the
    latest test cases from W3C as of 02/23/06 for XML.
    """

    def __init__(self, group, testsFolder):
        """
        @type	group: Group
        @param	group: Group this Generator belongs to
        @type	testsFolder: string
        @param	testsFolder: Location of test files
        """
        XmlParserTestsGeneric.__init__(self, group, testsFolder, None)
        self.setGroup(group)
        self._testsFile = 'invalid.txt'
        if testsFolder is not None:
            self._testsFolder = testsFolder


class XmlParserTestsValid(XmlParserTestsGeneric):
    """
    W3C XML Validation Tests, valid set only.

    NOTE: Test files are in samples/xmltests.zip these are the
    latest test cases from W3C as of 02/23/06 for XML.
    """

    def __init__(self, group, testsFolder):
        """
        @type	group: Group
        @param	group: Group this Generator belongs to
        @type	testsFolder: string
        @param	testsFolder: Location of test files
        """
        XmlParserTestsGeneric.__init__(self, group, testsFolder, None)
        self.setGroup(group)
        self._testsFile = 'valid.txt'
        if testsFolder is not None:
            self._testsFolder = testsFolder


class XmlParserTestsError(XmlParserTestsGeneric):
    """
    W3C XML Validation Tests, error set only.

    NOTE: Test files are in samples/xmltests.zip these are the
    latest test cases from W3C as of 02/23/06 for XML.
    """

    def __init__(self, group, testsFolder):
        """
        @type	group: Group
        @param	group: Group this Generator belongs to
        @type	testsFolder: string
        @param	testsFolder: Location of test files
        """
        XmlParserTestsGeneric.__init__(self, group, testsFolder, None)
        self.setGroup(group)
        self._testsFile = 'error.txt'
        if testsFolder is not None:
            self._testsFolder = testsFolder


class XmlParserTestsNotWellFormed(XmlParserTestsGeneric):
    """
    W3C XML Validation Tests, Invalid set only.

    NOTE: Test files are in samples/xmltests.zip these are the
    latest test cases from W3C as of 02/23/06 for XML.
    """

    def __init__(self, group, testsFolder):
        """
        @type	group: Group
        @param	group: Group this Generator belongs to
        @type	testsFolder: string
        @param	testsFolder: Location of test files
        """
        XmlParserTestsGeneric.__init__(self, group, testsFolder, None)
        self.setGroup(group)
        self._testsFile = 'nonwf.txt'
        if testsFolder is not None:
            self._testsFolder = testsFolder
