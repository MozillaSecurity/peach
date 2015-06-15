# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
import urllib2
import httplib

from Peach.publisher import Publisher


class HttpPost(Publisher):
    """
    This publisher can be called like a method including one or more
    parameters to be sent.

    If called as a stream the data will be posted in the body.
    """

    def __init__(self, url):
        Publisher.__init__(self)
        #: Indicates which method should be called.
        self.withNode = False
        self.url = url
        (self.scheme, self.netloc, self.path, self.query, self.frag) = httplib.urlsplit(url)
        self.headers = {'User-Agent': 'Mozilla/4.0 (compatible; MSIE 5.5; Windows NT)'}

    def connect(self):
        pass

    def start(self):
        """
        Change state such that send/receave will work.  For Tcp this
        could be connecting to a remote host
        """
        pass

    def stop(self):
        """
        Change state such that send/receave will not work.  For Tcp this
        could be closing a connection, for a file it might be closing the
        file handle.
        """
        pass

    def send(self, data):
        """
        Publish some data

        @type	data: string
        @param	data: Data to publish
        """

        req = urllib2.Request(self.url, data, self.headers)
        urllib2.urlopen(req)

    def receive(self, size=None):
        """
        Receive some data.

        @type	size: integer
        @param	size: Number of bytes to return
        @rtype: string
        @return: data received
        """
        raise PeachException("Action 'receive' not supported by publisher")

    def call(self, method, args):
        """
        Call a method using arguments.

        @type	method: string
        @param	method: Method to call
        @type	args: Array
        @param	args: Array of strings as arguments
        @rtype: string
        @return: data returned (if any)
        """
        raise PeachException("Action 'call' not supported by publisher")

    def property(self, property, value=None):
        """
        Get or set property

        @type	property: string
        @param	property: Name of method to invoke
        @type	value: object
        @param	value: Value to set.  If None, return property instead
        """
        self.headers[property] = value

    def close(self):
        """
        Close current stream/connection.
        """
        pass


class HttpDigestAuth(Publisher):
    """
    A simple HTTP publisher.
    """

    def __init__(self, url, realm, username, password, headers=None, timeout=0.1):
        """
        @type	host: string
        @param	host: Remote host
        @type	port: number
        @param	port: Remote port
        @type	timeout: number
        @param	timeout: How long to wait for reponse
        """
        Publisher.__init__(self)
        self._url = url
        self._realm = realm
        self._username = username
        self._password = password
        self._headers = eval(headers)
        self._timeout = float(timeout)
        self._fd = None

    def stop(self):
        """
        Close connection if open.
        """
        self.close()

    def connect(self):
        pass

    def close(self):
        if self._fd:
            self._fd.close()
            self._fd = None

    def send(self, data):
        """
        Send data via sendall.

        @type	data: string
        @param	data: Data to send
        """

        passmgr = urllib2.HTTPPasswordMgr()
        passmgr.add_password(self._realm, self._url, self._username, self._password)

        auth_handler = urllib2.HTTPDigestAuthHandler(passmgr)
        opener = urllib2.build_opener(auth_handler)
        urllib2.install_opener(opener)

        req = urllib2.Request(self._url, data, self._headers)

        try:
            self._fd = urllib2.urlopen(req)
        except:
            self._fd = None

    def receive(self, size=None):
        """
        Receive upto 10000 bytes of data.

        @rtype: string
        @return: received data.
        """
        if self._fd:
            if size is not None:
                return self._fd.read(size)

            return self._fd.read()

        else:
            return ''


class HttpDigestAuthDefaultRealm(Publisher):
    """
    A simple HTTP publisher.
    """

    def __init__(self, url, authurl, username, password, headers=None, timeout=0.1):
        Publisher.__init__(self)
        self._url = url
        self._authurl = authurl
        self._username = username
        self._password = password
        self._headers = eval(headers)
        self._timeout = float(timeout)
        self._fd = None

    def stop(self):
        self.close()

    def connect(self):
        pass

    def close(self):
        if self._fd:
            self._fd.close()
            self._fd = None

    def send(self, data):

        passmgr = urllib2.HTTPPasswordMgrWithDefaultRealm()
        passmgr.add_password(None, self._authurl, self._username, self._password)

        auth_handler = urllib2.HTTPDigestAuthHandler(passmgr)
        opener = urllib2.build_opener(auth_handler)
        urllib2.install_opener(opener)

        req = urllib2.Request(self._url, data, self._headers)

        try:
            self._fd = urllib2.urlopen(req)
        except:
            self._fd = None

    def receive(self, size=None):
        """
        Receive upto 10000 bytes of data.

        @rtype: string
        @return: received data.
        """
        if self._fd:
            if size is not None:
                return self._fd.read(size)

            return self._fd.read()

        else:
            return ''


class HttpBasicAuth(Publisher):
    """
    A simple HTTP publisher.
    """

    def __init__(self, url, realm, username, password, headers=None, timeout=0.1):
        """
        @type	host: string
        @param	host: Remote host
        @type	port: number
        @param	port: Remote port
        @type	timeout: number
        @param	timeout: How long to wait for reponse
        """
        Publisher.__init__(self)
        self._url = url
        self._realm = realm
        self._username = username
        self._password = password
        self._headers = headers
        self._timeout = float(timeout)
        self._fd = None

    def start(self):
        """
        Create connection.
        """
        pass

    def stop(self):
        self.close()

    def close(self):
        """
        Close connection if open.
        """
        if self._fd:
            self._fd.close()
            self._fd = None

    def send(self, data):
        """
        Send data via sendall.

        @type	data: string
        @param	data: Data to send
        """

        passmgr = urllib2.HTTPPasswordMgr()
        passmgr.add_password(self._realm, self._url, self._username, self._password)

        auth_handler = urllib2.HTTPBasicAuthHandler(passmgr)
        opener = urllib2.build_opener(auth_handler)
        urllib2.install_opener(opener)

        req = urllib2.Request(self._url, data, self._headers)

        try:
            self._fd = urllib2.urlopen(req)
        except:
            self._fd = None


    def receive(self, size=None):
        """
        Receive upto 10000 bytes of data.

        @rtype: string
        @return: received data.
        """
        if self._fd:
            if size is not None:
                return self._fd.read(size)

            return self._fd.read()

        else:
            return ''
