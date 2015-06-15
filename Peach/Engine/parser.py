# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
import sys, re, types, os, glob, logging
import traceback
import logging
from uuid import uuid1

from lxml import etree

from Peach.Engine.dom import *
from Peach.Engine import dom
import Peach.Engine
from Peach.Mutators import *
from Peach.Engine.common import *
from Peach.Engine.incoming import DataCracker
from Peach.mutatestrategies import *
from Peach.config import getInstanceProvider


def PeachStr(s):
    """
    Our implementation of str() which does not
    convert None to 'None'.
    """

    if s is None:
        return None

    return str(s)


class PeachResolver(etree.Resolver):
    def resolve(self, url, id, context):
        scheme, filename = url.split(":", 1)
        # raise PeachException("URL Exception: scheme required")

        # Add the files path to our sys.path

        if scheme == 'file':

            if os.path.isfile(filename):
                newpath = os.path.abspath('.')
                if newpath not in sys.path:
                    sys.path.append(newpath)
                return self.resolve_file(open(filename), context)

            for d in sys.path:
                for new_fn in (os.path.join(d, filename), os.path.join(d, 'Peach/Engine', filename)):
                    if os.path.isfile(new_fn):
                        newpath = os.path.abspath(os.path.split(new_fn)[0])
                        if newpath not in sys.path:
                            sys.path.append(newpath)
                        return self.resolve_file(open(new_fn), context)

            raise PeachException("Peach was unable to locate [%s]" % url)

        return etree.Resolver.resolve(self, url, id, context)


class ParseTemplate(object):
    """
    The Peach 2 XML -> Peach DOM parser. Uses lxml library.
    Parser returns a top level context object that contains things like templates, namespaces, etc.
    """

    dontCrack = False

    def __init__(self, configs=None):
        self._parser = etree.XMLParser(remove_comments=True)
        self._parser.resolvers.add(PeachResolver())
        if configs is None:
            self._configs = {}
        else:
            self._configs = configs

    def _getBooleanAttribute(self, node, name):
        """If node has no attribute named |name| return True."""
        v = self._getAttribute(node, name)
        if not v:
            return True
        v = v.lower()
        r = v in ('true', 'yes', '1')
        if not r:
            assert v in ('false', 'no', '0')
        return r

    def substituteConfigVariables(self, xmlString, final=False):
        result = []
        pos = 0
        numVarsLeft = 0
        numVarsFound = 0
        unresolved = []

        if not final:
            logging.info("Analyzing XML for potential macros.")

        for m in re.finditer(r"\$(\w+:?\w*)\$", xmlString):
            result.append(xmlString[pos:m.start(0)])
            varName = m.group(1)

            handled = False

            if varName in self._configs:
                logging.debug('Setting "{}" to "{}"'.format(varName, self._configs[varName]))
                result.append(self._configs[varName])
                handled = True

            elif ':' in varName:
                # Instance provider
                (instanceProviderName, identifier) = varName.split(':')

                instanceProvider = getInstanceProvider(instanceProviderName)

                try:
                    instance = str(instanceProvider.getInstanceById(identifier, self._configs))

                    logging.debug('Setting "{}" to "{}"'.format(varName, instance))

                    result.append(instance)

                    handled = True

                except Exception:
                    # allow it to fail for now, probably need other macros to resolve this
                    pass

            if not handled:
                result.append(m.group(0))
                unresolved.append(m.group(1))
                numVarsLeft += 1

            pos = m.end(0)
            numVarsFound += 1
        result.append(xmlString[pos:])

        if not final:
            logging.info("Found {} macros, {} resolved.".format(numVarsFound, numVarsFound - numVarsLeft))
        elif unresolved:
            for u in unresolved:
                logging.warning("Unresolved macro: %s" % u)

        return "".join(result)

    def parse(self, uri):
        """
        Parse a Peach XML file pointed to by uri.
        """
        logging.info(highlight.info("Parsing %s" % uri))
        doc = etree.parse(uri, parser=self._parser, base_url="http://phed.org").getroot()

        if "_target" in self._configs:

            target = etree.parse(self._configs["_target"], parser=self._parser, base_url="http://phed.org").getroot()

            if split_ns(target.tag)[1] != 'Peach':
                raise PeachException("First element in document must be Peach, not '%s'" % target.tag)

            for child in target.iterchildren():
                doc.append(child)

            del self._configs["_target"]

        # try early to find configuration macros
        self.FindConfigurations(doc)

        xmlString = etree.tostring(doc)

        return self.parseString(xmlString, findConfigs=False)

    def parseString(self, xml, findConfigs=True):
        """
        Parse a string as Peach XML.
        """

        xml = self.substituteConfigVariables(xml)

        doc = etree.fromstring(xml, parser=self._parser, base_url="http://phed.org")
        return self.HandleDocument(doc, findConfigs=findConfigs)

    def GetClassesInModule(self, module):
        """
        Return array of class names in module
        """

        classes = []
        for item in dir(module):
            i = getattr(module, item)
            if type(i) == type and item[0] != '_':
                classes.append(item)
            elif type(i) == types.MethodType and item[0] != '_':
                classes.append(item)
            elif type(i) == types.FunctionType and item[0] != '_':
                classes.append(item)
            elif repr(i).startswith("<class"):
                classes.append(item)

        return classes

    def FindConfigurations(self, doc):

        # FIRST check for a configuration section. If one exists, we need to parse it and then restart.

        #print "Looking for Configuration element"
        has_config = False
        for child in doc.iterchildren():
            child_tag = split_ns(child.tag)[1]
            if child_tag != 'Configuration':
                continue
            #assert not has_config, "Multiple <Configuration> elements"
            has_config = True
            #print "Found Configuration element"
            for child in child.iterchildren():
                child_tag = split_ns(child.tag)[1]
                assert child_tag == "Macro", "Unknown child in Configuration element: {}".format(child_tag)
                name = child.get("name")
                if name not in self._configs:
                    #print "\t%s = %s" % (name, child.get("value"))
                    self._configs[name] = child.get("value")
                else:
                    #print "\t%s = %s [dropped]" % (name, child.get("value"))
                    pass
        return has_config

    def HandleDocument(self, doc, uri="", findConfigs=True):

        if findConfigs and self.FindConfigurations(doc):
            return self.parseString(etree.tostring(doc), findConfigs=False)

        #self.StripComments(doc)
        self.StripText(doc)

        ePeach = doc

        if split_ns(ePeach.tag)[1] != 'Peach':
            raise PeachException("First element in document must be Peach, not '%s'" % ePeach.tag)

        peach = dom.Peach()
        peach.peachPitUri = uri
        #peach.node = doc
        self.context = peach
        peach.mutators = None

        #: List of nodes that need some parse love list of [xmlNode, parent]
        self.unfinishedReferences = []

        for i in ['templates', 'data', 'agents', 'namespaces', 'tests', 'runs']:
            setattr(peach, i, ElementWithChildren())

        # Peach attributes

        for i in ['version', 'author', 'description']:
            setattr(peach, i, self._getAttribute(ePeach, i))

        # The good stuff -- We are going todo multiple passes here to increase the likely hood
        # that things will turn out okay.

        # Pass 1 -- Include, PythonPath, Defaults
        for child in ePeach.iterchildren():
            child_tag = split_ns(child.tag)[1]
            if child_tag == 'Include':
                # Include this file

                nsName = self._getAttribute(child, 'ns')
                nsSrc = self._getAttribute(child, 'src')

                parser = ParseTemplate(self._configs)
                ns = parser.parse(nsSrc)

                ns.name = nsName + ':' + nsSrc
                ns.nsName = nsName
                ns.nsSrc = nsSrc
                ns.elementType = 'namespace'
                ns.toXml = new_instancemethod(dom.Namespace.toXml, ns)

                nss = Namespace()
                nss.ns = ns
                nss.nsName = nsName
                nss.nsSrc = nsSrc
                nss.name = nsName + ":" + nsSrc
                nss.parent = peach
                ns.parent = nss

                peach.append(nss)
                peach.namespaces.append(ns)
                setattr(peach.namespaces, nsName, ns)

            elif child_tag == 'PythonPath':
                # Add a search path

                p = self.HandlePythonPath(child, peach)
                peach.append(p)
                sys.path.append(p.name)

            elif child_tag == 'Defaults':
                self.HandleDefaults(child, peach)

        # one last check for unresolved macros
        for child in ePeach.iterdescendants():
            for k,v in list(child.items()):
                child.set(k, self.substituteConfigVariables(v, final=True))

        # Pass 2 -- Import
        for child in ePeach.iterchildren():
            child_tag = split_ns(child.tag)[1]
            if child_tag == 'Import':
                # Import module

                if child.get('import') is None:
                    raise PeachException("Import element did not have import attribute!")

                importStr = self._getAttribute(child, 'import')

                if child.get('from') is not None:
                    fromStr = self._getAttribute(child, 'from')

                    if importStr == "*":
                        module = __import__(PeachStr(fromStr), globals(), locals(), [PeachStr(importStr)], -1)

                        try:
                            # If we are a module with other modules in us then we have an __all__
                            for item in module.__all__:
                                globals()["PeachXml_" + item] = getattr(module, item)

                        except:
                            # Else we just have some classes in us with no __all__
                            for item in self.GetClassesInModule(module):
                                globals()["PeachXml_" + item] = getattr(module, item)

                    else:
                        module = __import__(PeachStr(fromStr), globals(), locals(), [PeachStr(importStr)], -1)
                        for item in importStr.split(','):
                            item = item.strip()
                            globals()["PeachXml_" + item] = getattr(module, item)

                else:
                    globals()["PeachXml_" + importStr] = __import__(PeachStr(importStr), globals(), locals(), [], -1)

                Holder.globals = globals()
                Holder.locals = locals()

                i = Element()
                i.elementType = 'import'
                i.importStr = self._getAttribute(child, 'import')
                i.fromStr = self._getAttribute(child, 'from')

                peach.append(i)

        # Pass 3 -- Template
        for child in ePeach.iterchildren():
            child_tag = split_ns(child.tag)[1]
            if child_tag == "Python":
                code = self._getAttribute(child, "code")
                if code is not None:
                    exec(code)

            elif child_tag == 'Analyzer':
                self.HandleAnalyzerTopLevel(child, peach)

            elif child_tag == 'DataModel' or child_tag == 'Template':
                # do something
                template = self.HandleTemplate(child, peach)
                #template.node = child
                peach.append(template)
                peach.templates.append(template)
                setattr(peach.templates, template.name, template)

        # Pass 4 -- Data, Agent
        for child in ePeach.iterchildren():
            child_tag = split_ns(child.tag)[1]
            if child_tag == 'Data':
                # do data
                data = self.HandleData(child, peach)
                #data.node = child
                peach.append(data)
                peach.data.append(data)
                setattr(peach.data, data.name, data)

            elif child_tag == 'Agent':
                agent = self.HandleAgent(child, None)
                #agent.node = child
                peach.append(agent)
                peach.agents.append(agent)
                setattr(peach.agents, agent.name, agent)

            elif child_tag == 'StateModel' or child_tag == 'StateMachine':
                stateMachine = self.HandleStateMachine(child, peach)
                #stateMachine.node = child
                peach.append(stateMachine)

            elif child_tag == 'Mutators':
                if self._getBooleanAttribute(child, "enabled"):
                    mutators = self.HandleMutators(child, peach)
                    peach.mutators = mutators

        # Pass 5 -- Tests
        for child in ePeach.iterchildren():
            child_tag = split_ns(child.tag)[1]
            if child_tag == 'Test':
                tests = self.HandleTest(child, None)
                #tests.node = child
                peach.append(tests)
                peach.tests.append(tests)
                setattr(peach.tests, tests.name, tests)

            elif child_tag == 'Run':
                run = self.HandleRun(child, None)
                #run.node = child
                peach.append(run)
                peach.runs.append(run)
                setattr(peach.runs, run.name, run)

        # Pass 6 -- Analyzers

        # Simce analyzers can modify the DOM we need to make our list
        # of objects we will look at first!

        objs = []

        for child in peach.getElementsByType(Blob):
            if child.analyzer is not None and child.defaultValue is not None and child not in objs:
                objs.append(child)
        for child in peach.getElementsByType(String):
            if child.analyzer is not None and child.defaultValue is not None and child not in objs:
                objs.append(child)

        for child in objs:
            try:
                analyzer = eval("%s()" % child.analyzer)
            except:
                analyzer = eval("PeachXml_" + "%s()" % child.analyzer)

            analyzer.asDataElement(child, {}, child.defaultValue)

        # We suck, so fix this up
        peach._FixParents()
        peach.verifyDomMap()
        #peach.printDomMap()

        return peach

    def StripComments(self, node):
        i = 0
        while i < len(node):
            if not etree.iselement(node[i]):
                del node[i] # may not preserve text, don't care
            else:
                self.StripComments(node[i])
                i += 1

    def StripText(self, node):
        node.text = node.tail = None
        for desc in node.iterdescendants():
            desc.text = desc.tail = None

    def GetRef(self, str, parent=None, childAttr='templates'):
        """
        Get the object indicated by ref.  Currently the object must have
        been defined prior to this point in the XML
        """

        #print "GetRef(%s) -- Starting" % str

        origStr = str
        baseObj = self.context
        hasNamespace = False
        isTopName = True
        found = False

        # Parse out a namespace

        if str.find(":") > -1:
            ns, tmp = str.split(':')
            str = tmp

            #print "GetRef(%s): Found namepsace: %s" % (str, ns)

            # Check for namespace
            if hasattr(self.context.namespaces, ns):
                baseObj = getattr(self.context.namespaces, ns)
            else:
                #print self
                raise PeachException("Unable to locate namespace: " + origStr)

            hasNamespace = True

        for name in str.split('.'):
            #print "GetRef(%s): Looking for part %s" % (str, name)

            found = False

            if not hasNamespace and isTopName and parent is not None:
                # check parent, walk up from current parent to top
                # level parent checking at each level.

                while parent is not None and not found:
                    #print "GetRef(%s): Parent.name: %s" % (name, parent.name)

                    if hasattr(parent, 'name') and parent.name == name:
                        baseObj = parent
                        found = True

                    elif hasattr(parent, name):
                        baseObj = getattr(parent, name)
                        found = True

                    elif hasattr(parent.children, name):
                        baseObj = getattr(parent.children, name)
                        found = True

                    elif hasattr(parent, childAttr) and hasattr(getattr(parent, childAttr), name):
                        baseObj = getattr(getattr(parent, childAttr), name)
                        found = True

                    else:
                        parent = parent.parent

            # check base obj
            elif hasattr(baseObj, name):
                baseObj = getattr(baseObj, name)
                found = True

            # check childAttr
            elif hasattr(baseObj, childAttr):
                obj = getattr(baseObj, childAttr)
                if hasattr(obj, name):
                    baseObj = getattr(obj, name)
                    found = True

            else:
                raise PeachException("Could not resolve ref %s" % origStr)

            # check childAttr
            if found == False and hasattr(baseObj, childAttr):
                obj = getattr(baseObj, childAttr)
                if hasattr(obj, name):
                    baseObj = getattr(obj, name)
                    found = True

            # check across namespaces if we can't find it in ours
            if isTopName and found == False:
                for child in baseObj:
                    if child.elementType != 'namespace':
                        continue

                    #print "GetRef(%s): CHecking namepsace: %s" % (str, child.name)
                    ret = self._SearchNamespaces(child, name, childAttr)
                    if ret:
                        #print "GetRef(%s) Found part %s in namespace" % (str, name)
                        baseObj = ret
                        found = True

            isTopName = False

        if not found:
            raise PeachException("Unable to resolve reference: %s" % origStr)

        return baseObj

    def _SearchNamespaces(self, obj, name, attr):
        """
        Used by GetRef to search across namespaces
        """

        #print "_SearchNamespaces(%s, %s)" % (obj.name, name)
        #print "dir(obj): ", dir(obj)

        # Namespaces are stuffed under this variable
        # if we have it we should be it :)
        if hasattr(obj, 'ns'):
            obj = obj.ns

        if hasattr(obj, name):
            return getattr(obj, name)

        elif hasattr(obj, attr) and hasattr(getattr(obj, attr), name):
            return getattr(getattr(obj, attr), name)

        for child in obj:
            if child.elementType != 'namespace':
                continue

            ret = self._SearchNamespaces(child, name, attr)
            if ret is not None:
                return ret

        return None

    def GetDataRef(self, str):
        """
        Get the data object indicated by ref.  Currently the object must
        have been defined prior to this point in the XML.
        """

        origStr = str
        baseObj = self.context

        # Parse out a namespace

        if str.find(":") > -1:
            ns, tmp = str.split(':')
            str = tmp

            #print "GetRef(): Found namepsace:",ns

            # Check for namespace
            if hasattr(self.context.namespaces, ns):
                baseObj = getattr(self.context.namespaces, ns)
            else:
                raise PeachException("Unable to locate namespace")

        for name in str.split('.'):
            # check base obj
            if hasattr(baseObj, name):
                baseObj = getattr(baseObj, name)

            # check templates
            elif hasattr(baseObj, 'data') and hasattr(baseObj.data, name):
                baseObj = getattr(baseObj.data, name)

            else:
                raise PeachException("Could not resolve ref '%s'" % origStr)

        return baseObj

    _regsHex = (
        re.compile(r"^([,\s]*\\x([a-zA-Z0-9]{2})[,\s]*)"),
        re.compile(r"^([,\s]*%([a-zA-Z0-9]{2})[,\s]*)"),
        re.compile(r"^([,\s]*0x([a-zA-Z0-9]{2})[,\s]*)"),
        re.compile(r"^([,\s]*x([a-zA-Z0-9]{2})[,\s]*)"),
        re.compile(r"^([,\s]*([a-zA-Z0-9]{2})[,\s]*)")
    )

    def GetValueFromNode(self, node):
        value = None
        type = 'string'

        if node.get('valueType') is not None:
            type = self._getAttribute(node, 'valueType')
            if not (type == 'literal' or type == 'hex'):
                type = 'string'

        if node.get('value') is not None:
            value = self._getAttribute(node, 'value')

            # Convert variouse forms of hex into a binary string
            if type == 'hex':
                if len(value) == 1:
                    value = "0" + value

                ret = ''

                valueLen = len(value) + 1
                while valueLen > len(value):
                    valueLen = len(value)

                    for i in range(len(self._regsHex)):
                        match = self._regsHex[i].search(value)
                        if match is not None:
                            while match is not None:
                                ret += chr(int(match.group(2), 16))
                                value = self._regsHex[i].sub('', value)
                                match = self._regsHex[i].search(value)
                            break

                return ret

            elif type == 'literal':
                return eval(value)

        if value is not None and (type == 'string' or node.get('valueType') is None):
            value = re.sub(r"([^\\])\\n", r"\1\n", value)
            value = re.sub(r"([^\\])\\r", r"\1\r", value)
            value = re.sub(r"([^\\])\\t", r"\1\t", value)
            value = re.sub(r"([^\\])\\n", r"\1\n", value)
            value = re.sub(r"([^\\])\\r", r"\1\r", value)
            value = re.sub(r"([^\\])\\t", r"\1\t", value)
            value = re.sub(r"^\\n", r"\n", value)
            value = re.sub(r"^\\r", r"\r", value)
            value = re.sub(r"^\\t", r"\t", value)
            value = re.sub(r"\\\\", r"\\", value)

        return value

    def GetValueFromNodeString(self, node):
        """
        This one is specific to <String> elements.  We
        want to preserve unicode characters.
        """

        value = None
        type = 'string'

        if node.get('valueType') is not None:
            type = self._getAttribute(node, 'valueType')
            if not type in ['literal', 'hex', 'string']:
                raise PeachException("Error: [%s] has invalid valueType attribute." % node.getFullname())

        if node.get('value') is not None:
            value = node.get('value')

            # Convert variouse forms of hex into a binary string
            if type == 'hex':
                value = str(value)

                if len(value) == 1:
                    value = "0" + value

                ret = ''

                valueLen = len(value) + 1
                while valueLen > len(value):
                    valueLen = len(value)

                    for i in range(len(self._regsHex)):
                        match = self._regsHex[i].search(value)
                        if match is not None:
                            while match is not None:
                                ret += chr(int(match.group(2), 16))
                                value = self._regsHex[i].sub('', value)
                                match = self._regsHex[i].search(value)
                            break

                return ret

            elif type == 'literal':
                value = eval(value)

        if value is not None and type == 'string':
            value = re.sub(r"([^\\])\\n", r"\1\n", value)
            value = re.sub(r"([^\\])\\r", r"\1\r", value)
            value = re.sub(r"([^\\])\\t", r"\1\t", value)
            value = re.sub(r"([^\\])\\n", r"\1\n", value)
            value = re.sub(r"([^\\])\\r", r"\1\r", value)
            value = re.sub(r"([^\\])\\t", r"\1\t", value)
            value = re.sub(r"^\\n", r"\n", value)
            value = re.sub(r"^\\r", r"\r", value)
            value = re.sub(r"^\\t", r"\t", value)
            value = re.sub(r"\\\\", r"\\", value)

        return value

    def GetValueFromNodeNumber(self, node):
        value = None
        type = 'string'

        if node.get('valueType') is not None:
            type = self._getAttribute(node, 'valueType')
            if not type in ['literal', 'hex', 'string']:
                raise PeachException("Error: [%s] has invalid valueType attribute." % node.getFullname())

        if node.get('value') is not None:
            value = self._getAttribute(node, 'value')

            # Convert variouse forms of hex into a binary string
            if type == 'hex':
                if len(value) == 1:
                    value = "0" + value

                ret = ''

                valueLen = len(value) + 1
                while valueLen > len(value):
                    valueLen = len(value)

                    for i in range(len(self._regsHex)):
                        match = self._regsHex[i].search(value)
                        if match is not None:
                            while match is not None:
                                ret += match.group(2)
                                value = self._regsHex[i].sub('', value)
                                match = self._regsHex[i].search(value)
                            break

                return int(ret, 16)

            elif type == 'literal':
                value = eval(value)

        return value

    # Handlers for Template ###################################################

    def HandleTemplate(self, node, parent):
        """
        Parse an element named Template.  Can handle actual
        Template elements and also reference Template elements.

        e.g.:

        <Template name="Xyz"> ... </Template>

        or

        <Template ref="Xyz" />
        """

        template = None

        # ref

        if node.get('ref') is not None:
            # We have a base template
            obj = self.GetRef(self._getAttribute(node, 'ref'))

            template = obj.copy(parent)
            template.ref = self._getAttribute(node, 'ref')
            template.parent = parent

        else:
            template = Template(self._getAttribute(node, 'name'))
            template.ref = None
            template.parent = parent

        # name

        if node.get('name') is not None:
            template.name = self._getAttribute(node, 'name')

        template.elementType = 'template'

        # mutable

        mutable = self._getAttribute(node, 'mutable')
        if mutable is None or len(mutable) == 0:
            template.isMutable = True

        elif mutable.lower() == 'true':
            template.isMutable = True

        elif mutable.lower() == 'false':
            template.isMutable = False

        else:
            raise PeachException(
                "Attribute 'mutable' has unexpected value [%s], only 'true' and 'false' are supported." % mutable)

        # pointer

        pointer = self._getAttribute(node, 'pointer')
        if pointer is None:
            pass

        elif pointer.lower() == 'true':
            template.isPointer = True

        elif pointer.lower() == 'false':
            template.isPointer = False

        else:
            raise PeachException(
                "Attribute 'pointer' has unexpected value [%s], only 'true' and 'false' are supported." % pointer)

        # pointerDepth

        if node.get("pointerDepth") is not None:
            template.pointerDepth = self._getAttribute(node, 'pointerDepth')

        # children

        self.HandleDataContainerChildren(node, template)

        # Switch any references to old name
        if node.get('ref') is not None:
            oldName = self._getAttribute(node, 'ref')
            for relation in template._genRelationsInDataModelFromHere():
                if relation.of == oldName:
                    relation.of = template.name

                elif relation.From == oldName:
                    relation.From = template.name


        #template.printDomMap()
        return template

    def HandleCommonTemplate(self, node, elem):
        """
        Handle the common children of data elements like String and Number.
        """

        elem.onArrayNext = self._getAttribute(node, "onArrayNext")

        for child in node:
            child_nodeName = split_ns(child.tag)[1]
            if child_nodeName == 'Relation':
                relation = self.HandleRelation(child, elem)
                elem.relations.append(relation)

            elif child_nodeName == 'Transformer':
                if elem.transformer is not None:
                    raise PeachException("Error, data element [%s] already has a transformer." % elem.name)

                elem.transformer = self.HandleTransformer(child, elem)

            elif child_nodeName == 'Fixup':
                self.HandleFixup(child, elem)

            elif child_nodeName == 'Placement':
                self.HandlePlacement(child, elem)

            elif child_nodeName == 'Hint':
                self.HandleHint(child, elem)

            else:
                raise PeachException("Found unexpected child node '%s' in element '%s'." % (child_nodeName, elem.name))

    def HandleTransformer(self, node, parent):
        """
        Handle Transformer element
        """

        transformer = Transformer(parent)

        childTransformer = None
        params = []

        # class

        if node.get("class") is None:
            raise PeachException("Transformer element missing class attribute")

        generatorClass = self._getAttribute(node, "class")
        transformer.classStr = generatorClass

        # children

        for child in node.iterchildren():
            child_nodeName = split_ns(child.tag)[1]
            if child_nodeName == 'Transformer':
                if childTransformer is not None:
                    raise PeachException("A transformer can only have one child transformer")

                childTransformer = self.HandleTransformer(child, transformer)
                continue

            if child_nodeName == 'Param':
                param = self.HandleParam(child, transformer)
                transformer.append(param)
                params.append([param.name, param.defaultValue])

        code = "PeachXml_" + generatorClass + '('

        isFirst = True
        for param in params:
            if not isFirst:
                code += ', '
            else:
                isFirst = False

            code += PeachStr(param[1])

        code += ')'

        trans = eval(code, globals(), locals())

        if childTransformer is not None:
            trans.addTransformer(childTransformer.transformer)

        transformer.transformer = trans

        if parent is not None:
            parent.transformer = transformer
            transformer.parent = parent
            #parent.append(transformer)

        return transformer

    def HandleDefaults(self, node, parent):
        """
        Handle data element defaults
        """

        # children

        for child in node.iterchildren():
            child_nodeName = split_ns(child.tag)[1]
            if child_nodeName == 'Blob':
                if child.get('valueType') is not None:
                    Blob.defaultValueType = self._getAttribute(child, 'valueType')

                    if Blob.defaultValueType not in ['string', 'literal', 'hex']:
                        raise PeachException("Error, default value for Blob.valueType incorrect.")

                if child.get('lengthType') is not None:
                    Blob.defaultLengthType = self._getAttribute(child, 'lengthType')

                    if Blob.defaultLengthType not in ['string', 'literal', 'calc']:
                        raise PeachException("Error, default value for Blob.lengthType incorrect.")

            elif child_nodeName == 'Flags':
                if child.get('endian') is not None:
                    Flags.defaultEndian = self._getAttribute(child, 'endian')

                    if Flags.defaultEndian not in ['little', 'big', 'network']:
                        raise PeachException("Error, default value for Flags.endian incorrect.")

            elif child_nodeName == 'Number':
                if child.get('endian') is not None:
                    Number.defaultEndian = self._getAttribute(child, 'endian')

                    if Number.defaultEndian not in ['little', 'big', 'network']:
                        raise PeachException("Error, default value for Number.endian incorrect.")

                if child.get('size') is not None:
                    Number.defaultSize = int(self._getAttribute(child, 'size'))

                    if Number.defaultSize not in Number._allowedSizes:
                        raise PeachException("Error, default value for Number.size incorrect.")

                if child.get('signed') is not None:
                    Number.defaultSigned = self._getAttribute(child, 'signed')

                    if Number.defaultSigned not in ['true', 'false']:
                        raise PeachException("Error, default value for Number.signed incorrect.")

                    if Number.defaultSigned == 'true':
                        Number.defaultSigned = True
                    else:
                        Number.defaultSigned = False

                if child.get('valueType') is not None:
                    Number.defaultValueType = self._getAttribute(child, 'valueType')

                    if Number.defaultValueType not in ['string', 'literal', 'hex']:
                        raise PeachException("Error, default value for Number.valueType incorrect.")

            elif child_nodeName == 'String':
                if child.get('valueType') is not None:
                    String.defaultValueType = self._getAttribute(child, 'valueType')

                    if String.defaultValueType not in ['string', 'literal', 'hex']:
                        raise PeachException("Error, default value for String.valueType incorrect.")

                if child.get('lengthType') is not None:
                    String.defaultLengthType = self._getAttribute(child, 'lengthType')

                    if String.defaultLengthType not in ['string', 'literal', 'calc']:
                        raise PeachException("Error, default value for String.lengthType incorrect.")

                if child.get('padCharacter') is not None:
                    String.defaultPadCharacter = child.get('padCharacter')

                if child.get('type') is not None:
                    String.defaultType = self._getAttribute(child, 'type')

                    if String.defaultType not in ['wchar', 'char', 'utf8']:
                        raise PeachException("Error, default value for String.type incorrect.")

                if child.get('nullTerminated') is not None:
                    String.defaultNullTerminated = self._getAttribute(child, 'nullTerminated')

                    if String.defaultNullTerminated not in ['true', 'false']:
                        raise PeachException("Error, default value for String.nullTerminated incorrect.")

                    if String.defaultNullTerminated == 'true':
                        String.defaultNullTerminated = True
                    else:
                        String.defaultNullTerminated = False


    def HandleFixup(self, node, parent):
        """
        Handle Fixup element
        """

        fixup = Fixup(parent)

        params = []

        # class

        if node.get("class") is None:
            raise PeachException("Fixup element missing class attribute")

        fixup.classStr = self._getAttribute(node, "class")

        # children

        for child in node.iterchildren():
            if split_ns(child.tag)[1] == 'Param':
                param = self.HandleParam(child, fixup)
                fixup.append(param)
                params.append([param.name, param.defaultValue])

        code = "PeachXml_" + fixup.classStr + '('

        isFirst = True
        for param in params:
            if not isFirst:
                code += ', '
            else:
                isFirst = False

            code += PeachStr(param[1])

        code += ')'

        fixup.fixup = eval(code, globals(), locals())

        if parent is not None:
            if parent.fixup is not None:
                raise PeachException("Error, data element [%s] already has a fixup." % parent.name)

            parent.fixup = fixup

        return fixup

    def HandlePlacement(self, node, parent):
        """
        Handle Placement element
        """

        placement = Placement(parent)

        placement.after = self._getAttribute(node, "after")
        placement.before = self._getAttribute(node, "before")

        if placement.after is None and placement.before is None:
            raise PeachException("Error: Placement element must have an 'after' or 'before' attribute.")

        if placement.after is not None and placement.before is not None:
            raise PeachException("Error: Placement can only have one of 'after' or 'before' but not both.")

        if parent is not None:
            if parent.placement is not None:
                raise PeachException("Error, data element [%s] already has a placement." % parent.name)

            #print "Setting placement on",parent.name
            parent.placement = placement
            #parent.append(placement)

        return placement

    def HandleRelation(self, node, elem):
        if node.get("type") is None:
            raise PeachException("Relation element does not have type attribute")

        type = self._getAttribute(node, "type")
        of = self._getAttribute(node, "of")
        From = self._getAttribute(node, "from")
        name = self._getAttribute(node, "name")
        when = self._getAttribute(node, "when")
        expressionGet = self._getAttribute(node, "expressionGet")
        expressionSet = self._getAttribute(node, "expressionSet")
        relative = self._getAttribute(node, "relative")

        if of is None and From is None and when is None:
            raise PeachException("Relation element does not have of, from, or when attribute.")

        if type not in ['size', 'count', 'index', 'when', 'offset']:
            raise PeachException("Unknown type value in Relation element")

        relation = Relation(name, elem)
        relation.of = of
        relation.From = From
        relation.type = type
        relation.when = when
        relation.expressionGet = expressionGet
        relation.expressionSet = expressionSet

        if self._getAttribute(node, "isOutputOnly") is not None and self._getAttribute(node, "isOutputOnly") in ["True",
                                                                                                                 "true"]:
            relation.isOutputOnly = True

        if relative is not None:
            if relative.lower() in ["true", "1"]:
                relation.relative = True
                relation.relativeTo = self._getAttribute(node, "relativeTo")
            elif relative.lower() in ["false", "0"]:
                relation.relative = False
                relation.relativeTo = None
            else:
                raise PeachException("Error: Value of Relation relative attribute is not true or false.")

        return relation

    def HandleAnalyzerTopLevel(self, node, elem):
        if node.get("class") is None:
            raise PeachException("Analyzer element must have a 'class' attribute")

        # Locate any arguments
        args = {}

        for child in node.iterchildren():
            if split_ns(child.tag)[1] == 'Param' and child.get('name') is not None:
                args[self._getAttribute(child, 'name')] = self._getAttribute(child, 'value')

        cls = self._getAttribute(node, "class")

        try:
            obj = eval("%s()" % cls)
        except:
            raise PeachException("Error creating analyzer '%s': %s" % (obj, repr(sys.exc_info())))

        if not obj.supportTopLevel:
            raise PeachException("Analyzer '%s' does not support use as top-level element" % cls)

        obj.asTopLevel(self.context, args)

    def HandleCommonDataElementAttributes(self, node, element):
        """
        Handle attributes common to all DataElements such as:

         - minOccurs, maxOccurs
         - mutable
         - isStatic
         - constraint
         - pointer
         - pointerDepth
         - token

        """

        # min/maxOccurs

        self._HandleOccurs(node, element)

        # isStatic/token

        isStatic = self._getAttribute(node, 'isStatic')
        if isStatic is None:
            isStatic = self._getAttribute(node, 'token')
        if isStatic is None or len(isStatic) == 0:
            element.isStatic = False

        elif isStatic.lower() == 'true':
            element.isStatic = True

        elif isStatic.lower() == 'false':
            element.isStatic = False

        else:
            if node.get("isStatic") is not None:
                raise PeachException(
                    "Attribute 'isStatic' has unexpected value [%s], only 'true' and 'false' are supported." % isStatic)
            else:
                raise PeachException(
                    "Attribute 'token' has unexpected value [%s], only 'true' and 'false' are supported." % isStatic)

        # mutable

        mutable = self._getAttribute(node, 'mutable')
        if mutable is None or len(mutable) == 0:
            element.isMutable = True

        elif mutable.lower() == 'true':
            element.isMutable = True

        elif mutable.lower() == 'false':
            element.isMutable = False

        else:
            raise PeachException(
                "Attribute 'mutable' has unexpected value [%s], only 'true' and 'false' are supported." % mutable)

        # pointer

        pointer = self._getAttribute(node, 'pointer')
        if pointer is None:
            pass

        elif pointer.lower() == 'true':
            element.isPointer = True

        elif pointer.lower() == 'false':
            element.isPointer = False

        else:
            raise PeachException(
                "Attribute 'pointer' has unexpected value [%s], only 'true' and 'false' are supported." % pointer)

        # pointerDepth

        if node.get("pointerDepth") is not None:
            element.pointerDepth = self._getAttribute(node, 'pointerDepth')

        # constraint

        element.constraint = self._getAttribute(node, "constraint")


    def _HandleOccurs(self, node, element):
        """
        Grab min, max, and generated Occurs attributes
        """

        if node.get('generatedOccurs') is not None:
            element.generatedOccurs = self._getAttribute(node, 'generatedOccurs')
        else:
            element.generatedOccurs = 10

        occurs = self._getAttribute(node, 'occurs')
        minOccurs = self._getAttribute(node, 'minOccurs')
        maxOccurs = self._getAttribute(node, 'maxOccurs')

        if minOccurs is None:
            minOccurs = 1
        else:
            minOccurs = eval(minOccurs)

        if maxOccurs is None:
            maxOccurs = 1
        else:
            maxOccurs = eval(maxOccurs)

        if minOccurs is not None and maxOccurs is not None:
            element.minOccurs = int(minOccurs)
            element.maxOccurs = int(maxOccurs)

        elif minOccurs is not None and maxOccurs is None:
            element.minOccurs = int(minOccurs)
            element.maxOccurs = 1024

        elif maxOccurs is not None and minOccurs is None:
            element.minOccurs = 0
            element.maxOccurs = int(maxOccurs)

        else:
            element.minOccurs = 1
            element.maxOccurs = 1

        if occurs is not None:
            element.occurs = element.minOccurs = element.maxOccurs = int(occurs)

    def HandleBlock(self, node, parent):
        # name

        if node.get('name') is not None:
            name = self._getAttribute(node, 'name')
        else:
            name = None

        # ref

        if node.get('ref') is not None:
            oldName = self._getAttribute(node, "ref")

            if name is None or len(name) == 0:
                name = Element.getUniqueName()

            # We have a base template
            obj = self.GetRef(self._getAttribute(node, 'ref'), parent)

            block = obj.copy(parent)
            block.name = name
            block.parent = parent
            block.ref = self._getAttribute(node, 'ref')

            # Block may not be a block!
            if getattr(block, 'toXml', None) is None:
                block.toXml = new_instancemethod(dom.Block.toXml, block)
            block.elementType = 'block'

        else:
            block = dom.Block(name, parent)
            block.ref = None

        #block.node = node

        # length (in bytes)

        if node.get('lengthType') is not None and self._getAttribute(node, 'lengthType') == 'calc':
            block.lengthType = self._getAttribute(node, 'lengthType')
            block.lengthCalc = self._getAttribute(node, 'length')
            block.length = -1

        elif node.get('length') is not None:
            length = self._getAttribute(node, 'length')
            if length is not None and len(length) != 0:
                block.length = int(length)
            else:
                block.length = None

        # alignment

        try:
            alignment = self._getAttribute(node, 'alignment')
            if len(alignment) == 0:
                alignment = None
        except:
            alignment = None

        if alignment is not None:
            block.isAligned = True
            block.alignment = int(alignment) ** 2

        # common attributes

        self.HandleCommonDataElementAttributes(node, block)

        # children

        self.HandleDataContainerChildren(node, block)

        # Switch any references to old name

        if node.get('ref') is not None:
            for relation in block._genRelationsInDataModelFromHere():
                if relation.of == oldName:
                    relation.of = name

                elif relation.From == oldName:
                    relation.From = name

        # Add to parent
        parent.append(block)
        return block


    def HandleDataContainerChildren(self, node, parent, errorOnUnknown=True):
        """
        Handle parsing conatiner children.  This method
        will handle children of DataElement types for
        containers like Block, Choice, and Template.

        Can be used by Custom types to create Custom container
        types.

        @type	node: XML Element
        @param	node: Current XML Node being handled
        @type	parent: ElementWithChildren
        @param	parent: Parent of this DataElement
        @type	errorOnUnknown: Boolean
        @param	errorOnUnknonw: Should we throw an error on unexpected child node (default True)
        """
        # children

        for child in node.iterchildren():
            name = self._getAttribute(child, 'name')
            if name is not None and '.' in name:
                # Replace a deep node, can only happen if we
                # have a ref on us.

                if node.get('ref') is None:
                    raise PeachException(
                        "Error, periods (.) are not allowed in element names unless overrideing deep elements when a parent reference (ref). Name: [%s]" % name)

                # Okay, lets locate the real parent.
                obj = parent
                for part in name.split('.')[:-1]:
                    if part not in obj:
                        raise PeachException(
                            "Error, unable to resolve [%s] in deep parent of [%s] override." % (part, name))

                    obj = obj[part]

                if obj is None:
                    raise PeachException("Error, unable to resolve deep parent of [%s] override." % name)

                # Remove periods from name
                child.set('name', name.split('.')[-1])

                # Handle child with new parent.
                self._HandleDataContainerChildren(node, child, obj, errorOnUnknown)

            else:
                self._HandleDataContainerChildren(node, child, parent, errorOnUnknown)


    def _HandleDataContainerChildren(self, node, child, parent, errorOnUnknown=True):
        node_nodeName = split_ns(node.tag)[1]
        child_nodeName = split_ns(child.tag)[1]
        if child_nodeName == 'Block':
            self.HandleBlock(child, parent)
        elif child_nodeName == 'String':
            self.HandleString(child, parent)
        elif child_nodeName == 'Number':
            self.HandleNumber(child, parent)
        elif child_nodeName == 'Flags':
            self.HandleFlags(child, parent)
        elif child_nodeName == 'Flag':
            self.HandleFlag(child, parent)
        elif child_nodeName == 'Blob':
            self.HandleBlob(child, parent)
        elif child_nodeName == 'Choice':
            self.HandleChoice(child, parent)
        elif child_nodeName == 'Transformer':
            parent.transformer = self.HandleTransformer(child, parent)
        elif child_nodeName == 'Relation':
            relation = self.HandleRelation(child, parent)
            parent.relations.append(relation)
        elif child_nodeName == 'Fixup':
            self.HandleFixup(child, parent)
        elif child_nodeName == 'Placement':
            self.HandlePlacement(child, parent)
        elif child_nodeName == 'Hint':
            self.HandleHint(child, parent)
        elif child_nodeName == 'Seek':
            self.HandleSeek(child, parent)
        elif child_nodeName == 'Custom':
            self.HandleCustom(child, parent)
        elif child_nodeName == 'Asn1':
            self.HandleAsn1(child, parent)
        elif child_nodeName == 'XmlElement':
            # special XmlElement reference

            if child.get('ref') is not None:
                # This is our special case, if we ref we suck the children
                # of the ref into our selves.  This is tricky!

                # get and copy our ref
                obj = self.GetRef(self._getAttribute(child, 'ref'), parent.parent)

                newobj = obj.copy(parent)
                newobj.parent = None

                # first verify all children are XmlElement or XmlAttribute
                for subchild in newobj:
                    if not isinstance(subchild, XmlElement) and not isinstance(subchild, XmlAttribute):
                        raise PeachException(
                            "Error, special XmlElement ref case, reference must only have Xml elements!! (%s,%s,%s)" % (
                                subchild.parent.name, subchild.name, subchild))

                # now move over children
                for subchild in newobj:
                    parent.append(subchild)

                # remove replaced element
                if self._getAttribute(child, 'name') in parent:
                    del parent[self._getAttribute(child, 'name')]

            else:
                self.HandleXmlElement(child, parent)

        elif child_nodeName == 'XmlAttribute':
            self.HandleXmlAttribute(child, parent)

        elif errorOnUnknown:
            raise PeachException(
                PeachStr("found unexpected node [%s] in Element: %s" % (child_nodeName, node_nodeName)))

    def HandleMutators(self, node, parent):
        # name

        name = self._getAttribute(node, 'name')

        mutators = dom.Mutators(name, parent)

        # children

        for child in node.iterchildren():
            child_nodeName = split_ns(child.tag)[1]
            if child_nodeName != 'Mutator':
                raise PeachException(PeachStr("Found unexpected node in Mutators element: %s" % child_nodeName))

            if child.get('class') is None:
                raise PeachException("Mutator element does not have required class attribute")

            mutator = Mutator(self._getAttribute(child, 'class'), mutators)
            mutators.append(mutator)

        parent.append(mutators)
        return mutators


    def HandleChoice(self, node, parent):
        # name

        name = self._getAttribute(node, 'name')

        # ref

        if node.get('ref') is not None:
            if name is None or len(name) == 0:
                name = Element.getUniqueName()

            # We have a base template
            obj = self.GetRef(self._getAttribute(node, 'ref'), parent)

            #print "About to deep copy: ", obj, " for ref: ", self._getAttribute(node, 'ref')

            block = obj.copy(parent)
            block.name = name
            block.parent = parent
            block.ref = self._getAttribute(node, 'ref')

        else:
            block = Choice(name, parent)
            block.ref = None

        block.elementType = 'choice'

        # length (in bytes)

        if self._getAttribute(node, 'lengthType') == 'calc':
            block.lengthType = self._getAttribute(node, 'lengthType')
            block.lengthCalc = self._getAttribute(node, 'length')
            block.length = -1

        elif node.get('length') is not None:
            length = self._getAttribute(node, 'length')
            if length is not None and len(length) != 0:
                block.length = int(length)
            else:
                block.length = None

        # common attributes

        self.HandleCommonDataElementAttributes(node, block)

        # children
        self.HandleDataContainerChildren(node, block)

        parent.append(block)
        return block

    def HandleAsn1(self, node, parent):
        # name

        name = self._getAttribute(node, 'name')

        # ref

        if node.get('ref') is not None:
            raise PeachException("Asn1 element does not yet support ref!")
            #
            #if name == None or len(name) == 0:
            #	name = Element.getUniqueName()
            #
            ## We have a base template
            #obj = self.GetRef( self._getAttribute(node, 'ref'), parent )
            #
            ##print "About to deep copy: ", obj, " for ref: ", self._getAttribute(node, 'ref')
            #
            #block = obj.copy(parent)
            #block.name = name
            #block.parent = parent
            #block.ref = self._getAttribute(node, 'ref')

        else:
            block = Asn1Type(name, parent)
            block.ref = None

        # encode type

        if node.get("encode"):
            block.encodeType = node.get("encode")

        # asn1Type

        if node.get("type") is None:
            raise PeachException("Error, all Asn1 elements must have 'type' attribute.")

        block.asn1Type = node.get("type")

        # Tag Stuff

        if node.get("tagNumber") is not None:
            try:
                block.tagClass = Asn1Type.ASN1_TAG_CLASS_MAP[self._getAttribute(node, "tagClass").lower()]
                block.tagFormat = Asn1Type.ASN1_TAG_TYPE_MAP[self._getAttribute(node, "tagFormat").lower()]
                block.tagCategory = self._getAttribute(node, "tagCategory").lower()
                block.tagNumber = int(self._getAttribute(node, "tagNumber"))
            except:
                raise PeachException(
                    "Error, When using tags you must specify 'tagClass', 'tagFormat', 'tagCategory', and 'tagNumber'.")

        # common attributes

        self.HandleCommonDataElementAttributes(node, block)

        # children
        self.HandleDataContainerChildren(node, block)

        parent.append(block)
        return block

    def HandleXmlElement(self, node, parent):
        # name

        name = self._getAttribute(node, 'name')

        block = XmlElement(name, parent)

        # elementName

        block.elementName = self._getAttribute(node, "elementName")
        if block.elementName is None:
            raise PeachException("Error: XmlElement without elementName attribute.")

        # ns

        block.xmlNamespace = self._getAttribute(node, "ns")

        # length (in bytes)

        if self._getAttribute(node, 'lengthType') == 'calc':
            block.lengthType = self._getAttribute(node, 'lengthType')
            block.lengthCalc = self._getAttribute(node, 'length')
            block.length = -1

        elif node.get('length') is not None:
            length = self._getAttribute(node, 'length')
            if length is not None and len(length) != 0:
                block.length = int(length)
            else:
                block.length = None

        # common attributes

        self.HandleCommonDataElementAttributes(node, block)

        # children
        self.HandleDataContainerChildren(node, block)

        parent.append(block)
        return block

    def HandleXmlAttribute(self, node, parent):
        # name

        name = self._getAttribute(node, 'name')

        block = XmlAttribute(name, parent)

        # elementName

        block.attributeName = self._getAttribute(node, "attributeName")

        # ns

        block.xmlNamespace = self._getAttribute(node, "ns")

        # length (in bytes)

        if self._getAttribute(node, 'lengthType') == 'calc':
            block.lengthType = self._getAttribute(node, 'lengthType')
            block.lengthCalc = self._getAttribute(node, 'length')
            block.length = -1

        elif node.get('length') is not None:
            length = self._getAttribute(node, 'length')
            if length is not None and len(length) != 0:
                block.length = int(length)
            else:
                block.length = None

        # common attributes

        self.HandleCommonDataElementAttributes(node, block)

        # children
        self.HandleDataContainerChildren(node, block)

        parent.append(block)
        return block

    def _getAttribute(self, node, name):
        attr = node.get(name)
        if attr is None:
            return None

        return PeachStr(attr)

    def _getValueType(self, node):
        valueType = self._getAttribute(node, 'valueType')
        if valueType is None:
            return 'string'

        return valueType

    def HandleString(self, node, parent):
        # name

        name = self._getAttribute(node, 'name')

        string = String(name, parent)

        # value

        string.defaultValue = self.GetValueFromNodeString(node)
        string.valueType = self._getValueType(node)
        string.defaultValue = self._HandleValueTypeString(string.defaultValue, string.valueType)

        # tokens

        string.tokens = self._getAttribute(node, 'tokens')

        # padCharacter

        if node.get('padCharacter') is not None:
            val = node.get('padCharacter')
            val = val.replace("'", "\\'")
            string.padCharacter = eval("u'''" + val + "'''")

        # type

        if node.get('type') is not None:
            type = self._getAttribute(node, 'type')
            if type is None or len(type) == 0:
                string.type = 'char'

            elif not (type in ['char', 'wchar', 'utf8', 'utf-8', 'utf-16le', 'utf-16be']):
                raise PeachException("Unknown type of String: %s" % type)

            else:
                string.type = type

        # nullTerminated (optional)

        if node.get('nullTerminated') is not None:
            nullTerminated = self._getAttribute(node, 'nullTerminated')
            if nullTerminated is None or len(nullTerminated) == 0:
                nullTerminated = 'false'

            if nullTerminated.lower() == 'true':
                string.nullTerminated = True
            elif nullTerminated.lower() == 'false':
                string.nullTerminated = False
            else:
                raise PeachException("nullTerminated should be true or false")

        # length (bytes)

        if self._getAttribute(node, 'lengthType') == 'calc':
            string.lengthType = self._getAttribute(node, 'lengthType')
            string.lengthCalc = self._getAttribute(node, 'length')
            string.length = -1

        elif node.get('length') is not None:
            length = self._getAttribute(node, 'length')
            if length is None or len(length) == 0:
                length = None

            try:
                if length is not None:
                    string.length = int(length)
                else:
                    string.length = None
            except:
                raise PeachException("length must be a number or missing %s" % length)

        # Analyzer

        string.analyzer = self._getAttribute(node, 'analyzer')

        # common attributes

        self.HandleCommonDataElementAttributes(node, string)


        # Handle any common children

        self.HandleCommonTemplate(node, string)

        parent.append(string)
        return string

    def HandleNumber(self, node, parent):
        # name

        name = self._getAttribute(node, 'name')

        number = Number(name, parent)

        # value

        number.defaultValue = PeachStr(self.GetValueFromNodeNumber(node))
        number.valueType = self._getValueType(node)

        if number.defaultValue is not None:
            try:
                number.defaultValue = int(number.defaultValue)
            except:
                raise PeachException("Error: The default value for <Number> elements must be an integer.")

        # size (bits)

        if node.get('size') is not None:
            size = self._getAttribute(node, 'size')
            if size is None:
                raise PeachException(
                    "Number element %s is missing the 'size' attribute which is required." % number.name)

            number.size = int(size)

            if not number.size in number._allowedSizes:
                raise PeachException("invalid size")

        # endian (optional)

        if node.get('endian') is not None:
            number.endian = self._getAttribute(node, 'endian')
            if number.endian == 'network':
                number.endian = 'big'

            if number.endian != 'little' and number.endian != 'big':
                raise PeachException("invalid endian %s" % number.endian)

        # signed (optional)

        if node.get('signed') is not None:
            signed = self._getAttribute(node, 'signed')
            if signed is None or len(signed) == 0:
                signed = Number.defaultSigned

            if signed.lower() == 'true':
                number.signed = True
            elif signed.lower() == 'false':
                number.signed = False
            else:
                raise PeachException("signed must be true or false")

        # common attributes

        self.HandleCommonDataElementAttributes(node, number)

        # Handle any common children

        self.HandleCommonTemplate(node, number)

        parent.append(number)
        return number


    def HandleFlags(self, node, parent):
        name = self._getAttribute(node, 'name')

        flags = dom.Flags(name, parent)
        #flags.node = node

        # length (in bits)

        length = self._getAttribute(node, 'size')
        flags.length = int(length)
        if flags.length % 2 != 0:
            raise PeachException("length must be multiple of 2")

        if flags.length not in [8, 16, 24, 32, 64]:
            raise PeachException("Flags size must be one of 8, 16, 24, 32, or 64.")

        # endian

        if node.get('endian') is not None:
            flags.endian = self._getAttribute(node, 'endian')

            if not ( flags.endian == 'little' or flags.endian == 'big' ):
                raise PeachException("Invalid endian type on Flags element")

        # rightToLeft

        if node.get('rightToLeft') is not None:
            if self._getAttribute(node, 'rightToLeft').lower() == "true":
                flags.rightToLeft = True

            elif self._getAttribute(node, 'rightToLeft').lower() == "false":
                flags.rightToLeft = False

            else:
                raise PeachException("Flags attribute rightToLeft must be 'true' or 'false'.")

        # padding

        if node.get('padding') is not None:
            if self._getAttribute(node, 'padding').lower() == "true":
                flags.padding = True

            elif self._getAttribute(node, 'padding').lower() == "false":
                flags.padding = False

            else:
                raise PeachException("Flags attribute padding must be 'true' or 'false'.")

        # constraint
        flags.constraint = self._getAttribute(node, "constraint")

        # children

        for child in node.iterchildren():
            child_nodeName = split_ns(child.tag)[1]
            if child_nodeName == 'Flag':
                childName = self._getAttribute(child, 'name')
                if childName is not None:
                    if childName in flags:
                        raise PeachException("Error, found duplicate Flag name in Flags set [%s]" % flags.name)

                self.HandleFlag(child, flags)

            elif child_nodeName == 'Relation':
                self.HandleRelation(child, flags)

            else:
                raise PeachException(PeachStr("found unexpected node in Flags: %s" % child_nodeName))

        parent.append(flags)
        return flags


    def HandleFlag(self, node, parent):
        name = self._getAttribute(node, 'name')

        flag = Flag(name, parent)
        #flag.node = node

        # value

        flag.defaultValue = PeachStr(self.GetValueFromNode(node))
        flag.valueType = self._getValueType(node)

        # position (in bits)

        position = self._getAttribute(node, 'position')
        flag.position = int(position)

        # length (in bits)

        length = self._getAttribute(node, 'size')
        flag.length = int(length)

        if flag.position > parent.length:
            raise PeachException("Invalid position, parent not big enough")

        if flag.position + flag.length > parent.length:
            raise PeachException("Invalid length, parent not big enough")


        # Handle any common children

        self.HandleCommonTemplate(node, flag)

        # Handle common data elements attributes

        self.HandleCommonDataElementAttributes(node, flag)

        # rest

        parent.append(flag)
        return flag


    def HandleBlob(self, node, parent):
        name = self._getAttribute(node, 'name')

        blob = Blob(name, parent)

        # value

        blob.defaultValue = PeachStr(self.GetValueFromNode(node))
        blob.valueType = self._getValueType(node)

        # length (in bytes)

        if self._getAttribute(node, 'lengthType') == 'calc':
            blob.lengthType = self._getAttribute(node, 'lengthType')
            blob.lengthCalc = self._getAttribute(node, 'length')
            blob.length = -1

        elif node.get('length') is not None:
            length = self._getAttribute(node, 'length')
            if length is not None and len(length) != 0:
                blob.length = int(length)
            else:
                blob.length = None

        # padValue

        if node.get('padValue') is not None:
            blob.padValue = self._getAttribute(node, 'padValue')
        else:
            blob.padValue = "\0"

        # Analyzer

        blob.analyzer = self._getAttribute(node, 'analyzer')

        # common attributes

        self.HandleCommonDataElementAttributes(node, blob)

        # Handle any common children

        self.HandleCommonTemplate(node, blob)

        parent.append(blob)
        return blob


    def HandleCustom(self, node, parent):
        name = self._getAttribute(node, 'name')

        cls = self._getAttribute(node, 'class')

        code = "PeachXml_%s(name, parent)" % cls
        custom = eval(code, globals(), locals())
        #custom.node = node

        # value

        custom.defaultValue = PeachStr(self.GetValueFromNode(node))
        custom.valueType = self._getValueType(node)

        # Hex handled elsewere.
        if custom.valueType == 'literal':
            custom.defaultValue = PeachStr(eval(custom.defaultValue))

        # common attributes

        self.HandleCommonDataElementAttributes(node, custom)

        # Handle any common children

        self.HandleCommonTemplate(node, custom)

        # constraint
        custom.constraint = self._getAttribute(node, "constraint")

        # Custom parsing
        custom.handleParsing(node)

        # Done
        parent.append(custom)
        return custom


    def HandleSeek(self, node, parent):
        """
        Parse a <Seek> element, part of a data model.
        """

        seek = Seek(None, parent)
        #seek.node = node

        seek.expression = self._getAttribute(node, 'expression')
        seek.position = self._getAttribute(node, 'position')
        seek.relative = self._getAttribute(node, 'relative')

        if seek.relative is not None:
            seek.relative = int(seek.relative)

        if seek.position is not None:
            seek.position = int(seek.position)

        if seek.expression is None and seek.position is None and seek.relative is None:
            raise PeachException("Error: <Seek> element must have an expression, position, or relative attribute.")

        parent.append(seek)
        return seek


    def HandleData(self, node, parent):
        # attribute: name
        name = self._getAttribute(node, 'name')

        # attribute: ref
        if node.get('ref') is not None:
            if name is None or not len(name):
                name = Element.getUniqueName()
            data = self.GetDataRef(self._getAttribute(node, 'ref')).copy(parent)
            data.name = name
        else:
            data = Data(name)
            if not isinstance(parent, Action) and (name is None or not len(name)):
                raise PeachException("<Data> must have a name attribute!")
        data.elementType = 'data'

        # attribute: maxFileSize
        if node.get('maxFileSize') is not None:
            data.maxFileSize = int(self._getAttribute(node, 'maxFileSize'))

        # attribute: fileName
        if node.get('fileName') is not None:
            data.fileName = self._getAttribute(node, 'fileName')
            if data.fileName.find('*') != -1:
                data.fileGlob = data.fileName
                for fpath in glob.glob(data.fileGlob):
                    if data.is_valid(fpath):
                        data.fileName = fpath
                data.multipleFiles = True
            elif os.path.isdir(data.fileName):
                data.folderName = data.fileName
                for fname in os.listdir(data.folderName):
                    fpath = os.path.join(data.folderName, fname)
                    if data.is_valid(fpath):
                        data.fileName = fpath
                data.multipleFiles = True
        if not os.path.isfile(data.fileName):
            raise PeachException("No sample data found matching requirements of <Data> element.")

        # attribute: recurse
        if node.get('recurse') is not None:
            data.recurse = bool(self._getAttribute(node, 'recurse'))

        # attribute: switchCount
        if node.get('switchCount') is not None:
            data.switchCount = int(self._getAttribute(node, 'switchCount'))
        else:
            data.switchCount = None

        # attribute: expression
        if node.get('expression') is not None:
            if data.fileName is not None:
                raise PeachException("<Data> can not have both a fileName and expression attribute.")
            data.expression = self._getAttribute(node, 'expression')

        # children
        for child in node.iterchildren():
            child_nodeName = split_ns(child.tag)[1]
            if child_nodeName == 'Field':
                if data.fileName is not None or data.expression is not None:
                    raise PeachException("<Data> can not have a fileName or expression attribute along with Field "
                                         "child elements.")
                self.HandleField(child, data)
            else:
                raise PeachException("Found unexpected node inside <Data>: %s" % child_nodeName)

        return data


    def HandleField(self, node, parent):
        # name

        if node.get('name') is None:
            raise PeachException("No attribute name found on field element")

        name = self._getAttribute(node, 'name')

        # value

        if node.get('value') is None:
            raise PeachException("No attribute value found on Field element")

        value = self._getAttribute(node, 'value')

        field = Field(name, value, parent)
        field.value = PeachStr(self.GetValueFromNode(node))
        field.valueType = self._getValueType(node)

        if field.name in parent:
            parent[field.name] = field
        else:
            parent.append(field)

        return field

    # Handlers for Agent ###################################################

    def HandleAgent(self, node, parent):
        # name

        name = self._getAttribute(node, 'name')

        # ref

        if node.get('ref') is not None:
            if name is None or len(name) == 0:
                name = Element.getUniqueName()

            obj = self.GetRef(self._getAttribute(node, 'ref'))

            agent = obj.copy(parent)
            agent.name = name
            agent.ref = self._getAttribute(node, 'ref')

        else:
            agent = Agent(name, parent)

        #agent.node = node
        agent.description = self._getAttribute(node, 'description')
        agent.location = self._getAttribute(node, 'location')
        if agent.location is None or len(agent.location) == 0:
            agent.location = "LocalAgent"
            #raise PeachException("Error: Agent definition must include location attribute.")

        agent.password = self._getAttribute(node, 'password')
        if agent.password is not None and len(agent.password) == 0:
            agent.password = None

        for child in node.iterchildren():
            child_nodeName = split_ns(child.tag)[1]
            if child_nodeName == 'Monitor':
                if not self._getBooleanAttribute(child, "enabled"):
                    logging.info('Monitor  "%s" is deactivated.' % self._getAttribute(child, "class"))
                    continue

                if child.get("platform") is not None:
                    validOS = [x for x in self._getAttribute(child, "platform").split(",") if x == sys.platform]
                    if not validOS:
                        logging.debug('Monitor "%s" for %s is not supported on this platform.' %
                                     (self._getAttribute(child, "class"), self._getAttribute(child, "platform")))
                        continue

                agent.append(self.HandleMonitor(child, agent))
                logging.info('Monitor "%s" attached.' % self._getAttribute(child, "class"))

            elif child_nodeName == 'PythonPath':
                p = self.HandlePythonPath(child, agent)
                agent.append(p)

            elif child_nodeName == 'Import':
                p = self.HandleImport(child, agent)
                agent.append(p)

            else:
                raise PeachException("Found unexpected child of Agent element")

        ## A remote publisher might be in play
        #if len(agent) < 1:
        #	raise Exception("Agent must have at least one Monitor child.")

        return agent

    def HandleMonitor(self, node, parent):
        """
        Handle Monitor element
        """

        name = self._getAttribute(node, 'name')

        monitor = Monitor(name, parent)

        # class

        if node.get("class") is None:
            raise PeachException("Monitor element missing class attribute")

        monitor.classStr = self._getAttribute(node, "class")

        # children

        for child in node.iterchildren():
            child_nodeName = split_ns(child.tag)[1]
            if not child_nodeName == 'Param':
                raise PeachException(PeachStr("Unexpected Monitor child node: %s" % child_nodeName))

            param = self.HandleParam(child, parent)
            monitor.params[param.name] = param.defaultValue

        return monitor


    # Handlers for Test ###################################################

    def HandleTest(self, node, parent):
        # name

        name = self._getAttribute(node, 'name')

        # ref

        if node.get('ref') is not None:
            if name is None or len(name) == 0:
                name = Element.getUniqueName()

            obj = self.GetRef(self._getAttribute(node, 'ref'), None, 'tests')

            test = obj.copy(parent)
            test.name = name
            test.ref = self._getAttribute(node, 'ref')

        else:
            test = Test(name, parent)

        #test.node = node
        if node.get('description') is not None:
            test.description = self._getAttribute(node, 'description')

        test.mutators = None

        for child in node.iterchildren():
            child_nodeName = split_ns(child.tag)[1]
            if child_nodeName == 'Publisher':
                if not test.publishers:
                    test.publishers = []

                pub = self.HandlePublisher(child, test)
                test.publishers.append(pub)
                test.append(pub.domPublisher)

            elif child_nodeName == 'Agent':
                if child.get('ref') is not None:
                    agent = self.GetRef(self._getAttribute(child, 'ref'), None, 'agents')

                if agent is None:
                    raise PeachException(PeachStr("Unable to locate agent %s specified in Test element %s" % (
                        self._getAttribute(child, 'ref'), name)))

                test.append(agent.copy(test))

            elif child_nodeName == 'StateMachine' or child_nodeName == 'StateModel':
                if child.get('ref') is None:
                    raise PeachException("StateMachine element in Test declaration must have a ref attribute.")

                stateMachine = self.GetRef(self._getAttribute(child, 'ref'), None, 'children')
                if stateMachine is None:
                    raise PeachException("Unable to locate StateMachine [%s] specified in Test [%s]" % (
                        str(self._getAttribute(child, 'ref')), name))

                #print "*** StateMachine: ", stateMachine
                test.stateMachine = stateMachine.copy(test)
                test.append(test.stateMachine)

                path = None
                for child2 in child.iterchildren():
                    child2_nodeName = split_ns(child.tag)[1]
                    if child2_nodeName == 'Path':
                        path = self.HandlePath(child2, test.stateMachine)
                        test.stateMachine.append(path)

                    elif child2_nodeName == 'Stop':
                        if path is None:
                            raise PeachException("Stop element must be used after a Path element.")

                        path.stop = True
                        # Do not accept anything after Stop element ;)
                        break

                    elif child2_nodeName == 'Strategy':
                        strategy = self.HandleStrategy(child2, test.stateMachine)
                        test.stateMachine.append(strategy)

                    else:
                        raise PeachException("Unexpected node %s" % child2_nodeName)

            elif child_nodeName == 'Mutator':
                if child.get('class') is None:
                    raise PeachException("Mutator element does not have required class attribute")

                mutator = Mutator(self._getAttribute(child, 'class'), test)

                if not test.mutators:
                    test.mutators = Mutators(None, test)

                mutator.parent = test.mutators
                test.mutators.append(mutator)

            elif child_nodeName == 'Include' or child_nodeName == 'Exclude':
                self._HandleIncludeExclude(child, test)

            elif child_nodeName == 'Strategy':
                if self._getBooleanAttribute(child, "enabled"):
                    test.mutator = self.HandleFuzzingStrategy(child, test)
            else:
                raise PeachException("Found unexpected child of Test element")

        if test.mutator is None:
            test.mutator = MutationStrategy.DefaultStrategy(None, test)

        if test.mutators is None:
            # Add the default mutators instead of erroring out
            test.mutators = self._locateDefaultMutators()

        if test.template is None and test.stateMachine is None:
            raise PeachException(PeachStr("Test %s does not have a Template or StateMachine defined" % name))

        if len(test.publishers) == 0:
            raise PeachException(PeachStr("Test %s does not have a publisher defined!" % name))

        if test.template is not None and test.stateMachine is not None:
            raise PeachException(PeachStr(
                "Test %s has both a Template and StateMachine defined.  Only one of them can be defined at a time." % name))

        # Now mark Mutatable(being fuzzed) elements
        # instructing on inclusions/exlusions
        test.markMutatableElements(node)

        return test

    def HandleFuzzingStrategy(self, node, parent):
        """
        Handle parsing <Strategy> element that is a child of
        <Test>
        """

        # name

        name = self._getAttribute(node, 'name')

        # class

        cls = self._getAttribute(node, 'class')

        # TODO why does this not work?
        #return globals()["PeachXml_" + cls](node, parent)

        exec("strategy = PeachXml_%s(node, parent)" % cls)
        return strategy

    def HandlePath(self, node, parent):
        if node.get('ref') is None:
            raise PeachException("Parser: Test::StateModel::Path missing ref attribute")

        stateMachine = parent
        ref = self._getAttribute(node, 'ref')
        state = self.GetRef(ref, stateMachine, None)

        path = Path(ref, parent)

        for child in node.iterchildren():
            child_nodeName = split_ns(child.tag)[1]
            if child_nodeName == 'Include' or child_nodeName == 'Exclude':
                self._HandleIncludeExclude(child, state)

            elif child_nodeName == 'Data':
            # Handle Data elements at Test-level
                data = self.HandleData(child, path)
                #data.node = child

                actions = [child for child in state if child.elementType == 'action']
                for action in actions:
                    cracker = DataCracker(action.getRoot())
                    cracker.optmizeModelForCracking(action.template)
                    action.template.setDefaults(data, self.dontCrack)

            elif child_nodeName not in ['Mutator']:
                raise PeachException("Found unexpected child of Path element")

        return path

    def _HandleIncludeExclude(self, node, parent):
        ref = None

        isExclude = split_ns(node.tag)[1] != 'Exclude'

        if node.get('ref') is not None and node.get('xpath') is not None:
            raise PeachException("Include/Exclude node can only have one of either ref or xpath attributes.")

        if node.get('xpath') is not None:
            xpath = self._getAttribute(node, 'xpath')
        else:
            ref = None
            if node.get('ref') is not None:
                ref = self._getAttribute(node, 'ref').replace('.', '/')

            xpath = self._retrieveXPath(ref, node.getparent())

        test = self._getTest(parent)
        test.mutatables.append([isExclude, xpath])

    def _getTest(self, element):
        if element is None:
            return None

        if element.elementType == 'test':
            return element

        return self._getTest(element.parent)

    def _retrieveXPath(self, xpath, node):
        if split_ns(node.tag)[1] == 'Test':
            if xpath is None:
                return "//*"
            else:
                return "//%s" % xpath

        if node.get('ref') is None:
            raise PeachException("All upper elements must have a ref attribute. Cannot retrieve relative XPath.")

        ref = self._getAttribute(node, 'ref')

        if xpath is not None:
            xpath = ref + "/" + xpath
        else:
            xpath = ref

        return self._retrieveXPath(xpath, node.getparent())

    def HandleStrategy(self, node, parent):
        # class
        if node.get("class") is None:
            raise PeachException("Strategy element missing class attribute")

        classStr = self._getAttribute(node, "class")
        strategy = Strategy(classStr, parent)

        # children
        for child in node.iterchildren():
            child_nodeName = split_ns(child.tag)[1]
            if not child_nodeName == 'Param':
                raise PeachException(PeachStr("Unexpected Strategy child node: %s" % child_nodeName))

            param = self.HandleParam(child, parent)
            strategy.params[param.name] = eval(param.defaultValue)

        return strategy

    def _locateDefaultMutators(self, obj=None):
        """
        Look for a default set of mutators.  We will follow this
        search pattern:

        1. Look at our self (context) level
        2. Look at our imported namespaces
        3. Recerse into namespaces (sub namespaces, etc)

        This means a <Mutators> element in the top level XML file will
        get precidence over the defaults.xml file which is included into
        a namepsace.
        """

        if obj is None:
            obj = self.context

        # First look at us
        if obj.mutators is not None:
            return obj.mutators

        # Now look at namespaces
        for n in obj:
            if n.elementType == 'namespace':
                if n.ns.mutators is not None:
                    return n.ns.mutators

        # Now look inside namespace
        for n in obj:
            if n.elementType == 'namespace':
                m = self._locateDefaultMutators(n.ns)
                if m is not None:
                    return m

        # YUCK
        raise PeachException("Could not locate default set of Mutators to use.  Please fix this!")


    def HandleRun(self, node, parent):
        haveLogger = False

        # name

        name = None
        if node.get('name') is not None:
            name = self._getAttribute(node, 'name')

        run = Run(name, parent)
        #run.node = node
        run.description = self._getAttribute(node, 'description')

        if node.get('waitTime') is not None:
            run.waitTime = float(self._getAttribute(node, 'waitTime'))

        for child in node.iterchildren():
            child_nodeName = split_ns(child.tag)[1]
            if child_nodeName == 'Test':
                test = None
                if child.get('ref') is not None:
                    test = self.GetRef(self._getAttribute(child, 'ref'), None, 'tests')

                if test is None:
                    raise PeachException(
                        PeachStr("Unable to locate tests %s specified in Run element %s" % (testsName, name)))

                test = test.copy(run)
                run.tests.append(test)
                run.append(test)

            elif child_nodeName == 'Logger':
                if not self._getBooleanAttribute(child, "enabled"):
                    continue
                loggerName = self._getAttribute(child, "class")
                try:
                    logger = self.HandleLogger(child, run)
                except Exception as msg:
                    logging.warning(highlight.warning("Unable to attach %s: %s" % (loggerName, msg)))
                    continue
                logging.info('Logger "%s" attached.' % loggerName)
                run.append(logger)
                haveLogger = True

            else:
                raise PeachException("Found unexpected child of Run element")

        if len(run.tests) == 0:
            raise PeachException(PeachStr("Run %s does not have any tests defined!" % name))

        if not haveLogger:
            logging.warning("Run '%s' does not have logging configured!" % name)

        return run


    def HandlePublisher(self, node, parent):
        params = []

        publisher = Publisher()

        # class

        if node.get("class") is None:
            raise PeachException("Publisher element missing class attribute")

        if len(node.get("class")) == 0:
            raise PeachException("Publisher class attribute is empty")

        publisher.classStr = publisherClass = self._getAttribute(node, "class")

        if node.get("name") is not None:
            publisher.name = self._getAttribute(node, "name")

        # children

        for child in node.iterchildren():
            child_nodeName = split_ns(child.tag)[1]
            if child.get("name") is None:
                raise PeachException("Publisher element missing name attribute")

            if child.get("value") is None:
                raise PeachException("Publisher element missing value attribute")

            if child.get("valueType") is None:
                valueType = "string"
            else:
                valueType = self._getAttribute(child, "valueType")

            name = self._getAttribute(child, "name")
            value = self._getAttribute(child, "value")

            param = Param(publisher)
            param.name = name
            param.defaultValue = PeachStr(value)
            param.valueType = valueType

            if valueType == 'string':
                # create a literal out of a string value
                value = "'''" + value + "'''"
            elif valueType == 'hex':
                ret = ''

                valueLen = len(value) + 1
                while valueLen > len(value):
                    valueLen = len(value)

                    for i in range(len(self._regsHex)):
                        match = self._regsHex[i].search(value)
                        if match is not None:
                            while match is not None:
                                ret += '\\x' + match.group(2)
                                value = self._regsHex[i].sub('', value)
                                match = self._regsHex[i].search(value)
                            break

                value = "'" + ret + "'"

            publisher.append(param)
            params.append([name, value])

        code = "PeachXml_%s(%s)" % (publisherClass, ",".join(str(v) for _,v in params))

        pub = eval(code, globals(), locals())

        pub.domPublisher = publisher
        pub.parent = parent
        return pub


    def HandleLogger(self, node, parent):
        params = {}
        logger = Logger(parent)
        #logger.node = node

        # class

        if node.get("class") is None:
            raise PeachException("Logger element missing class attribute")

        logger.classStr = self._getAttribute(node, "class")

        # children

        for child in node.iterchildren():
            child_nodeName = split_ns(child.tag)[1]
            if child.get("name") is None:
                raise PeachException("Logger element missing name attribute")

            if child.get("value") is None:
                raise PeachException("Logger element missing value attribute")

            if child.get("valueType") is None:
                valueType = "string"
            else:
                valueType = self._getAttribute(child, "valueType")

            name = self._getAttribute(child, "name")
            value = self._getAttribute(child, "value")

            param = Param(logger)
            param.name = name
            param.defaultValue = PeachStr(value)
            param.valueType = valueType

            if valueType == 'string':
                # create a literal out of a string value
                value = "'''" + value + "'''"
            elif valueType == 'hex':
                ret = ''

                valueLen = len(value) + 1
                while valueLen > len(value):
                    valueLen = len(value)

                    for i in range(len(self._regsHex)):
                        match = self._regsHex[i].search(value)
                        if match is not None:
                            while match is not None:
                                ret += '\\x' + match.group(2)
                                value = self._regsHex[i].sub('', value)
                                match = self._regsHex[i].search(value)
                            break

                value = "'" + ret + "'"

            #print "LoggeR: Adding %s:%s" % (PeachStr(name),PeachStr(value))
            logger.append(param)
            params[PeachStr(name)] = PeachStr(value)

        code = "PeachXml_" + logger.classStr + '(params)'
        pub = eval(code)
        pub.domLogger = logger
        return pub


    def HandleStateMachine(self, node, parent):
        if node.get("name") is None:
            raise PeachException("Parser: StateMachine missing name attribute")

        if node.get('initialState') is None:
            raise PeachException("Parser: StateMachine missing initialState attribute")

        stateMachine = StateMachine(self._getAttribute(node, "name"), parent)
        stateMachine.initialState = self._getAttribute(node, 'initialState')
        stateMachine.onLoad = self._getAttribute(node, 'onLoad')

        for child in node.iterchildren():
            child_nodeName = split_ns(child.tag)[1]
            if child_nodeName == 'State':
                state = self.HandleState(child, stateMachine)
                stateMachine.append(state)
            else:
                raise PeachException("Parser: StateMachine has unknown child [%s]" % PeachStr(child_nodeName))

        return stateMachine

    def HandleState(self, node, parent):
        if node.get("name") is None:
            raise PeachException("Parser: State missing name attribute")

        state = State(self._getAttribute(node, 'name'), parent)
        state.onEnter = self._getAttribute(node, 'onEnter')
        state.onExit = self._getAttribute(node, 'onExit')

        foundAction = False

        for child in node.iterchildren():
            child_nodeName = split_ns(child.tag)[1]
            if child_nodeName == 'Action':
                action = self.HandleAction(child, state)
                if action.name in state:
                    raise PeachException("Found duplicate Action name [%s]!" % action.name)

                state.append(action)
                foundAction = True

            elif child_nodeName == 'Choice':
                choice = self.HandleStateChoice(child, state)
                state.append(choice)

            else:
                raise PeachException("Parser: State has unknown child [%s]" % PeachStr(child_nodeName))

        if not foundAction:
            raise PeachException("State [%s] has no actions" % state.name)

        return state

    def HandleStateChoice(self, node, parent):
        choice = StateChoice(parent)

        for child in node.iterchildren():
            choice.append(self.HandleStateChoiceAction(child, node))

        return choice

    def HandleStateChoiceAction(self, node, parent):
        if node.get("ref") is None:
            raise PeachException("Parser: State::Choice::Action missing ref attribute")

        if node.get("type") is None:
            raise PeachException("Parser: State::Choice::Action missing type attribute")

        ref = self._getAttribute(node, "ref")
        type = self._getAttribute(node, "type")

        return StateChoiceAction(ref, type, parent)

    def HandleAction(self, node, parent):
        if node.get("type") is None:
            raise PeachException("Parser: Action missing 'type' attribute")

        action = Action(self._getAttribute(node, 'name'), parent)
        action.type = self._getAttribute(node, 'type')

        if not action.type in ['input', 'output', 'call', 'setprop', 'getprop', 'changeState',
                               'slurp', 'connect', 'close', 'accept', 'start', 'stop', 'wait', 'open']:
            raise PeachException("Parser: Action type attribute is not valid [%s]." % action.type)

        action.onStart = self._getAttribute(node, 'onStart')
        action.onComplete = self._getAttribute(node, 'onComplete')
        action.when = self._getAttribute(node, 'when')
        action.ref = self._getAttribute(node, 'ref')
        action.setXpath = self._getAttribute(node, 'setXpath')
        action.valueXpath = self._getAttribute(node, 'valueXpath')
        action.valueLiteral = self._getAttribute(node, 'value')
        action.method = self._getAttribute(node, 'method')
        action.property = self._getAttribute(node, 'property')
        action.publisher = self._getAttribute(node, 'publisher')

        # Quick hack to get open support.  open and connect are same.
        if action.type == 'open':
            action.type = 'connect'

        if (action.setXpath or action.valueXpath or action.valueLiteral) and (
            action.type != 'slurp' and action.type != 'wait'):
            raise PeachException("Parser: Invalid attribute for Action were type != 'slurp'")

        if action.method is not None and action.type != 'call':
            raise PeachException("Parser: Method attribute on an Action only available when type is 'call'.")

        if action.property is not None and not action.type in ['setprop', 'getprop']:
            raise PeachException(
                "Parser: Property attribute on an Action only available when type is 'setprop' or 'getprop'.")

        for child in node.iterchildren():
            child_nodeName = split_ns(child.tag)[1]
            if child_nodeName == 'Param':
                if not action.type in ['call', 'setprop', 'getprop']:
                    raise PeachException("Parser: Param is an invalid child of Action for this Action type")

                param = self.HandleActionParam(child, action)

                if param.name in action:
                    raise PeachException(
                        "Error, duplicate Param name [%s] found in Action [%s]." % (param.name, action.name))

                action.append(param)

            elif child_nodeName == 'Template' or child_nodeName == 'DataModel':
                if action.type not in ['input', 'output', 'getprop']:
                    raise PeachException("Parser: DataModel is an invalid child of Action for this Action type")

                #if child.get('ref') is None:
                #	raise PeachException("Parser: When DataModel is a child of Action it must have the ref attribute.")

                if action.template is not None:
                    raise PeachException("Error, action [%s] already has a DataModel specified." % action.name)

                obj = self.HandleTemplate(child, action)
                action.template = obj
                action.append(obj)

            elif child_nodeName == 'Data':
                if not (action.type == 'input' or action.type == 'output'):
                    raise PeachException("Parser: Data is an invalid child of Action for this Action type")

                if action.data is not None:
                    raise PeachException("Error, action [%s] already has a Data element specified." % action.name)

                data = self.HandleData(child, action)
                action.data = data

            elif child_nodeName == 'Result':
                if not action.type in ['call']:
                    raise PeachException("Parser: Result is an invalid child of Action of type 'call'.")

                result = self.HandleActionResult(child, action)

                if result.name in action:
                    raise PeachException(
                        "Error, duplicate Result name [%s] found in Action [%s]." % (param.name, action.name))

                action.append(result)

            else:
                raise PeachException("Parser: State has unknown child [%s]" % PeachStr(child_nodeName))

        if action.template is not None and action.data is not None:
            cracker = DataCracker(action.getRoot())
            cracker.optmizeModelForCracking(action.template)

            # Somehow data not getting parent.  Force setting
            action.data.parent = action

            action.template.setDefaults(action.data, self.dontCrack, True)

        # Verify action has a DataModel if needed
        if action.type in ['input', 'output']:
            if action.template is None:
                raise PeachException("Parser: Action [%s] of type [%s] must have a DataModel child element." % (
                    action.name, action.type))

        # Verify that setprop has a parameter
        if action.type == 'setprop':
            foundActionParam = False
            for c in action:
                if isinstance(c, ActionParam):
                    foundActionParam = True

            if not foundActionParam:
                raise PeachException(
                    "Parser: Action [%s] of type [%s] must have a Param child element." % (action.name, action.type))

        return action

    def HandleActionParam(self, node, parent):
        if node.get("type") is None:
            raise PeachException("Parser: ActionParam missing required type attribute")

        param = ActionParam(self._getAttribute(node, 'name'), parent)
        param.type = self._getAttribute(node, 'type')

        if not param.type in ['in', 'out', 'inout', 'return']:
            raise PeachException(
                "Parser: ActionParam type attribute is not valid [%s].  Must be one of: in, out, or inout" % param.type)

        for child in node.iterchildren():
            child_nodeName = split_ns(child.tag)[1]
            if child_nodeName == 'Template' or child_nodeName == 'DataModel':
                #if child.get('ref') is None:
                #	raise PeachException("Parser: When Template is a child of ActionParam it must have the ref attribute.")

                obj = self.HandleTemplate(child, param)
                param.template = obj
                param.append(obj)

            elif child_nodeName == 'Data':
                if not (param.type == 'in' or param.type == 'inout'):
                    raise PeachException(
                        "Parser: Data is an invalid child of ActionParam for this type [%s]" % param.type)

                data = self.HandleData(child, param)
                data.parent = param
                param.data = data

            else:
                raise PeachException("Parser: ActionParam has unknown child [%s]" % PeachStr(child_nodeName))

        if param.template is not None and param.data is not None:
            cracker = DataCracker(param.template.getRoot())
            cracker.optmizeModelForCracking(param.template)
            param.template.setDefaults(param.data, self.dontCrack, True)

        # Verify param has data model
        if param.template is None:
            raise PeachException("Parser: Action Param must have DataModel as child element.")

        return param

    def HandleActionResult(self, node, parent):
        result = ActionResult(self._getAttribute(node, 'name'), parent)

        for child in node.iterchildren():
            child_nodeName = split_ns(child.tag)[1]
            if child_nodeName == 'Template' or child_nodeName == 'DataModel':
                if child.get('ref') is None:
                    raise PeachException(
                        "Parser: When Template is a child of ActionParam it must have the ref attribute.")

                obj = self.HandleTemplate(child, result)
                result.template = obj
                result.append(obj)

            else:
                raise PeachException("Parser: Action Result has unknown child [%s]" % PeachStr(child_nodeName))

        # Verify param has data model
        if result.template is None:
            raise PeachException("Parser: Action Result must have DataModel as child element.")

        return result

    def _HandleValueType(self, value, valueType):
        """
        Handle types: string, literal, and hex
        """

        if not value or not valueType:
            return None

        if valueType == 'literal':
            return PeachStr(eval(value))

        return PeachStr(value)

    def _HandleValueTypeString(self, value, valueType):
        """
        Handle types: string, literal, and hex
        """

        if not value or not valueType:
            return None

        if valueType == 'literal':
            return eval(value)

        return value


    def HandleParam(self, node, parent):
        param = Param(parent)

        if node.get("name") is None:
            raise PeachException(
                "Parser: Param element missing name attribute.  Parent is [{}]".format(split_ns(node.getparent().tag)[1]))

        if node.get("value") is None:
            raise PeachException("Parser: Param element missing value attribute.  Name is [{}].  Parent is [{}]".format(node.get("name"), split_ns(node.getparent().tag)[1]))

        if node.get("valueType") is None:
            valueType = "string"
        else:
            valueType = self._getAttribute(node, "valueType")

        name = self._getAttribute(node, "name")
        value = self._getAttribute(node, "value")

        if valueType == 'string':
            # create a literal out of a string value
            try:
                value = "'''" + value + "'''"
            except TypeError:
                raise PeachException("Parser: Failed converting param value to string.  Name is [{}].  Value is [{}].".format(name, value))

        elif valueType == 'hex':
            ret = ''

            valueLen = len(value) + 1
            while valueLen > len(value):
                valueLen = len(value)

                for i in range(len(self._regsHex)):
                    match = self._regsHex[i].search(value)
                    if match is not None:
                        while match is not None:
                            ret += '\\x' + match.group(2)
                            value = self._regsHex[i].sub('', value)
                            match = self._regsHex[i].search(value)
                        break

            value = "'" + ret + "'"

        param.name = name
        param.defaultValue = PeachStr(value)
        param.valueType = valueType

        return param

    def HandlePythonPath(self, node, parent):
        if node.get('path') is None:
            raise PeachException("PythonPath element did not have a path attribute!")

        p = PythonPath()
        p.name = self._getAttribute(node, 'path')

        return p

    def HandleImport(self, node, parent):
        # Import module

        if node.get('import') is None:
            raise PeachException("HandleImport: Import element did not have import attribute!")

        i = Element()
        i.elementType = 'import'
        i.importStr = self._getAttribute(node, 'import')
        if node.get('from') is not None:
            i.fromStr = self._getAttribute(node, 'from')
        else:
            i.fromStr = None

        return i

    def HandleHint(self, node, parent):
        if node.get('name') is None or node.get('value') is None:
            raise PeachException("Error: Found Hint element that didn't have both name and value attributes.")

        hint = Hint(self._getAttribute(node, 'name'), parent)
        hint.value = self._getAttribute(node, 'value')
        parent.hints.append(hint)

        return hint

from Peach.Analyzers import *

