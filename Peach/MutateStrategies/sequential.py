# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
import random

from Peach.mutatestrategies import *
from Peach.mutator import *
from Peach.Engine.incoming import DataCracker


class _Unknown(object):
    name = "N/A"
    changedName = "N/A"


class _RandomMutator(object):
    name = "N/A"
    changedName = "N/A"


class SequentialMutationStrategy(MutationStrategy):
    """
    Perform a sequential mutation strategy.

    Note: This strategy does not affect the state model. First test case will
    not be modified.
    """

    def __init__(self, node, parent):
        MutationStrategy.__init__(self, node, parent)
        self.isFinite = True
        self._count = None
        #: Data models (by fullname)
        self._dataModels = []
        #: Data fields (K is data model fullname, V is array of data names)
        self._dataModelFields = {}
        #: K is field fullname, V is array of mutators, position 0 is current
        self._fieldMutators = {}
        self._isFirstTestCase = True
        #: Data model selected for change
        self._dataModelIndex = 0
        #: Current data model field
        self._fieldIndex = 0
        #: Current mutator for field
        self._mutatorIndex = 0

    def getCount(self):
        """
        Return the number of test cases
        """
        if self._isFirstTestCase:
            return None
        if self._count is None:
            cnt = 0
            for mutators in self._fieldMutators.values():
                for m in mutators:
                    c = m.getCount()
                    if c is None:
                        raise Exception("Count was null from {!r}".format(m))
                    cnt += c
            self._count = cnt
            return self._count
        return self._count

    def next(self):
        if len(self._dataModels) == 0:
            raise PeachException("Error: Peach couldn't find any DataModels "
                                 "with elements to fuzz!")
        dataModelName = self._dataModels[self._dataModelIndex]
        while self._fieldIndex >= len(self._dataModelFields[dataModelName]):
            self._fieldIndex = 0
            self._dataModelIndex += 1
            dataModelCount = len(self._dataModels)
            if self._dataModelIndex >= dataModelCount:
                raise MutatorCompleted()
            else:
                dataModelName = self._dataModels[self._dataModelIndex]
        fieldName = self._dataModelFields[dataModelName][self._fieldIndex]
        # If this is the first test case, don't next the mutator
        if self._isFirstTestCase:
            self._isFirstTestCase = False
        else:
            try:
                mutator = self._fieldMutators[fieldName][self._mutatorIndex]
                mutator.next()
                return
            except MutatorCompleted:
                pass
            self._mutatorIndex += 1
        # Fall through to here and move to next available field/mutator
        while fieldName is None or \
                self._mutatorIndex >= len(self._fieldMutators[fieldName]):
            self._mutatorIndex = 0
            self._fieldIndex += 1
            fieldCount = len(self._dataModelFields[dataModelName])
            if self._fieldIndex >= fieldCount:
                self._fieldIndex = 0
                self._dataModelIndex += 1
                dataModelCount = len(self._dataModels)
                if self._dataModelIndex >= dataModelCount:
                    raise MutatorCompleted()
                else:
                    dataModelName = self._dataModels[self._dataModelIndex]
            fieldName = None
            try:
                fieldName = \
                    self._dataModelFields[dataModelName][self._fieldIndex]
            except:
                pass

    def currentMutator(self):
        """
        Return the current Mutator in use.
        """
        if self._isFirstTestCase:
            return _Unknown()
        dataModelName = self._dataModels[self._dataModelIndex]
        fieldName = self._dataModelFields[dataModelName][self._fieldIndex]
        return self._fieldMutators[fieldName][self._mutatorIndex]

    def onDataModelGetValue(self, action, dataModel):
        """
        Called before getting a value from a data model

        @type	action: Action
        @param	action: Action we are starting
        @type	dataModel: Template
        @param	dataModel: Data model we are using
        """
        # On first test case lets just figure out which data models and fields
        # we will be mutating.
        if self._isFirstTestCase:
            fullName = dataModel.getFullname()
            if fullName not in self._dataModels:
                self._dataModels.append(fullName)
                self._dataModelFields[fullName] = []
                nodes = dataModel.getAllChildDataElements()
                nodes.append(dataModel)
                for node in nodes:
                    if node.isMutable:
                        self._dataModelFields[fullName].append(node.getFullname())
                        mutators = self._fieldMutators[node.getFullname()] = []
                        # We should also populate the mutators here
                        for m in Engine.context.mutators:
                            if m.supportedDataElement(node):
                                # Need to create new instance from class
                                mutators.append(m(Engine.context, node))
            return
        # Is this data model we are changing?
        if dataModel.getFullname() != self._dataModels[self._dataModelIndex]:
            return
        dataModelName = self._dataModels[self._dataModelIndex]
        fieldName = self._dataModelFields[dataModelName][self._fieldIndex]
        mutator = self._fieldMutators[fieldName][self._mutatorIndex]
        node = dataModel.getRoot().getByName(fieldName)
        mutator.sequentialMutation(node)


class RandomDeterministicMutationStrategy(MutationStrategy):
    """
    Randomly select an element to fuzz until every element has
    been completed.

    Note: This strategy does not affect the state model
    Note: First test case will not be modified
    """

    def __init__(self, node, parent):
        MutationStrategy.__init__(self, node, parent)
        self._random = random.Random()
        self._random.seed("fnord")
        #: Is this a finite strategy?
        self.isFinite = True
        #: Number of fields to change
        self._count = None
        #: Data models (by fullname)
        self._dataModels = []
        #: Key is field fullname, value is array of mutators, position 0 is current
        #: when mutators are completed they will be removed.  Same with fields.
        self._fieldMutators = {}
        #: Current mutator
        self.mutator = None
        #: Current field name
        self.fieldName = None
        #: Is initial test case?
        self._isFirstTestCase = True
        #self._counts = {}

    def getCount(self):
        """
        Return the number of test cases
        """
        if self._isFirstTestCase:
            return None
        if self._count is None:
            cnt = 0
            for mutators in self._fieldMutators.values():
                for m in mutators:
                    c = m.getCount()
                    #self._counts[m] = c
                    if c is None:
                        raise Exception("Count was null from {!r}".format(m))
                    cnt += c
            self._count = cnt
        return self._count

    def next(self):
        if len(self._fieldMutators.keys()) == 0:
            raise PeachException("Error: Peach couldn't find any DataModels "
                                 "with elements to fuzz!")
        if self._isFirstTestCase:
            self._isFirstTestCase = False
        if self.mutator is not None:
            try:
                #self._counts[self.mutator] -= 1
                self.mutator.next()
            except MutatorCompleted:
                self._fieldMutators[self.fieldName].remove(self.mutator)
                self.mutator = None
        while len(self._fieldMutators) > 0:
            self.fieldName = self._random.choice(self._fieldMutators.keys())
            if len(self._fieldMutators[self.fieldName]) == 0:
                del self._fieldMutators[self.fieldName]
                continue
            self.mutator = \
                self._random.choice(self._fieldMutators[self.fieldName])
            return
        #for m in self._counts.keys():
        #	print "%s has %d counts left" % (m.name, self._counts[m])
        raise MutatorCompleted()

    def currentMutator(self):
        """
        Return the current Mutator in use
        """
        if self._isFirstTestCase:
            return _Unknown()
        return self.mutator

    def onDataModelGetValue(self, action, dataModel):
        """
        Called before getting a value from a data model

        @type	action: Action
        @param	action: Action we are starting
        @type	dataModel: Template
        @param	dataModel: Data model we are using
        """
        # On first test case lets just figure out which data models and fields
        # we will be mutating.
        if self._isFirstTestCase:
            fullName = dataModel.getFullname()
            if fullName not in self._dataModels:
                self._dataModels.append(fullName)
                nodes = dataModel.getAllChildDataElements()
                nodes.append(dataModel)
                for node in nodes:
                    if node.isMutable:
                        mutators = self._fieldMutators[node.getFullname()] = []
                        # We should also populate the mutators here
                        for m in Engine.context.mutators:
                            if m.supportedDataElement(node):
                                # Need to create new instance from class
                                mutators.append(m(Engine.context, node))
            return
        # Is this data model we are changing?
        if not self.fieldName.startswith(dataModel.getFullname()):
            return
        node = dataModel.getRoot().getByName(self.fieldName)
        self.mutator.sequentialMutation(node)


class ReproStrategy(MutationStrategy):
    """
    Assumes a single output action and a folder of files to try.
    """

    def __init__(self, node, parent):
        MutationStrategy.__init__(self, node, parent)
        #: Number of iterations before we switch files
        self.switchCount = 100
        #: Number of iterations
        self.iterationCount = 0
        #: Are we using multiple data sets?
        self.multipleFiles = False
        #: Will this mutation strategy ever end?
        self.isFinite = False
        #: Number of fields to change
        self._n = 7
        #: Data models (fullname as key, value is node count)
        self._dataModels = {}
        #: Mutators for each field
        self._fieldMutators = {}
        #: Is initial test case?
        self._isFirstTestCase = True
        #: Data model selected for change
        self._dataModelToChange = None
        #: Random number generator for our instance
        self._random = random.Random()
        self._mutator = _RandomMutator()
        self.action = None
        self.completed = False
        self.firstFile = True

    def next(self):
        if self.action.data is not None and self.action.data.multipleFiles:
            if self.firstFile:
                self.action.data.gotoFirstFile()
                self.firstFile = False
            else:
                try:
                    self.action.data.gotoNextFile()
                except:
                    self.completed = True
        if self.completed:
            raise MutatorCompleted()

    def getCount(self):
        """
        Return the number of test cases
        """
        return None

    def _getNodeCount(self, node):
        """
        Return the number of DataElements that are children of node
        """
        return len(node.getAllChildDataElements())

    def currentMutator(self):
        """
        Return the current Mutator in use
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
        self.iterationCount += 1
        if not self._isFirstTestCase:
            self._dataModelToChange = self._dataModels.keys()[0]

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

    def onDataModelGetValue(self, action, dataModel):
        """
        Called before getting a value from a data model

        @type	action: Action
        @param	action: Action we are starting
        @type	dataModel: Template
        @param	dataModel: Data model we are using
        """
        if action.data is not None and action.data.multipleFiles:
            self.action = action
            self.context = action.getRoot()
            # If a file fails to parse, don't exit the run, instead re-crack
            # until we find a working file.
            while True:
                if self.firstFile:
                    action.data.gotoFirstFile()
                    self.firstFile = False
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
                    print("")
                    break
                except:
                    pass
            # Cache default values
            action.template = template
            template.getValue()
            # Re-create state engine copy.  We do this to avoid have
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
                for node in nodes:
                    mutators = []
                    self._fieldMutators[node.getFullname()] = mutators
                    for m in Engine.context.mutators:
                        if m.supportedDataElement(node):
                            # Need to create new instance from class
                            for i in range(m.weight ** 4):
                                mutators.append(m(Engine.context, node))
            return


#MutationStrategy.DefaultStrategy = SequentialMutationStrategy
MutationStrategy.DefaultStrategy = RandomDeterministicMutationStrategy
