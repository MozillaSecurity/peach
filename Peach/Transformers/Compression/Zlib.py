# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
import sys
import ctypes as C
import os
from ctypes import util

from Peach.transformer import Transformer


if sys.platform == "linux2" or sys.platform == "darwin":
    _zlib = C.cdll.LoadLibrary(util.find_library('libz'))
elif sys.platform == "win32":
    _zlib = C.cdll.LoadLibrary(os.path.join(os.path.dirname(__file__), "zlib1.dll"))
else:
    raise NotImplementedError


class _z_stream(C.Structure):
    _fields_ = [
        ("next_in", C.POINTER(C.c_ubyte)),
        ("avail_in", C.c_uint),
        ("total_in", C.c_ulong),
        ("next_out", C.POINTER(C.c_ubyte)),
        ("avail_out", C.c_uint),
        ("total_out", C.c_ulong),
        ("msg", C.c_char_p),
        ("state", C.c_void_p),
        ("zalloc", C.c_void_p),
        ("zfree", C.c_void_p),
        ("opaque", C.c_void_p),
        ("data_type", C.c_int),
        ("adler", C.c_ulong),
        ("reserved", C.c_ulong),
    ]


ZLIB_VERSION = C.c_char_p("1.2.3")
Z_NULL = 0x00
Z_OK = 0x00
Z_STREAM_END = 0x01
Z_NEED_DICT = 0x02
Z_BUF_ERR = -0x05
Z_NO_FLUSH = 0x00
Z_SYNC_FLUSH = 0x02
Z_FINISH = 0x04
CHUNK = 1024 * 128


class Compressor(object):
    def __init__(self, level=-1, dictionary=None):
        self.level = level
        self.st = _z_stream()
        err = _zlib.deflateInit_(C.byref(self.st), self.level, ZLIB_VERSION,
                                 C.sizeof(self.st))
        assert err == Z_OK, err
        if dictionary:
            err = _zlib.deflateSetDictionary(
                C.byref(self.st),
                C.cast(C.c_char_p(dictionary), C.POINTER(C.c_ubyte)),
                len(dictionary)
            )
            assert err == Z_OK, err

    def __call__(self, input):
        outbuf = C.create_string_buffer(CHUNK)
        self.st.avail_in = len(input)
        self.st.next_in = C.cast(C.c_char_p(input), C.POINTER(C.c_ubyte))
        self.st.next_out = C.cast(outbuf, C.POINTER(C.c_ubyte))
        self.st.avail_out = CHUNK
        err = _zlib.deflate(C.byref(self.st), Z_SYNC_FLUSH)
        if err in [Z_OK, Z_STREAM_END]:
            x = outbuf[:CHUNK - self.st.avail_out]
            return x
        else:
            raise AssertionError(err)

    def __del__(self):
        err = _zlib.deflateEnd(C.byref(self.st))


class Decompressor(object):
    def __init__(self, dictionary=None):
        self.dictionary = dictionary
        self.st = _z_stream()
        err = _zlib.inflateInit2_(C.byref(self.st), 15, ZLIB_VERSION,
                                  C.sizeof(self.st))
        assert err == Z_OK, err

    def __call__(self, input):
        outbuf = C.create_string_buffer(CHUNK)
        self.st.avail_in = len(input)
        self.st.next_in = C.cast(C.c_char_p(input), C.POINTER(C.c_ubyte))
        self.st.avail_out = CHUNK
        self.st.next_out = C.cast(outbuf, C.POINTER(C.c_ubyte))
        err = _zlib.inflate(C.byref(self.st), Z_SYNC_FLUSH)
        if err == Z_NEED_DICT:
            assert self.dictionary, "no dictionary provided"
            dict_id = _zlib.adler32(0,
                                    C.cast(C.c_char_p(self.dictionary), C.POINTER(C.c_ubyte)),
                                    len(self.dictionary))
            err = _zlib.inflateSetDictionary(
                C.byref(self.st),
                C.cast(C.c_char_p(self.dictionary), C.POINTER(C.c_ubyte)),
                len(self.dictionary)
            )
            assert err == Z_OK, err
            err = _zlib.inflate(C.byref(self.st), Z_SYNC_FLUSH)
        if err in [Z_OK, Z_STREAM_END]:
            return outbuf[:CHUNK - self.st.avail_out]
        else:
            raise AssertionError(err)

    def __del__(self):
        err = _zlib.inflateEnd(C.byref(self.st))


class DictZLib(Transformer):
    def __init__(self, level=-1, dicto=None):
        Transformer.__init__(self)
        self._level = level
        self._dicto = dicto

    def realEncode(self, data):
        _compress = Compressor(self._level, self._dicto)
        return _compress(data)

    def realDecode(self, data):
        _decompress = Decompressor(self._dicto)
        return _decompress(data)


class SPDYZLib(DictZLib):
    def __init__(self):
        _dicto = \
            "optionsgetheadpostputdeletetraceacceptaccept-charsetaccept-encod"\
            "ingaccept-languageauthorizationexpectfromhostif-modified-sinceif"\
            "-matchif-none-matchif-rangeif-unmodifiedsincemax-forwardsproxy-a"\
            "uthorizationrangerefererteuser-agent1001012002012022032042052063"\
            "0030130230330430530630740040140240340440540640740840941041141241"\
            "3414415416417500501502503504505accept-rangesageetaglocationproxy"\
            "-authenticatepublicretry-afterservervarywarningwww-authenticatea"\
            "llowcontent-basecontent-encodingcache-controlconnectiondatetrail"\
            "ertransfer-encodingupgradeviawarningcontent-languagecontent-leng"\
            "thcontent-locationcontent-md5content-rangecontent-typeetagexpire"\
            "slast-modifiedset-cookieMondayTuesdayWednesdayThursdayFridaySatu"\
            "rdaySundayJanFebMarAprMayJunJulAugSepOctNovDecchunkedtext/htmlim"\
            "age/pngimage/jpgimage/gifapplication/xmlapplication/xhtmltext/pl"\
            "ainpublicmax-agecharset=iso-8859-1utf-8gzipdeflateHTTP/1.1status"\
            "versionurl\0"
        DictZLib.__init__(self, dicto=_dicto)


if __name__ == "__main__":
    print(SPDYZLib().realDecode(DictZLib().realEncode('big ba\x45ng')))
