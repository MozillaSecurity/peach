# -*- test-case-name: twisted.web.test.test_xmlrpc -*-
# Copyright (c) Twisted Matrix Laboratories.
# See LICENSE for details.

"""
A generic resource for publishing objects via XML-RPC.

Maintainer: Itamar Shtull-Trauring
"""

# System Imports
import base64, sys
try:
    import xmlrpc.client as xmlrpclib
    import urllib.parse as urlparse
except ImportError:
    import xmlrpclib
    import urlparse

# Sibling Imports
from twisted.web import resource, server, http
from twisted.internet import defer, protocol, reactor
from twisted.python import log, reflect, failure

# These are deprecated, use the class level definitions
NOT_FOUND = 8001
FAILURE = 8002


# Useful so people don't need to import xmlrpclib directly
Fault = xmlrpclib.Fault
Binary = xmlrpclib.Binary
Boolean = xmlrpclib.Boolean
DateTime = xmlrpclib.DateTime


def withRequest(f):
    """
    Decorator to cause the request to be passed as the first argument
    to the method.

    If an I{xmlrpc_} method is wrapped with C{withRequest}, the
    request object is passed as the first argument to that method.
    For example::

        @withRequest
        def xmlrpc_echo(self, request, s):
            return s

    @since: 10.2
    """
    f.withRequest = True
    return f



class NoSuchFunction(Fault):
    """
    There is no function by the given name.
    """


class Handler:
    """
    Handle a XML-RPC request and store the state for a request in progress.

    Override the run() method and return result using self.result,
    a Deferred.

    We require this class since we're not using threads, so we can't
    encapsulate state in a running function if we're going  to have
    to wait for results.

    For example, lets say we want to authenticate against twisted.cred,
    run a LDAP query and then pass its result to a database query, all
    as a result of a single XML-RPC command. We'd use a Handler instance
    to store the state of the running command.
    """

    def __init__(self, resource, *args):
        self.resource = resource # the XML-RPC resource we are connected to
        self.result = defer.Deferred()
        self.run(*args)

    def run(self, *args):
        # event driven equivalent of 'raise UnimplementedError'
        self.result.errback(
            NotImplementedError("Implement run() in subclasses"))


class XMLRPC(resource.Resource):
    """
    A resource that implements XML-RPC.

    You probably want to connect this to '/RPC2'.

    Methods published can return XML-RPC serializable results, Faults,
    Binary, Boolean, DateTime, Deferreds, or Handler instances.

    By default methods beginning with 'xmlrpc_' are published.

    Sub-handlers for prefixed methods (e.g., system.listMethods)
    can be added with putSubHandler. By default, prefixes are
    separated with a '.'. Override self.separator to change this.

    @ivar allowNone: Permit XML translating of Python constant None.
    @type allowNone: C{bool}

    @ivar useDateTime: Present datetime values as datetime.datetime objects?
        Requires Python >= 2.5.
    @type useDateTime: C{bool}
    """

    # Error codes for Twisted, if they conflict with yours then
    # modify them at runtime.
    NOT_FOUND = 8001
    FAILURE = 8002

    isLeaf = 1
    separator = '.'
    allowedMethods = ('POST',)

    def __init__(self, allowNone=False, useDateTime=False):
        resource.Resource.__init__(self)
        self.subHandlers = {}
        self.allowNone = allowNone
        self.useDateTime = useDateTime


    def __setattr__(self, name, value):
        if name == "useDateTime" and value and sys.version_info[:2] < (2, 5):
            raise RuntimeError("useDateTime requires Python 2.5 or later.")
        self.__dict__[name] = value


    def putSubHandler(self, prefix, handler):
        self.subHandlers[prefix] = handler

    def getSubHandler(self, prefix):
        return self.subHandlers.get(prefix, None)

    def getSubHandlerPrefixes(self):
        return self.subHandlers.keys()

    def render_POST(self, request):
        request.content.seek(0, 0)
        request.setHeader("content-type", "text/xml")
        try:
            if self.useDateTime:
                args, functionPath = xmlrpclib.loads(request.content.read(),
                    use_datetime=True)
            else:
                # Maintain backwards compatibility with Python < 2.5
                args, functionPath = xmlrpclib.loads(request.content.read())
        except Exception as e:
            f = Fault(self.FAILURE, "Can't deserialize input: %s" % (e,))
            self._cbRender(f, request)
        else:
            try:
                function = self.lookupProcedure(functionPath)
            except Fault as f:
                self._cbRender(f, request)
            else:
                # Use this list to track whether the response has failed or not.
                # This will be used later on to decide if the result of the
                # Deferred should be written out and Request.finish called.
                responseFailed = []
                request.notifyFinish().addErrback(responseFailed.append)
                if getattr(function, 'withRequest', False):
                    d = defer.maybeDeferred(function, request, *args)
                else:
                    d = defer.maybeDeferred(function, *args)
                d.addErrback(self._ebRender)
                d.addCallback(self._cbRender, request, responseFailed)
        return server.NOT_DONE_YET


    def _cbRender(self, result, request, responseFailed=None):
        if responseFailed:
            return

        if isinstance(result, Handler):
            result = result.result
        if not isinstance(result, Fault):
            result = (result,)
        try:
            try:
                content = xmlrpclib.dumps(
                    result, methodresponse=True,
                    allow_none=self.allowNone)
            except Exception as e:
                f = Fault(self.FAILURE, "Can't serialize output: %s" % (e,))
                content = xmlrpclib.dumps(f, methodresponse=True,
                                          allow_none=self.allowNone)

            request.setHeader("content-length", str(len(content)))
            request.write(content)
        except:
            log.err()
        request.finish()


    def _ebRender(self, failure):
        if isinstance(failure.value, Fault):
            return failure.value
        log.err(failure)
        return Fault(self.FAILURE, "error")


    def lookupProcedure(self, procedurePath):
        """
        Given a string naming a procedure, return a callable object for that
        procedure or raise NoSuchFunction.

        The returned object will be called, and should return the result of the
        procedure, a Deferred, or a Fault instance.

        Override in subclasses if you want your own policy.  The base
        implementation that given C{'foo'}, C{self.xmlrpc_foo} will be returned.
        If C{procedurePath} contains C{self.separator}, the sub-handler for the
        initial prefix is used to search for the remaining path.

        If you override C{lookupProcedure}, you may also want to override
        C{listProcedures} to accurately report the procedures supported by your
        resource, so that clients using the I{system.listMethods} procedure
        receive accurate results.

        @since: 11.1
        """
        if procedurePath.find(self.separator) != -1:
            prefix, procedurePath = procedurePath.split(self.separator, 1)
            handler = self.getSubHandler(prefix)
            if handler is None:
                raise NoSuchFunction(self.NOT_FOUND,
                    "no such subHandler %s" % prefix)
            return handler.lookupProcedure(procedurePath)

        f = getattr(self, "xmlrpc_%s" % procedurePath, None)
        if not f:
            raise NoSuchFunction(self.NOT_FOUND,
                "procedure %s not found" % procedurePath)
        elif not callable(f):
            raise NoSuchFunction(self.NOT_FOUND,
                "procedure %s not callable" % procedurePath)
        else:
            return f

    def listProcedures(self):
        """
        Return a list of the names of all xmlrpc procedures.

        @since: 11.1
        """
        return reflect.prefixedMethodNames(self.__class__, 'xmlrpc_')


__all__ = [
    "XMLRPC",
    "Handler",
    "NoSuchFunction",
    "Proxy",
    "Fault",
    "Binary",
    "Boolean",
    "DateTime"]
