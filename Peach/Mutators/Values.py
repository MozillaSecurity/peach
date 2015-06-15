# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# Default: Big Endian
# Schema: (name, byteorder): [ values, ... ]

CustomValues = \
    {
        ("8bit", True): [
            "\xff",
            "\xfe",
            "\x01",
            "\x80",
            "\x7f",
        ],
        ("16bit", True): [
            "\xff\xff",
            "\xff\xfe",
            "\x7f\xff",
            "\x7f\xfe",
            "\x80\x00",
            "\x20\x00", # short << 2
            "\x40\x00", # ushort << 2
            "\x00\x01",
            "\x00\x00",
        ],
        ("32bit", True): [
            "\xff\xff\xff\xff",
            "\xff\xff\xff\xfe",
            "\x7f\xff\xff\xff",
            "\x7f\xff\xff\xfe",
            "\x80\x00\x00\x00",
            "\x00\x00\x00\x01", # unsigned short z = x - y
            "\xff\xc4\x40\x0f", # width * height * 4
            "\x00\x00\x00\x00", # n/0, array length
        ],
        ("bytestr", False): [
            "\x41\x41\x41\x41",
            "\x41\x41\x41\x41\x41\x41\x41"
        ],
        ("str", False): [
            "1",
            "10",
            "100"
        ]
        # https://developer.apple.com/fonts/ttrefman/RM05/Chap5.html
        # 0-255 8bit value as syscall + instruction bytes
        #  ...
    }

# UTF-7      2B 2F 76 (38 | 39 | 2B | 2F)
# UTF-8      EF BB BF
# UTF-16 LE  FE FF
# UTF-16 BE  FF FE
# UTF-32 BE  00 00 FE FF
# UTF-32 LE  FF FE 00 00