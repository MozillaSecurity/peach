# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
import pit
import shark
import stringtoken
import xml
import binary
import asn1

from xml import XmlAnalyzer

# Alias default analyzers
XmlAnalyzer = xml.XmlAnalyzer
Asn1Analyzer = asn1.Asn1Analyzer
BinaryAnalyzer = binary.Binary
PitXmlAnalyzer = pit.PitXmlAnalyzer
WireSharkAnalyzer = shark.WireSharkAnalyzer
StringTokenAnalyzer = stringtoken.StringTokenAnalyzer

__all__ = ["xml", "shark", "stringtoken", "pit", "binary", "asn1",
           "XmlAnalyzer",
           "Asn1Analyzer",
           "BinaryAnalyzer",
           "PitXmlAnalyzer",
           "WireSharkAnalyzer",
           "StringTokenAnalyzer"
]
