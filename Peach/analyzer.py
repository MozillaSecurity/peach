# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


class Analyzer(object):
    """
    Analyzers produce data and state models. Examples of analyzers would be the parsing of Peach Pit XML files,
    tokenizing a string, building a data model based on XML file, etc.
    """
    supportParser = False
    supportDataElement = False
    supportCommandLine = False
    supportTopLevel = False

    def asParser(self, uri):
        """
        Called when Analyzer is used as default Pit parser. Produces a Peach DOM.
        """
        raise Exception("This analyzer cannot be used as parser.")

    def asDataElement(self, parent, args, dataBuffer):
        """
        Called when Analyzer is used in a data model. Returns a DataElement.
        """
        raise Exception("This analyzer does not support being attached to a data element.")

    def asCommandLine(self, args):
        """
        Called when Analyzer is used from command line. Produces a Peach Pit XML.
        """
        raise Exception("This analyzer does not support being run from the command line.")

    def asTopLevel(self, peach, args):
        """
        Called when Analyzer is used from top level.
        From the top level producing zero or more data models and state models is possible.

        :param args: arguments from <Param> elements.
        :type args: dict
        """
        raise Exception("This analyzer does not support being used as a top level element.")
