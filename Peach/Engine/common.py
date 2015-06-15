# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
import os
import sys
import types
import traceback


def split_ns(text):
    """
    Splits an ElementTree style namespace out 

    input: {namespace}element
    output: (namespace, element)

    input: element
    output: (None, element)
    """
    if text.startswith("{"):
        return text[1:].split("}", 1)
    else:
        return None, text

class Holder(object):
    """
    Holds static stuff
    """
    globals = None
    locals = None


class SoftException(Exception):
    """
    Soft exceptions should end the current test iteration, but not the run.
    They are "recoverable" or "try again" errors.
    """
    pass


class HardException(Exception):
    """
    Hard exceptions are non-recoverable and should end the fuzzing run.
    """
    pass


class RedoTestException(SoftException):
    """
    Indicate we should re-run the current test. A recoverable error occurred.
    The main engine loop should only retry the test case 3 times before turning this into a hard exception.
    """
    pass


class PeachException(HardException):
    """
    Peach exceptions are specialized hard exceptions.
    The message contained in a PeachException is presentable to the user w/o any stack trace, etc.
    Examples would be:
        "Error: The DataModel element requires a name attribute."
    """
    def __init__(self, msg, module="Unknown"):
        Exception.__init__(self, msg)
        self.module = module
        self.msg = msg


def peachEval(code, environment=False):
    """
    Eval using the Peach namespace stuffs.
    """
    return eval(code, Holder.globals, Holder.locals)


def GetClassesInModule(module):
    """
    Return array of class names in module.
    """
    classes = []
    for item in dir(module):
        i = getattr(module, item)
        if type(i) == types.ClassType and item[0] != '_':
            classes.append(item)
        elif type(i) == types.MethodType and item[0] != '_':
            classes.append(item)
        elif type(i) == types.FunctionType and item[0] != '_':
            classes.append(item)
    return classes


def buildImports(node, g, l):
    root = node.getRoot()
    for child in root:
        if child.elementType == 'import':
            # Import module
            importStr = child.importStr
            fromStr = child.fromStr
            if fromStr is not None:
                if importStr == "*":
                    module = __import__(fromStr, globals(), locals(), [importStr], -1)
                    try:
                        # If we are a module with other modules in us then we have an __all__
                        for item in module.__all__:
                            g[item] = getattr(module, item)
                    except:
                        # Else we just have some classes in us with no __all__
                        for item in GetClassesInModule(module):
                            g[item] = getattr(module, item)
                else:
                    module = __import__(fromStr, globals(), locals(), [importStr], -1)
                    for item in importStr.split(','):
                        item = item.strip()
                        g[item] = getattr(module, item)
            else:
                g[importStr] = __import__(importStr, globals(), locals(), [], -1)


def peachPrint(msg):
    print("Print: %s", msg)
    return True


def domPrint(node):
    from Peach.Engine.dom import DomPrint
    print("vv[ DomPrint ]vvvvvvvvvvvvvvvv\n%s\n^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^" % DomPrint(0, node))
    return True


def changeDefaultEndian(endian):
    if endian not in ['little', 'big']:
        raise PeachException("Called ChangeEndian with invalid paramter [%s]" % endian)
    from Peach.Engine.dom import Number
    Number.defaultEndian = endian
    return True


def evalEvent(code, environment, node=None):
    """
    Eval python code returning result.
    code - String
    environment - Dictionary, keys are variables to place in local scope
    """
    globalScope = {
        'Print': peachPrint,
        'peachPrint': peachPrint,
        'ChangeDefaultEndian': changeDefaultEndian,
        'DomPrint': domPrint,
    }
    localScope = {
        'Print': peachPrint,
        'peachPrint': peachPrint,
        'ChangeDefaultEndian': changeDefaultEndian,
        'DomPrint': domPrint,
    }
    if node is not None:
        buildImports(node, globalScope, localScope)
    if Holder.globals is not None:
        for k in Holder.globals:
            globalScope[k] = Holder.globals[k]
    if Holder.locals is not None:
        for k in Holder.locals:
            localScope[k] = Holder.locals[k]
    for k in environment.keys():
        globalScope[k] = environment[k]
        localScope[k] = environment[k]
    try:
        ret = eval(code, globalScope, localScope)
    except:
        print("Code: [%s]" % code)
        print("Exception: %s" % sys.exc_info()[1])
        print("Environment:")
        for k in environment.keys():
            print("  [%s] = [%s]" % (k, repr(environment[k])))
        raise
    return ret


class _Getch(object):
    """Gets a single character from standard input.  Does not echo to the screen."""
    def __init__(self):
        try:
            self.impl = _GetchWindows()
        except ImportError:
            self.impl = _GetchUnix()

    def __call__(self): return self.impl()


class _GetchUnix(object):

    def __call__(self):
        import tty, termios
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(sys.stdin.fileno())
            ch = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return ch


class _GetchWindows(object):

    def __call__(self):
        import msvcrt
        return msvcrt.getch()


getch = _Getch()


class StreamBuffer(object):
    """
    A Peach data stream.  Used when generating or cracking data.
    """

    def __init__(self, data=None):
        #: Current position
        self.pos = 0
        #: Data buffer
        self.data = ""
        #: History of data locations
        self.positions = {}
        #: History of data length
        self.lengths = {}

        if data is not None:
            self.data = data

    def getValue(self):
        """
        Return the value created by this stream.
        """
        return self.data

    def setValue(self, data):
        """
        Set the internal buffer.
        """
        self.data = data

    def peek(self, size=None):
        """
        Read data with out changing position.
        """
        if size is None:
            return self.data[self.pos:]

        if self.pos + size > len(self.data):
            raise Exception("StreamBuffer.peek(%d): Peeking passed end of buffer." % size)

        return self.data[self.pos:self.pos + size]

    def read(self, size=None):
        """
        Read from current position.  If size
        isn't specified, read rest of stream.

        Read will shift the current position.
        """

        if size is None:
            ret = self.data[self.pos:]
            self.pos = len(self.data)
            return ret

        if self.pos + size > len(self.data):
            raise Exception("StreamBuffer.read(%d): Reading passed end of buffer." % size)

        ret = self.data[self.pos:self.pos + size]
        self.pos += size
        return ret

    def storePosition(self, name):
        """
        Store our position by name
        """
        #print "Storing position of %s at %d" % (name, self.pos)
        self.positions[name] = self.pos
        return self.pos

    def getPosition(self, name):
        """
        Retreave position by name
        """
        if name not in self.positions:
            return None

        return self.positions[name]

    def write(self, data, name=None):
        """
        Write a block of data at current position.
        Stream will expand if needed to support the
        written data.  Otherwise it will overright
        the existing data.

        @type	data: string
        @param	data: Data to write
        @type	name: string
        @param	name: Name to store position under [optional]
        """

        if name is not None:
            #print "write: %s: %s" % (name, repr(data))
            self.storePosition(name)
            self.lengths[name] = len(data)

        dataLen = len(data)
        ourDataLen = len(self.data)

        # Replace existing data
        if ourDataLen - self.pos > dataLen:
            ret = self.data[:self.pos]
            ret += data
            ret += self.data[self.pos + dataLen:]
            self.data = ret

        # Append new data
        elif self.pos == ourDataLen:
            self.data += data

        # Do both
        else:
            self.data = self.data[:self.pos] + data

        # Move position
        self.pos += dataLen

    def count(self):
        """
        Get the current size in bytes of the data stream.
        """
        return len(self.data)

    def tell(self):
        """
        Return the current position in the data stream.
        """
        return self.pos

    def seekFromCurrent(self, pos):
        """
        Change current position in data.

        NOTE: If the position is past the end of the
              existing stream data the data will be expanded
              such that the position exists padded with '\0'
        """

        newpos = self.pos + pos
        self.seekFromStart(newpos)

    def seekFromStart(self, pos):
        """
        Change current position in data.

        NOTE: If the position is past the end of the
              existing stream data the data will be expanded
              such that the position exists padded with '\0'
        """

        if pos < 0:
            raise Exception("StreamBuffer.seekFromStart(%d) results in negative position" % pos)

        # Should we expand buffer?
        if pos > len(self.data):
            self.data += '\0' * (pos - len(self.data))

        self.pos = pos

    def seekFromEnd(self, pos):
        """
        Change current position in data.

        NOTE: If the position is past the end of the
              existing stream data the data will be expanded
              such that the position exists padded with '\0'
        """

        newpos = len(self.data) + pos
        self.seekFromStart(newpos)


import weakref


class PeachEvent(object):
    """
    A .NET like Event system.  Uses weak references
    to avoid memory issues.
    """

    def __init__(self):
        self.handlers = set()

    def _objectFinalized(self, obj):
        """
        Called when an object we have a weak reference
        to is being garbage collected.
        """
        self.handlers.remove(obj)

    def handle(self, handler):
        """
        Add a handler to our event
        """
        self.handlers.add(weakref.ref(handler, self._objectFinalized))
        return self

    def unhandle(self, handler):
        """
        Remove a handler from our event
        """
        try:
            for ref in self.handlers:
                if ref() == handler:
                    self.handlers.remove(ref)
        except:
            raise ValueError("Handler is not handling this event, so cannot unhandle it.")

        return self

    def fire(self, *args, **kargs):
        """
        Trigger event and call our handlers
        """
        for handler in self.handlers:
            handler()(*args, **kargs)

    def getHandlerCount(self):
        """
        Count of handlers registered for this event
        """
        return len(self.handlers)

    __iadd__ = handle
    __isub__ = unhandle
    __call__ = fire
    __len__ = getHandlerCount

#class MockFileWatcher:
#    def __init__(self):
#        self.fileChanged = Event()
#
#    def watchFiles(self):
#        source_path = "foo"
#        self.fileChanged(source_path)
#
#def log_file_change(source_path):
#    print "%r changed." % (source_path,)
#
#def log_file_change2(source_path):
#    print "%r changed!" % (source_path,)
#
#watcher              = MockFileWatcher()
#watcher.fileChanged += log_file_change2
#watcher.fileChanged += log_file_change
#watcher.fileChanged -= log_file_change2
#watcher.watchFiles()


class ArraySetParent(object):
    """
    Special array type that will
    set the parent on all children.
    """

    def __init__(self, parent):
        if parent is None:
            raise Exception("Whoa, parent == None!")
        self._parent = parent
        self._array = []

    def append(self, obj):
        #if hasattr(obj, "of"):
        #	if obj.of == "Tables":
        #		print "SETTING TABLES PARENT TO:", self._parent
        #		print obj
        #		traceback.print_stack();

        obj.parent = self._parent
        return self._array.append(obj)

    def index(self, obj):
        return self._array.index(obj)

    def insert(self, index, obj):
        obj.parent = self._parent
        return self._array.insert(index, obj)

    def remove(self, obj):
        return self._array.remove(obj)

    def __len__(self):
        return self._array.__len__()

    def __getitem__(self, key):
        return self._array.__getitem__(key)

    def __setitem__(self, key, value):
        value.parent = self._parent
        return self._array.__setitem__(key, value)

    def __delitem__(self, key):
        return self._array.__delitem__(key)

    def __iter__(self):
        return self._array.__iter__()

    def __contains__(self, item):
        return self._array.__contains__(item)


class BitBuffer(object):
    """
    Access buffer as bit stream. Support the normal reading from left to right
    of bits as well as the reverse right to left.
    """

    def __init__(self, buf='', bigEndian=False):
        self.buf = [ord(x) for x in buf]

        self.pos = 0
        self.len = len(buf) * 8

        self.closed = False
        self.softspace = 0

        self.bigEndian = bigEndian

    def close(self):
        """Let me think... Closes and flushes the toilet!"""
        if not self.closed:
            self.closed = True
            del self.buf, self.pos, self.len, self.softspace

    def isatty(self):
        if self.closed:
            raise ValueError("I/O operation on closed file")
        return 0

    def seek(self, pos, mode=0):
        """Set new position"""

        if self.closed:
            raise ValueError("I/O operation on closed file")
        if mode == 1:
            pos += self.pos
        elif mode == 2:
            pos += self.len
        self.pos = max(0, pos)

    def tell(self):
        """Tell current position"""

        if self.closed:
            raise ValueError("I/O operation on closed file")
        return self.pos

    def flush(self):
        """Flush the toilet"""

        if self.closed:
            raise ValueError("I/O operation on closed file")

    def truncate(self, size=None):
        if self.closed:
            raise ValueError("I/O operation on closed file")
        if size is None:
            size = self.pos
        elif size < 0:
            raise IOError(EINVAL, "Negative size not allowed")
        elif size < self.pos:
            self.pos = size

        self.len = size
        self.buf = self.buf[:(size // 8) + (size % 8 != 0)]
        if self.buf: self.buf[-1] &= (1 << (size % 8)) - 1

    def writebits(self, n, bitlen):
        """Writes bits"""

        if self.closed:
            raise ValueError("I/O operation on closed file")

        n &= (1 << bitlen) - 1

        newpos = self.pos + bitlen

        startBPos = self.pos % 8
        startBlock = self.pos // 8

        endBPos = newpos % 8
        endBlock = newpos // 8 + (endBPos != 0)

        #print startBlock, startBPos, endBlock, endBPos

        while len(self.buf) < endBlock: self.buf += [0]

        pos = startBPos

        if not self.bigEndian:
            while bitlen > 0:
                bitsLeft = 8 - (pos % 8)
                if bitsLeft > bitlen: bitsLeft = bitlen

                mask = (1 << bitsLeft) - 1

                self.buf[startBlock + (pos // 8)] ^= self.buf[startBlock + (pos // 8)] & (mask << (pos % 8))
                self.buf[startBlock + (pos // 8)] |= int(n & mask) << (pos % 8)

                n >>= bitsLeft
                bitlen -= bitsLeft

                pos += bitsLeft

            self.pos = newpos
            if self.pos > self.len:
                self.len = self.pos

        else:
            while bitlen > 0:
                bitsLeft = 8 - (pos % 8)
                if bitsLeft > bitlen: bitsLeft = bitlen

                mask = (1 << bitsLeft) - 1
                shift = (8 - self.bitlen(self.binaryFormatter(mask, 8))) - (pos - (pos / 8 * 8))

                byte = n >> bitlen - self.bitlen(self.binaryFormatter(mask, 8))

                self.buf[startBlock + (pos // 8)] |= ((byte & mask) << shift)

                bitlen -= bitsLeft
                pos += bitsLeft

            self.pos = newpos
            if self.pos > self.len:
                self.len = self.pos

    def binaryFormatter(self, num, bits):
        """
        Create a string in binary notation
        """
        ret = ""
        for i in range(bits - 1, -1, -1):
            ret += str((num >> i) & 1)

        assert len(ret) == bits
        return ret

    def bitlen(self, s):
        return len(s) - s.find('1')

    def readbits(self, bitlen):
        """
        Reads bits based on endianness
        """

        if self.closed:
            raise ValueError("I/O operation on closed file")

        newpos = self.pos + bitlen
        orig_bitlen = bitlen

        startBPos = self.pos % 8
        startBlock = self.pos // 8

        endBPos = newpos % 8
        endBlock = newpos // 8 + (endBPos != 0)

        ret = 0

        pos = startBPos

        while bitlen > 0:
            bitsLeft = 8 - (pos % 8)
            bitsToLeft = pos - (pos / 8 * 8)
            if bitsLeft > bitlen:
                bitsLeft = bitlen

            mask = (1 << bitsLeft) - 1

            byte = self.buf[startBlock + (pos // 8)]

            if not self.bigEndian:
                # Reverse all bits
                newByte = 0
                for _ in range(8):
                    bit = byte & 0x01
                    byte >>= 1
                    newByte <<= 1
                    newByte |= bit
                byte = newByte

            byte >>= (8 - bitsLeft) - bitsToLeft

            shift = self.bitlen(self.binaryFormatter(mask, 8))
            ret <<= shift
            ret |= byte & mask

            shift += bitsLeft
            bitlen -= bitsLeft
            pos += bitsLeft

        # Reverse requested bits
        if not self.bigEndian:
            newByte = 0
            for _ in range(orig_bitlen):
                bit = ret & 0x01
                ret >>= 1
                newByte <<= 1
                newByte |= bit
            ret = newByte

        self.pos = newpos
        return ret

    def getvalue(self):
        """Get the buffer"""

        return ''.join(map(chr, self.buf))

    def write(self, s):
        for c in str(s):
            self.writebits(ord(c), 8)

    def writelines(self, list):
        self.write(''.join(list))

    def read(self, i):
        ret = []
        for i in range(i):
            ret.append(chr(self.readbits(8)))

        return ''.join(ret)

    def writebit(self, b):
        """Writes Bit (1bit)"""

        self.writebits(b, 1)

    def readbit(self):
        """Reads Bit (1bit)"""

        return self.readbits(1)

    def writebyte(self, i):
        """Writes Byte (8bits)"""

        self.writebits(i, 8)

    def readbyte(self):
        """Reads Byte (8bits)"""

        return self.readbits(8)

    def writeword(self, i):
        """Writes Word (16bits)"""

        self.writebits(i, 16)

    def readword(self):
        """Reads Word (16bits)"""

        return self.readbits(16)

    def writedword(self, i):
        """Writes DWord (32bits)"""

        self.writebits(i, 32)

    def readdword(self):
        """Reads DWord (32bits)"""

        return self.readbits(32)

    def writevbl(self, n):
        """Writes Variable bit length."""

        self.writebit(n < 0)
        n = abs(n)
        self.writebits(n, 6)
        n >>= 6

        while n:
            self.writebit(1)
            self.writebits(n, 8)
            n >>= 8

        self.writebit(0)

    def readvbl(self):
        """Reads Variable bit length."""

        isNeg = self.readbit()
        r = self.readbits(6)
        pos = 6

        while self.readbit():
            r |= self.readbits(8) << pos
            pos += 8

        if isNeg:
            r = -r

        return r


import threading


class DomBackgroundCopier(object):
    """
    This class spins up a thread that makes
    copies of Data Models.  This should
    allow us to take advantage of multi-core
    CPUs and increase fuzzing speed.
    """

    copyThread = None
    stop = None

    def __init__(self):
        self.doms = []
        self.copies = {}
        self.minCopies = 1
        self.maxCopies = 10
        self.copiesLock = threading.Lock()
        DomBackgroundCopier.needcopies = threading.Event()
        DomBackgroundCopier.copyThread = None
        DomBackgroundCopier.stop = threading.Event()

        self.singleThread = True
        if os.getenv("PEACH_SINGLETHREAD") is None:
            self.singleThread = False
            DomBackgroundCopier.copyThread = threading.Thread(target=self.copier)
            self.copyThread.start()

    def copier(self):
        while not self.stop.isSet():
            for dom in self.doms:
                self.copiesLock.acquire()
                if len(self.copies[dom]) < self.minCopies:
                    self.copiesLock.release()

                    domCopy = dom.copy(None)

                    self.copiesLock.acquire()
                    self.copies[dom].append(domCopy)
                    self.copiesLock.release()
                else:
                    self.copiesLock.release()

            for dom in self.doms:
                self.copiesLock.acquire()
                if len(self.copies[dom]) < self.maxCopies:
                    #print "DOM[%s]: %d copies < %d" % (dom, len(self.copies[dom]), self.maxCopies)
                    self.copiesLock.release()

                    domCopy = dom.copy(None)

                    self.copiesLock.acquire()
                    self.copies[dom].append(domCopy)
                    self.copiesLock.release()

                else:
                    self.copiesLock.release()

            DomBackgroundCopier.needcopies.wait()
            DomBackgroundCopier.needcopies.clear()

    def addDom(self, dom):
        if dom in self.doms:
            return

        self.copiesLock.acquire()
        try:
            self.doms.append(dom)
            self.copies[dom] = []
        finally:
            self.copiesLock.release()
        DomBackgroundCopier.needcopies.set()

    def getCopy(self, dom):
        # If using a single thread just return a copy
        if self.singleThread:
            return dom.copy(None)

        if not dom in self.doms:
            return None

        if len(self.copies[dom]) == 0:
            return None

        if len(self.copies[dom]) < (self.maxCopies / 2):
            DomBackgroundCopier.needcopies.set()

        self.copiesLock.acquire()
        try:
            c = self.copies[dom][0]
            self.copies[dom] = self.copies[dom][1:]
            return c
        finally:
            self.copiesLock.release()

    def removeDom(self, dom):
        if not dom in self.doms:
            return

        self.copiesLock.acquire()
        try:
            self.doms.remove(dom)
            del self.copies[dom]
        finally:
            self.copiesLock.release()


class Highlight(object):
    HEADER = '\033[95m'
    INFO = '\033[36m'
    OK = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    REPR = '\033[35m'
    BLOCK = '\033[30;47m'
    NOTE = '\033[1;37m'
    ENDC = '\033[0m'

    def __init__(self):
        if os.sys.platform == "win32":
            self.disable()

    def error(self, msg):
        return "%s%s%s" % (self.FAIL, msg, self.ENDC)

    def ok(self, msg):
        return "%s%s%s" % (self.OK, msg, self.ENDC)

    def warning(self, msg):
        return "%s%s%s" % (self.WARNING, msg, self.ENDC)

    def repr(self, msg):
        return "%s%s%s" % (self.REPR, msg, self.ENDC)

    def block(self, msg):
        return "%s%s%s" % (self.BLOCK, msg, self.ENDC)

    def info(self, msg):
        return "%s%s%s" % (self.INFO, msg, self.ENDC)

    def note(self, msg):
        return "%s%s%s" % (self.NOTE, msg, self.ENDC)

    def disable(self):
        self.HEADER = ''
        self.INFO = ''
        self.GREEN = ''
        self.WARNING = ''
        self.FAIL = ''
        self.ENDC = ''


highlight = Highlight()
