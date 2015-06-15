# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from Peach.Engine.parser import *
from Peach.Engine.common import *
from Peach.analyzer import *


class PitXmlAnalyzer(Analyzer):
    """
    Analyzers produce data and state models. Examples of analyzers would be the parsing
    of PeachPit XML files, tokenizing a string, building a data model based on XML file, etc.
    """

    supportParser = True

    def __init__(self):
        self.configs = None

    def asParser(self, uri):
        """
        Called when Analyzer is used as default Pit parser.
        Should produce a Peach DOM.
        """
        return ParseTemplate(self.configs).parse(uri)

