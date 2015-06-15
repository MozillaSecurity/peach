# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
import zlib
import hashlib
import binascii
import array

from lxml import etree

from Peach.fixup import Fixup
from Peach.Engine.common import *


class ExpressionFixup(Fixup):
    """
    Sometimes you need to perform some math as the fixup. This relation will
    take a ref, then a python expression.
    """

    def __init__(self, ref, expression):
        Fixup.__init__(self)
        self.ref = ref
        self.expression = expression

    def fixup(self):
        ref = self.context.findDataElementByName(self.ref)
        stuff = ref.getValue()
        if stuff is None:
            raise Exception("Error: ExpressionFixup was unable to locate "
                            "[{}]".format(self.ref))
        return evalEvent(self.expression,
                         {"self": self, "ref": ref, "data": stuff}, ref)


class SHA224Fixup(Fixup):

    def __init__(self, ref):
        Fixup.__init__(self)
        self.ref = ref

    def fixup(self):
        self.context.defaultValue = "0"
        stuff = self.context.findDataElementByName(self.ref).getValue()
        if stuff is None:
            raise Exception("Error: SHA1Fixup was unable to locate "
                            "[{}]".format(self.ref))
        h = hashlib.sha224()
        h.update(stuff)
        return h.digest()


class SHA256Fixup(Fixup):

    def __init__(self, ref):
        Fixup.__init__(self)
        self.ref = ref

    def fixup(self):
        self.context.defaultValue = "0"
        stuff = self.context.findDataElementByName(self.ref).getValue()
        if stuff is None:
            raise Exception("Error: SHA256Fixup was unable to locate "
                            "[{}]".format(self.ref))
        h = hashlib.sha256()
        h.update(stuff)
        return h.digest()


class SHA384Fixup(Fixup):

    def __init__(self, ref):
        Fixup.__init__(self)
        self.ref = ref

    def fixup(self):
        self.context.defaultValue = "0"
        stuff = self.context.findDataElementByName(self.ref).getValue()
        if stuff is None:
            raise Exception("Error: SHA384Fixup was unable to locate "
                            "[{}]".format(self.ref))
        h = hashlib.sha384()
        h.update(stuff)
        return h.digest()


class SHA512Fixup(Fixup):

    def __init__(self, ref):
        Fixup.__init__(self)
        self.ref = ref

    def fixup(self):
        self.context.defaultValue = "0"
        stuff = self.context.findDataElementByName(self.ref).getValue()
        if stuff is None:
            raise Exception("Error: SHA512Fixup was unable to locate "
                            "[{}]".format(self.ref))
        h = hashlib.sha512()
        h.update(stuff)
        return h.digest()


class SHA1Fixup(Fixup):

    def __init__(self, ref):
        Fixup.__init__(self)
        self.ref = ref

    def fixup(self):
        self.context.defaultValue = "0"
        stuff = self.context.findDataElementByName(self.ref).getValue()
        if stuff is None:
            raise Exception("Error: SHA1Fixup was unable to locate "
                            "[{}]".format(self.ref))
        h = hashlib.sha1()
        h.update(stuff)
        return h.digest()


class MD5Fixup(Fixup):

    def __init__(self, ref):
        Fixup.__init__(self)
        self.ref = ref

    def fixup(self):
        self.context.defaultValue = "0"
        stuff = self.context.findDataElementByName(self.ref.getValue())
        if stuff is None:
            raise Exception("Error: MD5Fixup was unable to locate "
                            "[{}]".format(self.ref))
        h = hashlib.md5()
        h.update(stuff)
        return h.digest()


class Crc32Fixup(Fixup):
    """
    Standard CRC32 as defined by ISO 3309. Used by PNG, ZIP, etc.
    """

    def __init__(self, ref):
        Fixup.__init__(self)
        self.ref = ref

    def fixup(self):
        self.context.defaultValue = "0"
        stuff = self.context.findDataElementByName(self.ref).getValue()
        if stuff is None:
            raise Exception("Error: Crc32Fixup was unable to locate "
                            "[{}]".format(self.ref))
        crc = zlib.crc32(stuff)
        if crc < 0:
            crc = ~crc ^ 0xffffffff
        return crc


class LRCFixup(Fixup):

    def __init__(self, ref):
        Fixup.__init__(self)
        self.ref = ref

    def fixup(self):
        self.context.defaultValue = "0"
        stuff = self.context.findDataElementByName(self.ref).getValue()
        if stuff is None:
            raise Exception("Error: LRCFixup was unable to locate "
                            "[{}]".format(self.ref))
        lrc = 0
        for b in stuff:
            lrc ^= ord(b)
        return chr(lrc)


class Crc32DualFixup(Fixup):
    """
    Standard CRC32 as defined by ISO 3309. Used by PNG, ZIP, etc.
    """

    def __init__(self, ref1, ref2):
        Fixup.__init__(self)
        self.ref1 = ref1
        self.ref2 = ref2

    def fixup(self):
        self.context.defaultValue = "0"
        stuff1 = self.context.findDataElementByName(self.ref1).getValue()
        stuff2 = self.context.findDataElementByName(self.ref2).getValue()
        if stuff1 is None or stuff2 is None:
            raise Exception("Error: Crc32DualFixup was unable to locate [{}] "
                            "or [{}]".format(self.ref1, self.ref2))
        crc1 = zlib.crc32(stuff1)
        crc = zlib.crc32(stuff2, crc1)
        if crc < 0:
            crc = ~crc ^ 0xffffffff
        return crc


class EthernetChecksumFixup(Fixup):
    """
    Ethernet Chucksum Fixup.
    """

    def __init__(self, ref):
        Fixup.__init__(self)
        self.ref = ref

    def _checksum(self, checksum_packet):
        ethernetKey = 0x04C11DB7
        return binascii.crc32(checksum_packet, ethernetKey)

    def fixup(self):
        self.context.defaultValue = "0"
        stuff = self.context.findDataElementByName(self.ref).getValue()
        if stuff is None:
            raise Exception("Error: EthernetChecksumFixup was unable to locate"
                            " [{}]".format(self.ref))
        return self._checksum(stuff)


class IcmpChecksumFixup(Fixup):
    """
    Ethernet Checksum Fixup.
    """

    def __init__(self, ref):
        Fixup.__init__(self)
        self.ref = ref

    def _checksum(self, checksum_packet):
        # Add byte if not dividable by 2
        if len(checksum_packet) & 1:
            checksum_packet += '\0'
            # Split into 16-bit word and insert into a binary array
        words = array.array('h', checksum_packet)
        sum = 0
        # Perform ones complement arithmetic on 16-bit words
        for word in words:
            sum += (word & 0xffff)
        hi = sum >> 16
        lo = sum & 0xffff
        sum = hi + lo
        sum += sum >> 16
        return (~sum) & 0xffff  # return ones complement

    def fixup(self):
        self.context.defaultValue = "0"
        stuff = self.context.findDataElementByName(self.ref).getValue()
        if stuff is None:
            raise Exception("Error: IcmpChecksumFixup was unable to locate "
                            "[{}]".format(self.ref))
        return self._checksum(stuff)


class FontTableChecksum(Fixup):

    def __init__(self, ref):
        Fixup.__init__(self)
        self.ref = ref

    def calc(self, stuff):
        sum = 0x00
        length = len(stuff)
        #stuff += '\x00' * (length % 4)
        for c in range(length):
            sum += int(ord(stuff[c]))
        return sum

    def fixup(self):
        ref = self.context.findDataElementByName(self.ref)
        #print "self.context.findDataElementByName:", ref.getFullname()
        stuff = ref.getValue()
        #print "First 10 bytes of Data:", repr(stuff[0:10])
        if stuff is None:
            raise Exception("Error: FontTableChecksumFixup was unable to "
                            "locate [{}]".format(self.ref))
        return self.calc(stuff)


class FontChecksum(Fixup):

    def __init__(self, ref):
        Fixup.__init__(self)
        self.ref = ref

    def calc(self, stuff):
        sum = 0x00
        length = len(stuff)
        #stuff += '\x00' * (length % 4)
        for c in range(length):
            sum += int(ord(stuff[c]))
        return sum

    def fixup(self):
        ref = self.context.findDataElementByName(self.ref)
        stuff = ref.getValue()
        if stuff is None:
            raise Exception("Error: FontChecksum Fixup was unable to locate "
                            "[{}]".format(self.ref))
        return 0xB1B0AFBA - self.calc(stuff)


try:
    import sspi, sspicon

    class SspiAuthenticationFixup(Fixup):
        """
        Perform basic SSPI authentication. Assumes a two step auth.
        """

        _sspi = None
        _firstObj = None
        _secondObj = None
        _data = None

        def __init__(self, firstSend, secondSend, user=None, group=None, password=None):
            Fixup.__init__(self)
            self.firstSend = firstSend
            self.secondSend = secondSend
            self.username = user
            self.workgroup = group
            self.password = password

        def getXml(self):
            dict = {}
            doc = etree.fromstring("<Peach/>", base_url="http://phed.org")
            self.context.getRoot().toXmlDom(doc, dict)
            return doc

        def fixup(self):
            try:
                fullName = self.context.getFullname()
                xml = self.getXml()
                firstFullName = str(xml.xpath(self.firstSend)[0].get("fullName"))
                firstFullName = firstFullName[firstFullName.index('.') + 1:]
                if fullName.find(firstFullName) > -1 and SspiAuthenticationFixup._firstObj != self.context:
                    #scflags = sspicon.ISC_REQ_INTEGRITY|sspicon.ISC_REQ_SEQUENCE_DETECT|\
                    #	sspicon.ISC_REQ_REPLAY_DETECT|sspicon.ISC_REQ_CONFIDENTIALITY
                    scflags = sspicon.ISC_REQ_INTEGRITY | sspicon.ISC_REQ_SEQUENCE_DETECT | \
                              sspicon.ISC_REQ_REPLAY_DETECT
                    SspiAuthenticationFixup._firstObj = self.context
                    SspiAuthenticationFixup._sspi = sspi.ClientAuth(
                        "Negotiate",
                        "", # client_name
                        (self.username, self.workgroup, self.password), # auth_info
                        None, # targetsn (target security context provider)
                        scflags, #scflags	# None,	# security context flags
                    )
                    (done, data) = SspiAuthenticationFixup._sspi.authorize(None)
                    data = data[0].Buffer
                    SspiAuthenticationFixup._data = data
                    return data
                if fullName.find(firstFullName) > -1:
                    return SspiAuthenticationFixup._data
                secondFullName = str(xml.xpath(self.secondSend)[0].get("fullName"))
                secondFullName = secondFullName[secondFullName.index('.') + 1:]
                if fullName.find(secondFullName) > -1 and SspiAuthenticationFixup._secondObj != self.context:
                    inputData = self.context.getInternalValue()
                    if len(inputData) < 5:
                        return None
                    (done, data) = SspiAuthenticationFixup._sspi.authorize(inputData)
                    data = data[0].Buffer
                    SspiAuthenticationFixup._secondObj = self.context
                    SspiAuthenticationFixup._data = data
                    return data
                if fullName.find(secondFullName) > -1:
                    return SspiAuthenticationFixup._data
            except:
                print("!!! EXCEPTION !!!")
                print(repr(sys.exc_info()))
                pass
except:
    pass
