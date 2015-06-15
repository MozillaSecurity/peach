# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from Peach.analyzer import *
from Peach.Engine.dom import *
from Peach.Engine.common import *
from Peach.Engine.parser import PeachResolver

from lxml import etree


class XmlAnalyzer(Analyzer):
    """
    Produces data models or PeachPits from XML documents.
    """

    supportDataElement = True
    supportCommandLine = True
    supportTopLevel = True

    def __init__(self):
        pass

    def asDataElement(self, parent, args, dataBuffer):
        """
        Called when Analyzer is used in a data model.
        Should return a DataElement such as Block, Number or String.
        """
        if len(dataBuffer) == 0:
            return
        dom = _Xml2Dom().xml2Dom(dataBuffer)
        # replace parent with new dom
        dom.name = parent.name
        parentOfParent = parent.parent
        indx = parentOfParent.index(parent)
        del parentOfParent[parent.name]
        parentOfParent.insert(indx, dom)

    def asCommandLine(self, args):
        """
        Called when Analyzer is used from command line.
        Analyzer should produce PeachPit XML as output.
        """
        try:
            inFile = args["xmlfile"]
            outFile = args["out"]
        except:
            raise PeachException("XmlAnalyzer requires two parameters, xmlfile and out.")
        xml = _Xml2Peach().xml2Peach("file:" + inFile)
        with open(outFile, "wb+") as fo:
            fo.write(xml)

    def asTopLevel(self, peach, args):
        """
        Called when Analyzer is used from top level.
        From the top level producing zero or more data models and state models is possible.
        """
        raise Exception("asTopLevel not supported")


class _Xml2Peach(object):
    XmlContainer = """
<?xml version="1.0" encoding="utf-8"?>
<Peach>
	<Include ns="default" src="file:defaults.xml" />
	
	<DataModel name="TheDataModel">
%s
	</DataModel>

	<StateModel name="TheState" initialState="Initial">
		<State name="Initial">
			<Action type="output">
				<DataModel ref="TheDataModel" />
			</Action>
		</State>
	</StateModel>

	<Agent name="LocalAgent" location="http://127.0.0.1:9000">
		<Monitor class="test.TestStopOnFirst" />
	</Agent>
	-->
	
	<Test name="TheTest">
		<!-- <Agent ref="LocalAgent"/> -->
		<StateModel ref="TheState"/>
		<!-- TODO: Complete publisher -->
		<Publisher class="stdout.Stdout" />
	</Test>

	<Run name="DefaultRun">
		<Test ref="TheTest" />
	</Run>

</Peach>
"""

    def xml2Peach(self, url):
        parser = etree.XMLParser()
        parser.resolvers.add(PeachResolver())
        doc = etree.parse(url, parser=parser)
        peachDoc = etree.Element("DEADBEEF")
        self.handleElement(doc, peachDoc)
        # Get the string representation
        # TODO: make it better
        value = etree.tostring(peachDoc, pretty_print=True).strip()
        deadbeef, value = value[:10], value[10:]
        assert deadbeef == "<DEADBEEF>"
        value, deadbeef = value[:-11], value[-11:]
        assert deadbeef == "</DEADBEEF>"
        return self.XmlContainer % value

    def handleElement(self, node, parent):
        """
        Handle an XML element, children and attributes. Returns an XmlElement object.
        """
        if parent is None:
            return None
        # Element
        element = etree.Element("XmlElement")
        ns, tag = split_ns(node.tag)
        element.set("elementName", tag)
        if ns is not None:
            element.set("ns", ns)
        parent.append(element)
        # Element attributes
        for attrib in node.keys():
            attribElement = self.handleAttribute(attrib, node.get(attrib), element)
            element.append(attribElement)
        # Element children
        self._handleText(node.text, element)
        for child in node.iterchildren():
            if etree.iselement(child):  # TODO: skip comments
                self.handleElement(child, element)
            self._handleText(child.tail, element)
        return element

    def _handleText(self, text, parent):
        if text is not None and len(text.strip('\n\r\t\x10 ')) > 0:
            string = etree.Element("String")
            string.set("value", text)
            string.set("type", "utf8")
            parent.append(string)

    def handleAttribute(self, attrib, attribObj, parent):
        """
        Handle an XML attribute. Returns an XmlAttribute object.
        """
        # Attribute
        element = etree.Element("XmlAttribute")
        ns, attrib = split_ns(attrib)
        if ns is not None:
            element.set("ns", ns)
        element.set("attributeName", attrib)
        # Attribute value
        string = etree.Element("String")
        string.set("value", attribObj)
        string.set("type", "utf8")
        element.append(string)
        return element


class _Xml2Dom(object):
    """
    Convert an XML Document into a Peach DOM.
    """

    def xml2Dom(self, data):
        child = etree.XML(data)
        doc = child.getroottree()
        root = self.handleElement(child, None)
        return root

    def handleElement(self, node, parent):
        """
        Handle an XML element, children and attributes. Returns an XmlElement object.
        """
        doc = node.getroottree()
        # Element
        element = XmlElement(None, parent)
        ns, tag = split_ns(node.tag)
        if ns is not None:
            element.xmlNamespace = ns
        element.elementName = tag
        # Element attributes
        for attrib in node.keys():
            attribElement = self.handleAttribute(attrib, node.get(attrib), element)
            element.append(attribElement)
        # Element children
        self._handleText(node.text, element)
        for child in node.iterchildren():
            if etree.iselement(child):  # TODO: skip comments
                childElement = self.handleElement(child, element)
                element.append(childElement)
            self._handleText(child.tail, element)
        return element

    def _handleText(self, text, parent):
        if text is not None and len(text.strip('\n\r\t\x10 ')) > 0:
            string = String(None, parent)
            string.defaultValue = text
            parent.append(string)
            try:
                _ = int(string.defaultValue)
                hint = Hint("NumericalString", string)
                hint.value = "true"
                string.hints.append(hint)
            except ValueError:
                pass

    def handleAttribute(self, attrib, attribObj, parent):
        """
        Handle an XML attribute. Returns an XmlAttribute object.
        """
        # Attribute
        element = XmlAttribute(None, parent)
        ns, attrib = split_ns(attrib)
        if ns is not None:
            element.xmlNamespace = ns
        element.attributeName = attrib
        # Attribute value
        string = String(None, element)
        string.defaultValue = attribObj
        element.append(string)
        return element
