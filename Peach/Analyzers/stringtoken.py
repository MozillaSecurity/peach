# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from Peach.Engine.dom import *
from Peach.Engine.common import *
from Peach.analyzer import *


class StringTokenAnalyzer(Analyzer):
    """
    Produces a tree of strings based on token precidence.
    """

    supportCommandLine = False
    supportDataElement = True
    supportTopLevel = True

    # Tokens that group parts of a string
    pairs = [
        [u'{', u'}'],
        [u'(', u')'],
        [u'[', u']'],
        [u'<', u'>'],
    ]

    # Tokens in order of precidence
    tokens = [
        u'\0', u'\n', u'\r', u'<', u'>', u'?', u';', u',', u'|', u'@', u':', u'(', u')',
        u'{', u'}', u'[', u']', u'/', u'\\', u'&', u'=', u' ', u'-', u'+', u'.'
    ]

    def asCommandLine(self, args):
        """
        Called when Analyzer is used from command line.
        Analyzer should produce PeachPit XML as output.
        """
        raise NotImplementedError("StringTokenAnalyzer asCommandLine is not supported.")

    def asTopLevel(self, peach, args):
        """
        Called when Analyzer is used from top level.
        From the top level producing zero or more data models and state models is possible.
        """
        raise NotImplementedError("StringTokenAnalyzer asTopLevel is not supported.")

    def asDataElement(self, parent, args, data):
        """
        Called when Analyzer is used in a data model. Should return a DataElement.
        """
        if not isinstance(parent, String):
            raise PeachException("StringTokenAnalyzer can only be attached to <String> elements.")
        self.stringType = parent.type
        dom = self.tokenize_string(data, None)
        if parent.nullTerminated:
            blob = Blob(None, None)
            blob.defaultValue = "\x00" if parent.type is "wchar" else "\x00\x00"
            dom.append(blob)
        # replace parent with new dom
        dom.name = parent.name
        i = parent.parent.index(parent)
        del parent.parent[parent.name]
        parent.parent.insert(i, dom)

    def _new_string_element(self, value, parent=None):
        s = String(None, parent)
        s.type = self.stringType
        s.defaultValue = value
        try:
            _ = int(s.defaultValue)
            hint = Hint("NumericalString", s)
            hint.value = "true"
            s.hints.append(hint)
        except ValueError:
            pass
        return s

    def _split(self, string, token):
        """
        A version of split that also returns the tokens.
        """
        # return re.split('(\%c)' % token, string)
        pos = string.find(token)
        parts = []
        if pos is -1:
            return parts
        while pos > -1:
            parts.append(string[:pos])
            parts.append(string[pos:pos + 1])
            string = string[pos + 1:]
            pos = string.find(token)
        parts.append(string)
        return parts

    def tokenize_string(self, string, tokens=None):
        if string is None:
            return None
        tokens = self.tokens if tokens is None else tokens
        parent = Block(None, None)
        parent.append(self._new_string_element(string))
        for p in self.pairs:
            self._pair_tree(p, parent)
        for t in tokens:
            self._token_tree(t, parent)
        return parent

    def _pair_tree(self, p, node):
        if isinstance(node, Block):
            for c in node:
                self._pair_tree(p, c)
            return
        string = node.defaultValue
        index1 = string.find(p[0])
        if index1 is -1:
            return
        index2 = string[index1:].find(p[1])
        if index2 is -1:
            return
        index2 += index1
        block = Block(None, None)
        pre = string[:index1]
        token_start = string[index1]
        middle = string[index1 + 1:index2]
        token_end = string[index2]
        after = string[index2 + 1:]
        if len(pre):
            block.append(self._new_string_element(pre))
        block.append(self._new_string_element(token_start))
        block.append(self._new_string_element(middle))
        block.append(self._new_string_element(token_end))
        if len(after):
            block.append(self._new_string_element(after))
        block.name = node.name
        node.parent[node.name] = block

    def _token_tree(self, token, node):
        if isinstance(node, Block):
            for c in node:
                self._token_tree(token, c)
            return
        if len(node.defaultValue) < 2:
            return
        stuff = self._split(node.defaultValue, token)
        if not len(stuff):
            return
        block = Block(node.name, None)
        for s in stuff:
            block.append(self._new_string_element(s))
        node.parent[node.name] = block
