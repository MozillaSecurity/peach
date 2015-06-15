# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
import random
import hashlib
import logging

from Peach.Engine.engine import Engine
from Peach.mutatestrategies import *
from Peach.Engine.incoming import DataCracker
from Peach.Engine.common import *


class _RandomMutator(object):
    name = "Random"
    changedName = "N/A"


class RandomMutationStrategy(MutationStrategy):
    """
    This mutation strategy will randomly select N fields from a data model to
    fuzz on each test case.

    Note: This strategy does not affect the state model. First test case will
    not be modified.
    """

    def __init__(self, node, parent):
        MutationStrategy.__init__(self, node, parent)
        if node is not None and node.get("seed") is not None:
            Engine.context.SEED = RandomMutationStrategy.SEED = node.get("seed")
        else:
            RandomMutationStrategy.SEED = Engine.context.SEED
        self.switchCount = 200
        if node is not None and node.get("switchCount") is not None:
            self.switchCount = int(node.get("switchCount"))
        self.iterationCount = 0
        self.multipleFiles = False
        self.isFinite = False
        self._n = 7
        if node is not None and node.get("maxFieldsToMutate") is not None:
            self._n = int(node.get("maxFieldsToMutate"))
        self._dataModels = {}
        self._fieldMutators = {}
        self._isFirstTestCase = True
        self._dataModelToChange = None
        self._random = random.Random()
        self._random.seed(hashlib.sha512(str(RandomMutationStrategy.SEED) +
                                         str(self.iterationCount)).digest())
        self._mutator = _RandomMutator()

    def next(self):
        self.iterationCount += 1
        self._random.seed(hashlib.sha512(str(RandomMutationStrategy.SEED) +
                                         str(self.iterationCount)).digest())

    def getCount(self):
        """
        Return the number of test cases.
        """
        return None

    def _getNodeCount(self, node):
        """
        Return the number of DataElements that are children of node.
        """
        return len(node.getAllChildDataElements())

    def currentMutator(self):
        """
        Return the current Mutator in use.
        """
        return self._mutator

    def onTestCaseStarting(self, test, count, stateEngine):
        """
        Called as we start a test case

        @type	test: Test instance
        @param	test: Current test being run
        @type	count: int
        @param	count: Current test #
        @type	stateEngine: StateEngine instance
        @param	stateEngine: StateEngine instance in use
        """
        if not self._isFirstTestCase:
            ## Select the data model to change
            self._dataModelToChange = \
                self._random.choice(self._dataModels.keys())

    def onTestCaseFinished(self, test, count, stateEngine):
        """
        Called as we exit a test case

        @type	test: Test instance
        @param	test: Current test being run
        @type	count: int
        @param	count: Current test #
        @type	stateEngine: StateEngine instance
        @param	stateEngine: StateEngine instance in use
        """
        self._isFirstTestCase = False
        self._dataModelToChange = None

    def GetRef(self, str, parent=None, childAttr='templates'):
        """
        Get the object indicated by ref. Currently the object must have been
        defined prior to this point in the XML.
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
                # Check parent, walk up from current parent to top level
                # parent checking at each level.
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
                    elif hasattr(parent, childAttr) and \
                            hasattr(getattr(parent, childAttr), name):
                        baseObj = getattr(getattr(parent, childAttr), name)
                        found = True
                    else:
                        parent = parent.parent
            # Check base obj
            elif hasattr(baseObj, name):
                baseObj = getattr(baseObj, name)
                found = True
            # Check childAttr
            elif hasattr(baseObj, childAttr):
                obj = getattr(baseObj, childAttr)
                if hasattr(obj, name):
                    baseObj = getattr(obj, name)
                    found = True
            else:
                raise PeachException("Could not resolve ref %s" % origStr)
            # Check childAttr
            if found is False and hasattr(baseObj, childAttr):
                obj = getattr(baseObj, childAttr)
                if hasattr(obj, name):
                    baseObj = getattr(obj, name)
                    found = True
            # Check across namespaces if we can't find it in ours
            if isTopName and found is False:
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
        # Namespaces are stuffed under this variable if we have it we should
        # be it.
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

    def onDataModelGetValue(self, action, dataModel):
        """
        Called before getting a value from a data model

        @type	action: Action
        @param	action: Action we are starting
        @type	dataModel: Template
        @param	dataModel: Data model we are using
        """
        if action.data is not None and action.data.multipleFiles \
                and action.data.switchCount is not None:
            self.switchCount = action.data.switchCount
        if action.data is not None and action.data.multipleFiles \
                and self.iterationCount % self.switchCount == 0:
            self.context = action.getRoot()
            # If a file fails to parse, don't exit the run, instead re-crack
            # until we find a working file.
            while True:
                action.data.gotoRandomFile()
                # Locate fresh copy of template with no data
                obj = self.GetRef(action.template.ref)
                cracker = DataCracker(obj.getRoot())
                cracker.optmizeModelForCracking(obj)
                template = obj.copy(action)
                template.ref = action.template.ref
                template.parent = action
                template.name = action.template.name
                # Switch any references to old name
                oldName = template.ref
                for relation in template._genRelationsInDataModelFromHere():
                    if relation.of == oldName:
                        relation.of = template.name
                    elif relation.From == oldName:
                        relation.From = template.name
                # Crack file
                try:
                    template.setDefaults(action.data, False, True)
                    break
                except Exception as e:
                    logging.warning(e)
            # Cache default values
            action.template = template
            template.getValue()
            # Re-create state engine copy. We do this to avoid have
            # optmizeModelForCracking called over and over.
            if hasattr(action, "origionalTemplate"):
                #delattr(action, "origionalTemplate")
                action.origionalTemplate = action.template
                action.origionalTemplate.BuildRelationCache()
                action.origionalTemplate.resetDataModel()
                action.origionalTemplate.getValue()
                action.template = action.template.copy(action)
            # Regenerate mutator state
            self._isFirstTestCase = True
            self._dataModels = {}
            self._fieldMutators = {}
        if self._isFirstTestCase:
            fullName = dataModel.getFullname()
            if fullName not in self._dataModels:
                self._dataModels[fullName] = self._getNodeCount(dataModel)
                nodes = dataModel.getAllChildDataElements()
                nodes.append(dataModel)
                nonMutableNodes = []
                for node in nodes:
                    if not node.isMutable:
                        nonMutableNodes.append(node)
                    mutators = []
                    self._fieldMutators[node.getFullname()] = mutators
                    for m in Engine.context.mutators:
                        if m.supportedDataElement(node):
                            # Need to create new instance from class
                            for i in range(m.weight ** 4):
                                mutators.append(m(Engine.context, node))
                for node in nonMutableNodes:
                    nodes.remove(node)
                nonMutableNodes = None
            return
        else:
            # Is this data model we are changing?
            if dataModel.getFullname() != self._dataModelToChange:
                return
            # Select fields to modify
            nodes = dataModel.getAllChildDataElements()
            nodes.append(dataModel)
            nodesToRemove = []
            # Remove non-mutable fields
            for node in nodes:
                if not node.isMutable:
                    nodesToRemove.append(node)
            for node in nodesToRemove:
                nodes.remove(node)
            #for node in nodes:
            #    if not self._fieldMutators.has_key(node.getFullname()) or len(self._fieldMutators[node.getFullname()]) == 0:
            #        raise Exception("Found element with no mutations!")
            #logging.info("Preparing testcase for file {}".format(action.data.fileName))
            # Select nodes we will modify
            logging.info("Performing mutation.")
            if len(nodes) <= self._n:
                fields = nodes
                maxN = self._n - len(fields)
                if maxN <= 0:
                    maxN = self._n / 2
                for _ in range(self._random.randint(1, maxN)):
                    # Now perform mutations on fields
                    if len(fields) < 3:
                        sampleset = fields
                    else:
                        sampleset = self._random.sample(
                            fields, self._random.randint(1, len(fields)))
                    for node in sampleset:
                        try:
                            mutator = self._random.choice(self._fieldMutators[node.getFullname()])
                            fullName = node.getFullnameInDataModel()[len(dataModel.name) + 1:]
                            logging.debug("%s => %s" % (mutator.name, fullName or "N/A"))
                            # Since we are applying multiple mutations sometimes a mutation will fail.
                            # We should ignore those failures.
                            try:
                                mutator.randomMutation(node, self._random)
                            except:
                                pass
                        except:
                            pass
            else:
                fields = self._random.sample(nodes, self._random.randint(1, self._n))
                # Now perform mutations on fields
                for node in fields:
                    try:
                        mutator = self._random.choice(self._fieldMutators[node.getFullname()])
                        fullName = node.getFullnameInDataModel()[len(dataModel.name) + 1:]
                        logging.debug("%s => %s" % (mutator.name, fullName or "N/A"))
                        # Since we are applying multiple mutations sometimes a
                        # mutation will fail. We should ignore those failures.
                        try:
                            mutator.randomMutation(node, self._random)
                        except:
                            pass
                    except:
                        pass
            logging.info("Mutation finished.")

#MutationStrategy.DefaultStrategy = RandomMutationStrategy
