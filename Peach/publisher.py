# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from Peach.Engine.common import SoftException, PeachException


class PublisherStartError(Exception):
    """
    Exception thrown if error occurs during start call.
    """
    pass


class PublisherStopError(Exception):
    """
    Exception thrown if error occurs during stop call.
    """
    pass


class PublisherSoftException(SoftException):
    """
    Recoverable exception occurred in the Publisher.
    """
    pass


class Timeout(SoftException):

    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return self.msg


class PublisherBuffer(object):
    """
    An I/O buffer.
    """

    def __init__(self, publisher, data=None, haveAllData=False):
        self.publisher = publisher
        if self.publisher is not None:
            self.publisher.publisherBuffer = self
        self.data = ""
        self.haveAllData = haveAllData
        if data is not None:
            self.data = data
            self.haveAllData = True

    def read(self, size=1):
        """
        Read additional data into I/O buffer.
        """
        if self.haveAllData:
            return
        ret = []
        timeout = False
        try:
            if size is not None:
                need = size
                while need > 0 and not self.haveAllData:
                    try:
                        ret.append(self.publisher.receive(size))
                        need -= len(ret[-1])
                    except Timeout:
                        # Retry once more after a timeout
                        if timeout:
                            raise
                        timeout = True
                        self.haveAllData = True
            else:
                try:
                    self.haveAllData = True
                    ret.append(self.publisher.receive(size))
                except Timeout:
                    pass
        finally:
            self.data = "".join([self.data] + ret)

    def readAll(self):
        if self.haveAllData:
            return
        try:
            self.read(None)
        finally:
            self.haveAllData = True


class Publisher(object):
    """
    The Publisher object(s) implement a way to send and/or receive data by
    some means. There are two "types" of publishers, stream based and call
    based. This base class supports both types.
    To support stream based publishing implement everything but "call". To
    support call based publishing implement start, stop, and call. A
    publisher can support both stream and call based publishing.
    """

    def __init__(self):
        #: Indicates which method should be called.
        self.withNode = False
        self.publisherBuffer = None

    def initialize(self):
        """
        Called at start of test run. Called once per <Test> section.
        """
        pass

    def finalize(self):
        """
        Called at end of test run. Called once per <Test> section.
        """
        pass

    def start(self):
        """
        Change state such that send/receive will work. For TCP this could be
        connecting to a remote host.
        """
        pass

    def stop(self):
        """
        Change state such that send/receive will not work. For TCP this could
        be closing a connection, for a file it might be closing the file
        handle.
        """
        pass

    def send(self, data):
        """
        Publish some data.

        :param data: data to publish
        :type data: str
        """
        raise PeachException("Action 'send' not supported by publisher.")

    def sendWithNode(self, data, dataNode):
        """
        Publish some data.

        :param data: data to publish
        :type data: str
        :param dataNode: root of data model that produced data
        :type dataNode: DataElement
        """
        raise PeachException("Action 'sendWithNode' not supported by "
                             "publisher.")

    def receive(self, size=None):
        """
        Receive some data.

        :param size: number of bytes to return
        :type size: int
        :returns: data received
        :rtype: str
        """
        raise PeachException("Action 'receive' not supported by publisher.")

    def call(self, method, args):
        """
        Call a method using arguments.

        :param method: method to call
        :type method: str
        :param args: list of strings as arguments
        :type args: list
        :returns: data (if any)
        :rtype: str
        """
        raise PeachException("Action 'call' not supported by publisher.")

    def callWithNode(self, method, args, argNodes):
        """
        Call a method using arguments.

        :param method: method to call
        :type method: str
        :param args: list of strings as arguments
        :type args: list
        :param argNodes: list of DataElements
        :type argNodes: list
        :returns: data (if any)
        :rtype: str
        """
        raise PeachException("Action 'callWithNode' not supported by publisher.")

    def property(self, property, value=None):
        """
        Get or set property.

        :param property: name of method to invoke
        :type property: str
        :param value: value to set. If None, return property instead
        :type value: object
        """
        raise PeachException("Action 'property' not supported by publisher.")

    def propertyWithNode(self, property, value, valueNode):
        """
        Get or set property.

        :param property: name of method to invoke
        :type property: str
        :param value: value to set. If None, return property instead
        :type value: object
        :param valueNode: data model root node that produced value
        :type valueNode: DataElement
        """
        raise PeachException("Action 'propertyWithNode' not supported by publisher.")

    def connect(self):
        """
        Called to connect or open a connection / file.
        """
        raise PeachException("Action 'connect' not supported by publisher.")

    def accept(self):
        """
        Accept incoming connection. Blocks until incoming connection occurs.
        """
        raise PeachException("Action 'accept' not supported by publisher.")

    def close(self):
        """
        Close current stream/connection.
        """
        raise PeachException("Action 'close' not supported by publisher.")

    def debug(self, fmt):
        print("{}: {}".format(self.__class__.__name__, fmt))
