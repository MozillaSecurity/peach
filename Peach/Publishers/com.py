# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
import os
import sys
import time
import signal
try:
    import pywintypes
    import win32com.client
    import win32com.client.gencache
except:
    pass

from Peach.publisher import Publisher


class Com(Publisher):
    """
    Very simple Com publisher that allows for a single method call.  The
    method call is fed in as a string which is evaled.  This allows for
    calling any method with any number of parameters.
    """

    _clsid = None
    _methodFormat = None
    _lastReturn = None
    _object = None

    def __init__(self, clsid):
        """
        Create Com Object. clsid = '{...}'

        @type	clsid: string
        @param	clsid: CLSID of COM object in {...} format
        """
        Publisher.__init__(self)
        self._clsid = clsid
        self.withNode = True

    def start(self):
        try:
            self._object = None
            self._object = win32com.client.DispatchEx(self._clsid)

        except pywintypes.com_error as e:
            print("Caught pywintypes.com_error creating ActiveX control [%s]" % e)
            raise

        except:
            print("Caught unkown exception creating ActiveX control [%s]" % sys.exc_info()[0])
            raise

    def stop(self):
        self._object = None

    #	def call(self, method, args):
    def callWithNode(self, method, args, argNodes):
        """
        Call method on COM object.

        @type	method: string
        @param	method: Name of method to invoke
        @type	args: array of objects
        @param	args: Arguments to pass
        """

        self._lastReturn = None

        realArgNodes = []
        for arg in argNodes:
            if len(arg) == 1:
                realArgNodes.append(arg[0])
            else:
                realArgNodes.append(arg)

        for arg in realArgNodes:
            print("Type", type(arg.getInternalValue()))
            print("Value", repr(arg.getInternalValue()))

        try:
            ret = None
            callStr = "ret = self._object.%s(" % str(method)

            if len(realArgNodes) > 0:
                for i in range(0, len(argNodes)):
                    callStr += "realArgNodes[%d].getInternalValue()," % i

                callStr = callStr[:len(callStr) - 1] + ")"

            else:
                callStr += ")"

            print("Call:", callStr)

            exec(callStr)
            return ret

        except pywintypes.com_error as e:
            print("Caught pywintypes.com_error on call [%s]" % e)
            raise

        except NameError as e:
            print("Caught NameError on call [%s]" % e)
            raise

        except:
            print("Com::Call(): Caught unknown exception")
            raise

    #	def property(self, property, value = None):
    def propertyWithNode(self, property, value, valueNode):
        """
        Get or set property

        @type	property: string
        @param	property: Name of method to invoke
        @type	value: object
        @param	value: Value to set.  If None, return property instead
        """

        try:
            if value is None:
                ret = None
                callStr = "ret = self._object.%s" % str(property)

                #print "Call string:", callStr
                exec(callStr)
                return ret

            ret = None
            callStr = "self._object.%s = valueNode.getInternalValue()" % str(property)

            #print "Call string:", callStr
            exec(callStr)
            return None

        except pywintypes.com_error as e:
            print("Caught pywintypes.com_error on property [%s]" % e)
        #raise

        except NameError as e:
            print("Caught NameError on property [%s]" % e)
        #raise

        except:
            print("Com::property(): Caught unknown exception")
            raise

        return None
