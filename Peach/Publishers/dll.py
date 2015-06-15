# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
import ctypes
from Peach.publisher import Publisher


class Dll(Publisher):
    """
    Shared library publisher using ctypes
    """

    def __init__(self, library):
        Publisher.__init__(self)
        self.library = library
        self.dll = None
        self.withNode = True

    def start(self):
        try:
            self.dll = ctypes.cdll.LoadLibrary(self.library)

        except:
            print("Caught exception loading library [%s]" % self.library)
            raise

    def stop(self):
        self.dll = None

    def callWithNode(self, method, args, argNodes):
        """
        Call method on COM object.

        @type	method: string
        @param	method: Name of method to invoke
        @type	args: array of objects
        @param	args: Arguments to pass
        """

        self._lastReturn = None

        #ct = argNodes[0].asCType()
        #print ct
        #print ct.contents
        #print ct._fields_
        #print ct.Named_37
        #print ct.Named_38

        try:
            ret = None
            callStr = "self.dll.%s(" % str(method)

            if len(args) > 0:
                for i in range(0, len(args)):
                    callStr += "argNodes[%d].asCType()," % i

                callStr = callStr[:len(callStr) - 1] + ")"

            else:
                callStr += ")"

            ret = eval(callStr)
            return ret

        except:
            print("dll.Dll(): Caught unknown exception making call to %s" % method)
            raise

    #def property(self, property, value = None):
    #	'''
    #	Get or set property
    #
    #	@type	property: string
    #	@param	property: Name of method to invoke
    #	@type	value: object
    #	@param	value: Value to set.  If None, return property instead
    #	'''
    #
    #	try:
    #		if value == None:
    #			ret = None
    #			callStr = "ret = self._object.%s" % str(property)
    #
    #			#print "Call string:", callStr
    #			exec callStr
    #			return ret
    #
    #		ret = None
    #		callStr = "self._object.%s = value" % str(property)
    #
    #		#print "Call string:", callStr
    #		exec callStr
    #		return None
    #
    #	except pywintypes.com_error, e:
    #		print "Caught pywintypes.com_error on property [%s]" % e
    #		#raise
    #
    #	except NameError, e:
    #		print "Caught NameError on property [%s]" % e
    #		#raise
    #
    #	except:
    #		print "Com::property(): Caught unknown exception"
    #		raise
    #
    #	return None
