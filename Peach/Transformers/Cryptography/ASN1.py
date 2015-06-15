# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
try:
    from struct import *
    from Peach.transformer import Transformer
    from pyasn1.type import univ
    from pyasn1.codec import der, ber, cer

    class DerEncodeOctetString(Transformer):
        """DER encode an octect string ASN.1 style."""

        def realEncode(self, data):
            return der.encoder.encode(univ.OctetString(data))

    class DerEncodeBitString(Transformer):
        """DER encode a bit string ASN.1 style."""

        def realEncode(self, data):
            return der.encoder.encode(univ.BitString(data))

    class DerEncodeInteger(Transformer):
        """DER encode an integer ASN.1 style."""

        def realEncode(self, data):
            return der.encoder.encode(univ.Integer(int(data)))

    class DerEncodeBoolean(Transformer):
        """DER encode a boolean ASN.1 style. Expects 0 or 1."""

        def realEncode(self, data):
            data = int(data)
            if data != 0 and data != 1:
                raise Exception("DerEncodeBoolean transformer expects 0 or 1")
            return der.encoder.encode(univ.Boolean(data))

    class DerEncodeObjectIdentifier(Transformer):
        """DER encode an object identifierASN.1 style."""

        def realEncode(self, data):
            return der.encoder.encode(univ.ObjectIdentifier(data))

    class BerEncodeOctetString(Transformer):
        """BER encode a string ASN.1 style."""

        def realEncode(self, data):
            return ber.encoder.encode(univ.OctetString(data))

    class BerEncodeBitString(Transformer):
        """BER encode a bit string ASN.1 style."""

        def realEncode(self, data):
            return ber.encoder.encode(univ.BitString(data))

    class BerEncodeInteger(Transformer):
        """BER encode an integer ASN.1 style."""

        def realEncode(self, data):
            return ber.encoder.encode(univ.Integer(int(data)))

    class BerEncodeBoolean(Transformer):
        """BER encode a boolean ASN.1 style. Expects 0 or 1."""

        def realEncode(self, data):
            data = int(data)
            if data != 0 and data != 1:
                raise Exception("BerEncodeBoolean transformer expects 0 or 1")
            return ber.encoder.encode(univ.Boolean(data))

    class BerEncodeObjectIdentifier(Transformer):
        """BER encode an object identifierASN.1 style."""

        def realEncode(self, data):
            return ber.encoder.encode(univ.ObjectIdentifier(data))

    class CerEncodeOctetString(Transformer):
        """CER encode a string ASN.1 style."""

        def realEncode(self, data):
            return cer.encoder.encode(univ.OctetString(data))

    class CerEncodeBitString(Transformer):
        """CER encode a bit string ASN.1 style."""

        def realEncode(self, data):
            return cer.encoder.encode(univ.BitString(data))

    class CerEncodeInteger(Transformer):
        """CER encode an integer ASN.1 style."""

        def realEncode(self, data):
            return cer.encoder.encode(univ.Integer(int(data)))

    class CerEncodeBoolean(Transformer):
        """CER encode a boolean ASN.1 style.  Expects 0 or 1."""

        def realEncode(self, data):
            data = int(data)
            if data != 0 and data != 1:
                raise Exception("CerEncodeBoolean transformer expects 0 or 1")
            return cer.encoder.encode(univ.Boolean(data))

    class CerEncodeObjectIdentifier(Transformer):
        """CER encode an object identifierASN.1 style."""

        def realEncode(self, data):
            return cer.encoder.encode(univ.ObjectIdentifier(data))
except Exception as e:
    pass
