# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from Peach.Engine.dom import *
from Peach.Engine.common import *
from Peach.analyzer import Analyzer


class _Node(object):
    def __init__(self, type, startPos, endPos, value):
        self.type = type
        self.value = value
        self.startPos = startPos
        self.endPos = endPos


class Binary(Analyzer):
    """
    Analyzes binary blobs to build data models

     1. Locate strings, char & wchar
       a. Analyze string for XML
       b. UTF8/UTF16 and byte order marks
     2. Find string lengths (relations!) --> Would also give us endian
     3. Compressed segments (zip, gzip)
    """

    supportParser = False
    supportDataElement = True
    supportCommandLine = False
    supportTopLevel = True

    def locateStrings(self, data):
        maxLooseStrings = 200
        strs = []
        cnt = 0
        for match in re.finditer(r"[\n\r\ta-zA-Z0-9,./<>\?;':\"\[\]\\\{\}|=\-+_\)\(*&^%$#@!~`]{4,}\0?", data):
            strs.append(_Node('str', match.start(), match.end(), match.group(0)))
            cnt += 1
            if cnt > maxLooseStrings:
                break
        if cnt < maxLooseStrings:
            return strs
        strs = []
        cnt = 0
        for match in re.finditer(r"[a-zA-Z0-9,./\?;':\"\\\-_&%$@!]{5,}\0?", data):
            strs.append(_Node('str', match.start(), match.end(), match.group(0)))
            cnt += 1
            if cnt > maxLooseStrings:
                break
        if cnt < maxLooseStrings:
            return strs
        strs = []
        cnt = 0
        for match in re.finditer(r"[a-zA-Z0-9,.?:\"&@!]{5,}\0?", data):
            strs.append(_Node('str', match.start(), match.end(), match.group(0)))
            cnt += 1
            if cnt > maxLooseStrings:
                break
        if cnt < maxLooseStrings:
            return strs
        strs = []
        cnt = 0
        for match in re.finditer(r"[a-zA-Z0-9.\"]{6,}\0?", data):
            strs.append(_Node('str', match.start(), match.end(), match.group(0)))
            cnt += 1
            if cnt > maxLooseStrings:
                break
        if cnt < maxLooseStrings:
            return strs
        strs = []
        cnt = 0
        for match in re.finditer(r"[a-zA-Z0-9.\"]{10,}\0?", data):
            strs.append(_Node('str', match.start(), match.end(), match.group(0)))
            cnt += 1
            if cnt > maxLooseStrings:
                break
        if cnt < maxLooseStrings:
            return strs
        return []

    def locateStringLengths(self, strs, data):
        lengths = {}
        for s in strs:
            (lengthL16, lengthL32, lengthB16, lengthB32) = 0, 0, 0, 0
            length = len(s.value)
            try:
                lengthL16 = struct.pack("H", length)
                lengthB16 = struct.pack("!H", length)
            except:
                pass
            lengthL32 = struct.pack("I", length)
            lengthB32 = struct.pack("!I", length)
            first2 = data[s.startPos - 2:s.startPos]
            first4 = data[s.startPos - 4:s.startPos]
            # Always check larger # first in case 0x00AA :)
            if first4 == lengthL32:
                obj = _Node('len', s.startPos - 4, s.startPos, length)
                obj.endian = 'little'
                obj.lengthOf = s
                obj.size = 32
                lengths[s] = obj
            elif first4 == lengthB32:
                obj = _Node('len', s.startPos - 4, s.startPos, length)
                obj.endian = 'big'
                obj.lengthOf = s
                obj.size = 32
                lengths[s] = obj
            elif first2 == lengthL16:
                obj = _Node('len', s.startPos - 2, s.startPos, length)
                obj.endian = 'little'
                obj.lengthOf = s
                obj.size = 16
                lengths[s] = obj
            elif first2 == lengthB16:
                obj = _Node('len', s.startPos - 2, s.startPos, length)
                obj.endian = 'big'
                obj.lengthOf = s
                obj.size = 16
                lengths[s] = obj
        return lengths

    def locateCompressedSegments(self, data):
        pass

    def analyzeBlob(self, data):
        """
        Will analyze a binary blob and return a Block data element containing the split up blob.
        """
        # 1. First we locate strings
        strs = self.locateStrings(data)
        # 2. Now we check for lengths
        lengths = self.locateStringLengths(strs, data)
        # 3. Now we need to build up our DataElement DOM
        root = Block(None, None)
        pos = 0
        for s in strs:
            # Check and see if we need a Blob starter
            startPos = s.startPos
            if s in lengths:
                startPos = lengths[s].startPos
            if startPos > pos:
                # Need a Blob filler
                b = Blob(None, None)
                b.defaultValue = data[pos:startPos]
                root.append(b)
            # Now handle what about length?
            stringNode = String(None, None)
            numberNode = None
            if s in lengths:
                l = lengths[s]
                numberNode = Number(None, None)
                numberNode.size = l.size
                numberNode.endian = l.endian
                numberNode.defaultValue = str(l.value)
                root.append(numberNode)
                relation = Relation(None, None)
                relation.type = "size"
                relation.of = stringNode.name
                numberNode.relations.append(relation)
                relation = Relation(None, None)
                relation.type = "size"
                relation.From = numberNode.name
                stringNode.relations.append(relation)
            if s.value[-1] == "\0":
                stringNode.defaultValue = s.value[:-1]
                stringNode.nullTerminated = True
            else:
                stringNode.defaultValue = s.value
            root.append(stringNode)
            pos = s.endPos

        # Finally, we should see if we need a trailing blob...
        if pos < (len(data) - 1):
            b = Blob(None, None)
            b.defaultValue = data[pos:]
            root.append(b)
        return root

    def asDataElement(self, parent, args, dataBuffer):
        """
        Called when Analyzer is used in a data model.
        Should return a DataElement such as Block, Number or String.
        """
        dom = self.analyzeBlob(dataBuffer)
        # Replace parent with new dom
        parentOfParent = parent.parent
        dom.name = parent.name
        indx = parentOfParent.index(parent)
        del parentOfParent[parent.name]
        parentOfParent.insert(indx, dom)

    def asCommandLine(self, args):
        """
        Called when Analyzer is used from command line.
        Analyzer should produce Peach PIT XML as output.
        """
        raise Exception("asCommandLine not supported")

    def asTopLevel(self, peach, args):
        """
        Called when Analyzer is used from top level.
        From the top level producing zero or more data models and state models is possible.
        """
        raise Exception("asTopLevel not supported")


if __name__ == "__main__":

    from lxml import etree

    data = None
    with open("sample.bin", "rb+") as fo:
        data = fo.read()
    dom = Binary().analyzeBlob(data)
    data2 = dom.getValue()

    if data2 == data:
        print("THEY MATCH")
    else:
        print(repr(data2))
        print(repr(data))

    dom.toXmlDom(etree.XML("<Peach/>", {})).write(sys.stdout, pretty_print=True)
