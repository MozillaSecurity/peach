# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
import os
import sys

from Peach.analyzer import *
from Peach.Engine.dom import *
from Peach.Engine.common import *

try:
    from pyasn1.type import univ
    import pyasn1.codec.ber.decoder
    import pyasn1.codec.cer.decoder
    import pyasn1.codec.der.decoder

    import pyasn1.codec.ber.encoder
    import pyasn1.codec.cer.encoder
    import pyasn1.codec.der.encoder

except:
    #raise PeachException("Error loading pyasn1 library.  This library\ncan be installed from the dependencies folder.\n\n")
    pass


class Asn1Analyzer(Analyzer):
    """
    Produces data models or peach pits from XML documents.
    """

    #: Does analyzer support asDataElement()
    supportDataElement = True
    #: Does analyzer support asCommandLine()
    supportCommandLine = False
    #: Does analyzer support asTopLevel()
    supportTopLevel = True

    def __init__(self):
        pass

    def analyzeAsn1(self, codec, data):

        decoder = eval("pyasn1.codec.%s.decoder" % codec)

        asn1Obj = decoder.decode(data)[0]
        return self.Asn12Peach(codec, asn1Obj)

    def Asn12Peach(self, codec, asn1Obj):

        obj = Asn1Type(None, None)
        obj.asn1Type = asn1Obj.__class__.__name__
        obj.encodeType = codec
        obj.asnTagSet = None #asn1Obj._tagSet
        obj.asn1Spec = None # asn1Obj._asn1Spec

        if hasattr(asn1Obj, "_value"):
            value = asn1Obj._value
            obj.objType = type(value)

            if type(value) == long or type(value) == int:
                n = Number(None, None)
                n.defaultValue = str(value)
                n.size = 32

                obj.append(n)

            elif type(value) == str:
                # Could be blob or string...hmmm

                # Sometimes we have ASN.1 inside of ASN.1
                # most common for OctetString type
                if asn1Obj.__class__.__name__ == 'OctetString':
                    try:
                        decoder = eval("pyasn1.codec.%s.decoder" % codec)
                        subAsn1 = decoder.decode(asn1Obj._value)[0]

                        child = self.Asn12Peach(codec, subAsn1)
                        b = Block(None, None)
                        b.append(child)

                    except:
                        b = Blob(None, None)
                        b.defaultValue = value

                else:
                    b = Blob(None, None)
                    b.defaultValue = value

                obj.append(b)

            elif type(value) == tuple:
                # Probably and ObjectIdentifier!

                if asn1Obj.__class__.__name__ == 'ObjectIdentifier':
                    oid = []
                    for i in value:
                        oid.append(str(i))

                    b = String(None, None)
                    b.defaultValue = ".".join(oid)

                    obj.append(b)

                elif asn1Obj.__class__.__name__ == 'BitString':
                    # Make this a blob
                    b = Blob(None, None)

                    encoder = eval("pyasn1.codec.%s.encoder" % codec)
                    b.defaultValue = encoder.encode(asn1Obj)[4:]

                    obj.append(b)

                else:
                    print("UNKNOWN TUPLE TYPE")
                    print(asn1Obj.__class__.__name__)
                    print(value)
                    raise Exception("foo")

        if hasattr(asn1Obj, "_componentValues"):
            for c in asn1Obj._componentValues:
                child = self.Asn12Peach(codec, c)
                obj.append(child)

        return obj

    def asDataElement(self, parent, args, dataBuffer):
        """
        Called when Analyzer is used in a data model.

        Should return a DataElement such as Block, Number or String.
        """

        dom = self.analyzeAsn1("der", dataBuffer)

        # Replace parent with new dom

        dom.name = parent.name
        parentOfParent = parent.parent

        indx = parentOfParent.index(parent)
        del parentOfParent[parent.name]
        parentOfParent.insert(indx, dom)

    # now just cross our fingers :)

    def asCommandLine(self, args):
        """
        Called when Analyzer is used from command line.  Analyzer
        should produce Peach PIT XML as output.
        """

        raise Exception("asCommandLine not supported (yet)")

    #try:
    #	inFile = args["xmlfile"]
    #	outFile = args["out"]
    #except:
    #	raise PeachException("XmlAnalyzer requires two parameters, xmlfile and out.")
    #
    #xml = _Xml2Peach().xml2Peach("file:"+inFile)
    #
    #fd = open(outfile, "wb+")
    #fd.write(xml)
    #fd.close()

    def asTopLevel(self, peach, args):
        """
        Called when Analyzer is used from top level.

        From the top level producing zero or more data models and
        state models is possible.
        """
        raise Exception("asTopLevel not supported")
