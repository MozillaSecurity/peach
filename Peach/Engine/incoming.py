# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
import sys
import struct
import logging

from Peach.Engine.common import *
from Peach.Engine.dom import *
import Peach


def Debug(level, msg):
    """
    Debug output.  Uncommenting the following
    print line will cause *lots* of output
    to be displayed.  It significantly slows the
    data cracking process.
    """
    # Don't show look aheads
    if Peach.Engine.engine.Engine.debug:
        if DataCracker._tabLevel == 0:
            print(msg)


def PeachStr(s):
    """
    Our implementation of str() which does not
    convert None to 'None'.
    """

    if s is None:
        return None

    return str(s)


class DataCracker(object):
    """
    This class will try and parse data into a data model.  This
    process will try and best-fit data based on performing look
    aheads with fit-ratings.
    """

    #: Have we recursed into DataCracker?
    _tabLevel = 0

    def __init__(self, peachXml, inner=False):
        self.peach = peachXml
        self.deepString = -1

        #: To what depth are we looking ahead?
        self.lookAheadDepth = 0

        #: Are we looking ahead?
        self.lookAhead = False

        #: Parent position (if any)
        self.parentPos = 0

        if not inner:
            DataCracker._tabLevel = 0

    def internalCrackData(self, template, buff, method='setValue'):
        """
        This is the internal method called when we recurse into
        crackData.  It will not perform certain operations that should
        be performed on the entire data model instead of sub-portions.
        """

        if not isinstance(buff, PublisherBuffer):
            raise Exception("Error: buff is not a PublisherBuffer")

        self.method = method
        (rating, pos) = self._handleNode(template, buff, 0, None) #, self.dom)
        Debug(1, "RATING: %d - POS: %d - LEN(DATA): %d" % (rating, self.parentPos + pos, len(buff.data)))
        if pos < len(buff.data) - 1:
            Debug(1, highlight.warning("WARNING: Did not consume all data!!!"))

        Debug(1, "Done cracking stuff")
        return rating, pos

    def optmizeModelForCracking(self, datamodel, silent=False):
        """
        This method will pre-compute some values that will
        enable optimzing how we crack data into said model.
        """

        if not silent:
            logging.info("Optimizing DataModel '%s'" % datamodel.name)

        # Setup choice fastcheck
        for node in datamodel.getAllChildDataElements():
            if node.elementType == 'choice':
                for child in node:
                    # If _isTokenNext on our choice child is true we can cache
                    # cache that value and use it to super speed up choice checks
                    fastCheck = False
                    fastCheckValue = None
                    fastCheckOffset = 0

                    if child.isStatic:
                        fastCheck = True
                        fastCheckValue = child.getValue()
                        fastCheckOffset = 0

                    #Debug(1, "optmizeModelForCracking: FastCheck: Child is token for '%s'" % child.name)
                    else:
                        values = self._isTokenNext(child, True)
                        #Debug(1, "optmizeModelForCracking: FastCheck: back from _isTokenNext")
                        if values is not None and values[0].getFullname().find(child.getFullname()) != -1:
                            fastCheck = True
                            fastCheckValue = values[0].getValue()
                            fastCheckOffset = values[1]

                            # Sanity check
                            if len(fastCheckValue) < 1:
                                raise PeachException(
                                    "optmizeModelForCracking: Warning, fastCheckValue is < 1 in length")

                                #Debug(1, "optmizeModelForCracking: FastCheck: Found next token for '%s' [%s]" % (child.name, values[0].name))

                        else:
                            #Debug(1, "optmizeModelForCracking: Found no token for '%s'" % child.name)
                            #raise PeachException("_handleChoice(): Found no token for '%s'" % child.name)
                            pass

                    child.choiceCache = (fastCheck, fastCheckOffset, fastCheckValue)


    def crackData(self, template, buff, method='setValue'):
        """
        Crack data based on template.  Set values into data tree.

        Will throw an exception (NeedMoreData) if additional data is required.
        The exception contains the minimum amount of additional data needed before
        trying to re-crack the data.
        """

        if not isinstance(buff, PublisherBuffer):
            raise Exception("Error: buff is not a PublisherBuffer")

        # Reset all values in tree
        # NOTE: Do not change setValue to method.  We NEEVER want
        #       to run this with setDefaultValue or else DEATH AND DOOM TO U!
        #
        # Do we really need todo this?
        #
        #self._resetDataElementValues(template, 'setValue')

        #self.method = 'setValue'
        self.crackPassed = True
        self.method = method
        (rating, pos) = self._handleNode(template, buff, 0, None) #, self.dom)
        Debug(1, "RATING: %d - POS: %d - LEN(DATA): %d" % (rating, self.parentPos + pos, len(buff.data)))
        if pos < len(buff.data) - 1:
            self.crackPassed = False
            Debug(1, "WARNING: Did not consume all data!!!")
        if rating > 2:
            self.crackPassed = False

        # Find all our placements and shift elements around.
        placements = []
        for placement in template.getAllPlacementsInDataModel():
            placements.append(placement)

        for placement in placements:
            # ----

            # We need to update all relations to fully qualified names since we have fully moved
            # nodes around.  There are two categories.  First, of-relations and second relations.
            # We will track these in to arrays of a tuple.

            relations = []
            relationsHold = []
            paramReferences = []

            Debug(1, "Get all relations")
            for relation in placement.parent.getRelationsOfThisElement():
                if relation.type == 'when':
                    continue

                #print "Found:",relation.getFullname()
                relations.append([relation, placement.parent])
                relationsHold.append(relation)

            for child in placement.parent.getAllChildDataElements():
                for relation in child.getRelationsOfThisElement():
                    if relation not in relationsHold and relation.type != 'when':
                        #print "Found:",relation.getFullname()
                        relations.append([relation, child])
                        relationsHold.append(relation)

            for relation in placement.parent._getAllRelationsInDataModel(placement.parent):
                if relation not in relationsHold and relation.type != 'when':
                    try:
                        obj = relation.getOfElement()
                        if obj is None:
                            print("relation:", relation.getFullname())
                            print("of: ", relation.of)

                            raise Exception("obj is null")
                    except:
                        print("relation:", relation.getFullname())
                        print("of:", relation.of)
                        raise

                    #print "Found:",relation.getFullname()
                    relations.append([relation, obj])
                    relationsHold.append(relation)

            # Locate things like <Param name="ref" value="Data" />
            Debug(1, "Get all parameter references")
            for param in placement.parent.getRootOfDataMap().getElementsByType(Param):
                if param.name == 'ref':
                    obj = param.parent.parent.find(param.defaultValue.replace("'", ""))
                    if obj == placement.parent:
                        paramReferences.append([param, obj])

            # ----

            if placement.after is not None:
                #after = template.findDataElementByName(placement.after)
                after = placement.parent.find(placement.after)
                if after is None:
                    raise Exception("Error: Unable to locate element [%s] for placement" % placement.after)

                Debug(1, "Moving element [%s] to after [%s]." % (placement.parent.name, after.name))
                Debug(1, "  Pre-name: %s" % placement.parent.getFullnameInDataModel())
                Debug(1, "  Found %d relations" % len(relationsHold))
                Debug(1, "  Found %d param references" % len(paramReferences))

                # Remove from old place
                placement.parent.origName = placement.parent.name
                del placement.parent.parent[placement.parent.origName]

                # Do we need to rename our Element?
                if after.parent.has_key(placement.parent.name):
                    # Yes... :)
                    cnt = 0
                    while after.parent.has_key(placement.parent.name):
                        placement.parent.name = placement.parent.origName + ("_%d" % cnt)
                        cnt += 1

                    Debug(1, "  Renamed before move from [%s] to [%s]" % (
                        placement.parent.origName, placement.parent.name))

                # Insert after after
                after.parent.insert(after.parent.index(after) + 1, placement.parent)

                # Update parent
                placement.parent.parent = after.parent

                # Remove placement
                placement.parent.placement = None

            elif placement.before is not None:
                #before = template.findDataElementByName(placement.before)
                before = placement.parent.find(placement.before)
                if before is None:
                    raise Exception("Error: Unable to locate element [%s] for placement" % placement.before)

                Debug(1, "Moving element [%s] to before [%s]." % (placement.parent.name, before.name))
                Debug(1, "  Pre-name: %s" % placement.parent.getFullnameInDataModel())
                Debug(1, "  Found %d relations" % len(relationsHold))
                Debug(1, "  Found %d param references" % len(paramReferences))

                # Remove from old place
                placement.parent.origName = placement.parent.name
                del placement.parent.parent[placement.parent.origName]

                # Do we need to rename our Element?
                if before.parent.has_key(placement.parent.name):
                    # Yes... :)
                    cnt = 0
                    while before.parent.has_key(placement.parent.name):
                        placement.parent.name = placement.parent.origName + ("_%d" % cnt)
                        cnt += 1

                    Debug(1, "  Renamed before move from [%s] to [%s]" % (
                        placement.parent.origName, placement.parent.name))

                # Insert after after
                before.parent.insert(before.parent.index(before), placement.parent)

                # Update parent
                placement.parent.parent = before.parent

                # Remove placement
                placement.parent.placement = None

                Debug(1, "  Final name: %s" % placement.parent.getFullnameInDataModel())

            else:
                raise Exception("Error: placement is all null in bad ways!")

            # Update relations
            Debug(1, "Update relations")
            for relation, of in relations:
                relation.of = of.getFullnameInDataModel()

                # Handle FROM side too
                for r in of.relations:
                    if r.From is not None and r.From.endswith(relation.parent.name):
                        r.From = relation.parent.getFullnameInDataModel()

                        #print "Updating %s to %s" % (relation.getFullname(), relation.of)

            Debug(1, "Update param references")
            for param, obj in paramReferences:
                # Need to recreate the fixup to make sure
                # it re-parses the ref parameter.

                param.defaultValue = "'''%s'''" % obj.getFullnameInDataModel()

                fixup = param.parent

                code = "PeachXml_" + fixup.classStr + '('

                isFirst = True
                for param in fixup:
                    if not isinstance(param, Param):
                        continue

                    if not isFirst:
                        code += ', '
                    else:
                        isFirst = False

                    code += PeachStr(param.defaultValue)

                code += ')'

                fixup.fixup = evalEvent(code, {})

        Debug(1, "Done cracking stuff")
        #sys.exit(0)

        #template.printDomMap()

        return rating, pos

    def _resetDataElementValues(self, node, method):
        """
        Reset values in data tree to None.
        """

        eval("node.%s(None)" % method)

        if hasattr(node, 'rating'):
            node.rating = None

        if hasattr(node, 'pos'):
            node.pos = None

        for child in node._children:
            if isinstance(child, Peach.Engine.dom.DataElement):
                self._resetDataElementValues(child, method)


    def _GetTemplateByName(self, str):
        """
        Get the object indicated by ref.  Currently the object must have
        been defined prior to this point in the XML
        """

        origStr = str
        baseObj = self.peach

        # Parse out a namespace

        if str.find(":") > -1:
            ns, tmp = str.split(':')
            str = tmp

            # Check for namespace
            if hasattr(self.context.namespaces, ns):
                baseObj = getattr(self.context.namespaces, ns)
            else:
                raise Exception("Unable to locate namespace")

        for name in str.split('.'):
            # check base obj
            if hasattr(baseObj, name):
                baseObj = getattr(baseObj, name)

            # check templates
            elif hasattr(baseObj, 'templates') and hasattr(baseObj.templates, name):
                baseObj = getattr(baseObj.templates, name)

            else:
                raise Exception("Could not resolve ref '%s'" % origStr)

        return baseObj

    def _getRootParent(self, node):
        root = node
        while hasattr(root, 'parent') and root.parent is not None:
            root = root.parent

        return root

    def _handleArray(self, node, buff, pos, parent=None, doingMinMax=False):
        """
        This method is used when an array has been located (an element with
        minOccurs or maxOccurs set).

        Note: This code was moved out of _handleNode() on 11/16/08

        Todo: This array handling code has gotten out of hand.  It needs
              some re-working and cleaning up.
        """

        Debug(1, "_handleArray(%s): %s >>Enter" % (node.name, node.elementType))
        Debug(1, "_handleArray(%s): %s" % (node.name, node.getFullname()))

        if node.parent is None:
            raise Exception("Error, parent is null: " + node.name)

        Debug(1, "*** Node Occures more then once!")
        rating = newRating = 1
        newCurPos = pos
        origPos = pos
        dom = None
        curpos = None
        maxOccurs = node.maxOccurs
        minOccurs = node.minOccurs
        name = node.name
        goodLookAhead = None
        hasCountRelation = False
        isDeterministic = self._doesNodeHaveStatic(node) or self._doesNodeHaveConstraint(node)
        origionalNode = node.copy(node.parent)

        ## Locate any count restrictions and update maxCount to match

        Debug(1, "-- Looking for Count relation...")
        relation = node.getRelationOfThisElement('count')
        if relation is not None and relation.type == 'count' and node.parent is not None:
            maxOccurs = int(relation.getValue(True))
            Debug(1, "@@@ Found count relation [%d]" % maxOccurs)
            hasCountRelation = True

            ## Check for count relation, verify > 0
            if maxOccurs < 0:
                Debug(1, "_handleArray: Found negative count relation: %d" % maxOccurs)
                return 4, pos

            elif maxOccurs == 0:
                for child in node.getElementsByType(DataElement):
                    if child == node:
                        continue

                    # Remove relation (else we get errors)
                    for relation in child.getRelationsOfThisElement():
                        if node.getFullname().find(relation.parent.getFullname()) == 0:
                            # Relation inside of block we are removing
                            continue

                        Debug(1, "@! Child Relation: From: %s  - of: %s" % (relation.parent.name, relation.of))
                        if relation in relation.parent.relations:
                            relation.parent.relations.remove(relation)
                        if relation.parent.has_key(relation.name):
                            del relation.parent[relation.name]

                        for rfrom in node.relations:
                            if rfrom.From is not None and rfrom.From.endswith(relation.parent.name):
                                Debug(1, "@ Also removing FROM side")
                                node.relations.remove(rfrom)
                                if node.parent.has_key(rfrom.name):
                                    del node.parent[rfrom.name]


                # Remove relation (else we get errors)
                for relation in node.getRelationsOfThisElement():
                    Debug(1, "@ Found and removing relation: %s" % relation.getFullname())
                    if relation in relation.parent.relations:
                        Debug(1, "@ Removing type: %s, parent.name: %s" % (relation.type, relation.parent.name))
                        relation.parent.relations.remove(relation)

                    if relation.parent.has_key(relation.name):
                        Debug(1, "@ Also removeing from collection")
                        del relation.parent[relation.name]

                    for rfrom in node.relations:
                        if rfrom.From is not None and rfrom.From.endswith(relation.parent.name):
                            Debug(1, "@ Also removing FROM side")
                            node.relations.remove(rfrom)
                            if node.parent.has_key(rfrom.name):
                                del node.parent[rfrom.name]

                # Remove element
                del node.parent[node.name]

                # We passed muster...I think :)
                rating = 2
                pos = origPos

                Debug(1, "_handleArray(%s): Zero count on array, removed <<EXIT 1" % node.name)
                return rating, pos

        ## Hack for fixed length arrays to remove lookAheads

        if hasCountRelation == False and node.occurs is not None:
            maxOccurs = node.occurs
            hasCountRelation = True

        ## Handle maxOccurs > 1

        try:
            node.relationOf = None
            Debug(1, "@@@ Entering while loop")
            for occurs in range(maxOccurs):
                Debug(1, "@@@ In While, newCurPos=%d" % (self.parentPos + newCurPos))

                ## Are we out at end of stream?
                if buff.haveAllData and newCurPos >= len(buff.data):
                    Debug(1, "@ Exiting while loop, end of data! YAY!")
                    if occurs == 0:
                        Debug(1, "@ Exiting while on first loop")
                        if node.minOccurs > 0:
                            Debug(1, "@ minOccurs != 0, changing rating to 4")
                            rating = 4

                        else:
                            # This code is duplicated lower down.

                            # Remove node and increase rating.
                            Debug(1, "@ minOccurs == 0, removing node")

                            # Remove relation (else we get errors)
                            for relation in node.getRelationsOfThisElement():
                                Debug(1, "@ Found and removing relation...")
                                relation.parent.relations.remove(relation)
                                relation.parent.__delitem__(relation.name)

                            # Delete node from parent
                            del node.parent[node.name]

                            # Fix up our rating
                            rating = 2
                            curpos = pos
                    break

                else:
                    Debug(1, "@ Have enough data to try again: %d < %d" % (newCurPos, len(buff.data)))

                ## Make a copy so we don't overwrite existing node
                if occurs > 0:
                    nodeCopy = origionalNode.copy(node.parent)
                    nodeCopy.name = name + "-%d" % occurs

                    ## Add to parent
                    node.parent.insert(node.parent.index(node) + occurs, nodeCopy)

                else:
                    ## If we are on the first element
                    nodeCopy = node

                ## Run onArrayNext
                if DataCracker._tabLevel == 0 and nodeCopy.onArrayNext is not None:
                    evalEvent(node.onArrayNext, {'node': nodeCopy}, node)

                ## Check out look-ahead (unless we have count relation)
                if (not isDeterministic) and (not hasCountRelation) and self._nextNode(nodeCopy) is not None:
                    Debug(1, "*** >> node.name: %s" % node.name)
                    Debug(1, "*** >> nodeCopy.name: %s" % nodeCopy.name)
                    Debug(1, "*** >> LookAhead")

                    newRating = self._lookAhead(nodeCopy, buff, newCurPos, None, False)
                    Debug(1, "*** << LookAhead [%d]" % newRating)

                    # If look ahead was good, save and check later.
                    if newRating < 3:
                        goodLookAhead = newRating

                ## Do actual
                Debug(1, "*** >> nodeCopy.name: %s" % nodeCopy.name)
                Debug(1, "*** >> DOING ACTUAL HANDLENODE")

                origNewCurPos = newCurPos
                (newRating, newCurPos) = self._handleNode(nodeCopy, buff, newCurPos, None, True)
                if newCurPos < origNewCurPos:
                    raise Exception("WHoa!  We shouldn't have moved back in position there... [%d:%d]" % origNewCurPos,
                                    newCurPos)

                ## Handle minOccurs == 0
                if occurs == 0 and newRating >= 3 and node.minOccurs == 0:
                    # This code is duplicated higher up

                    if hasCountRelation and maxOccurs > 0:
                        Debug(1, "Error: We think count == 0, relation says %d" % maxOccurs)
                        Debug(1, "Returning a rating of suck (4)")
                        return 4, pos

                    # Remove node and increase rating.
                    Debug(1, "Firt element rating was poor and minOccurs == 0, remoing element and upping rating.")

                    # Remove relation (else we get errors)
                    for relation in node.getRelationsOfThisElement():
                        relation.parent.relations.remove(relation)
                        del relation.parent[relation.name]

                    # Delete our copy
                    if nodeCopy.name != node.name:
                        del node.parent[nodeCopy.name]

                    # Delete orig
                    del node.parent[node.name]
                    rating = 2
                    curpos = pos = origPos
                    break

                ## Verify we didn't break a good lookahead
                if not hasCountRelation and newRating < 3 and not self.lookAhead and goodLookAhead is not None:
                    lookAheadRating = self._lookAhead(nodeCopy, buff, newCurPos, None, False)
                    if lookAheadRating >= 3:
                        del node.parent[nodeCopy.name]
                        Debug(1, "*** Exiting min/max: We broke a good lookAhead!")
                        break

                ## Verify high enough rating
                if newRating < 3 and not self.lookAhead:
                    Debug(1, "*** That worked out!")
                    pos = curpos = newCurPos
                    rating = newRating

                    # First time through convert position 0 node
                    if occurs == 0:
                        ## First fix up our first node
                        index = node.parent.index(node)
                        del node.parent[node.name]

                        node.array = node.name
                        node.name += "-0"
                        node.arrayPosition = 0
                        node.arrayMinOccurs = node.minOccurs
                        node.arrayMaxOccurs = node.maxOccurs
                        node.minOccurs = 1
                        node.maxOccurs = 1

                        node.parent.insert(index, node)

                        # Update relation to have new name
                        if relation is not None and relation.of is not None:
                            # We need to support out count being outside
                            # a double loop, so lets check and see if
                            # our relation is closer to root than us
                            # and if so check the parents in between

                            relationParents = []
                            obj = relation.parent.parent
                            while obj is not None and obj.parent is not None:
                                if isinstance(obj, DataElement):
                                    relationParents.append(obj)
                                obj = obj.parent

                            currentParents = []
                            obj = node.parent
                            while obj is not None and obj.parent is not None:
                                if isinstance(obj, DataElement):
                                    currentParents.append(obj)
                                obj = obj.parent

                            boolInsideArray = False
                            if len(currentParents) > len(relationParents):
                                minParents = len(relationParents)
                            else:
                                minParents = len(currentParents)

                            # Make sure i gets initialized
                            # in some cases (minParents == 0) we never
                            # go through this next for loop and i is unknown.
                            i = minParents

                            for i in range(minParents):
                                if relationParents[i] != currentParents[i]:
                                    #Debug(1, "_handleArray: Miss-match parents: %s, %s" % (relationParents[i].name, currentParents[i].name))
                                    break

                            #Debug(1, "_handleArray: i == %d" % i)
                            for x in range(i, len(currentParents)):
                                if currentParents[x].maxOccurs > 1:
                                    #Debug(1, "_handleArray: Outside array found: %s" % currentParents[x].name)
                                    boolInsideArray = True
                                    break

                            if boolInsideArray:
                                Debug(1, "_handleArray: Our count relation is outside of a double array.")
                                Debug(1, "_handleArray: Keeping a copy around for next iteration.")

                                newRel = relation.copy(relation.parent)
                                relation.parent.append(newRel)
                                relation.parent.relations.append(newRel)
                            else:
                                Debug(1, "_handleArray: No double array relation issue")

                                # Should we remove From?
                                for r in origionalNode.relations:
                                    if r.From == relation.parent.name:
                                        Debug(1, "_handleArray: Removing r.From origionalNode")

                                        origionalNode.relations.remove(r)

                                        try:
                                            del origionalNode[r.name]
                                        except:
                                            pass

                            # Now update curretn realtion
                            relation.of = node.name


                    else:
                        # Next fix up our copied node
                        nodeCopy.array = node.array
                        nodeCopy.arrayPosition = occurs
                        nodeCopy.arrayMinOccurs = node.arrayMinOccurs
                        nodeCopy.arrayMaxOccurs = node.arrayMaxOccurs
                        nodeCopy.minOccurs = 1
                        nodeCopy.maxOccurs = 1

                else:
                    Debug(1, "*** Didn't work out!")
                    del node.parent[nodeCopy.name]
                    break

                occurs += 1

                Debug(1, "@@@ Looping, occurs=%d, rating=%d" % (occurs, rating))

            if occurs < minOccurs:
                rating = 4

            Debug(1, "@@@ Exiting While Loop")

        except:
            #pass
            raise

        ### Do a quick dump of parent's children:
        #print "------"
        #for c in node.parent:
        #	if isinstance(c, DataElement):
        #		print c.name
        #print "------"

        if curpos is not None:
            Debug(1, "@@@ Returning a rating=%d, curpos=%d, pos=%d, newCurPos=%d, occuurs=%d" % (
                rating, self.parentPos + curpos, self.parentPos + pos, self.parentPos + newCurPos, occurs))
            node.relationOf = None
            return rating, curpos

        Debug(1, "_handleArray(%s): type=%s, realpos=%d, pos=%d, rating=%d <<EXIT" % (
            node.name, node.elementType, self.parentPos + pos, pos, rating))
        node.relationOf = None
        return rating, pos

    def _handleNode(self, node, buff, pos, parent=None, doingMinMax=False):
        Debug(1, "_handleNode(%s): %s pos(%d) >>Enter" % (highlight.info(node.name), node.elementType, pos))

        ## Sanity checking

        if pos > len(buff.data):
            Debug(1, "_handleNode: Running past data!, pos: %d, len.data: %d" % (pos, len(buff.data)))
            return 4, pos

        if node is None:
            raise Exception("_handleNode: Node is None, bailing!")

        ## Save off origional position

        origPos = pos

        ## check for when relation

        if node.HasWhenRelation():
            rel = node.GetWhenRelation()

            environment = {
                #'Peach' : self.engine.peach,
                'self': node,
                'pos': pos,
                'data': buff.data
            }

            Debug(1, "_handleNode: When: Running expression")
            node._fixRealParent(node)

            if not evalEvent(rel.when, environment, node):
                # Remove this node from data tree
                #print "REMOVING:",node.name

                # Locate relations and kill 'em off
                for r in node.getRelationsOfThisElement():
                    # With --new we had some issues with
                    # double deleteing.

                    try:
                        r.parent.relations.remove(r)
                        del r.parent[r.name]
                    except:
                        pass

                # Remove relations for all children as well
                for child in node.getAllChildDataElements():
                    for r in child.getRelationsOfThisElement():
                        try:
                            r.parent.relations.remove(r)
                            del r.parent[r.name]
                        except:
                            pass

                node._unFixRealParent(node)
                del node.parent[node.name]

                Debug(1, "_handleNode: When: Returned False.  Removing and returning 1.")

                node.relationOf = None
                return 1, pos

            node._unFixRealParent(node)
            Debug(1, "_handleNode: When: Returned True.")

        ## Skipp around if we have an offset relations

        popPosition = None
        if isinstance(node, DataElement) and not (not doingMinMax and (node.minOccurs < 1 or node.maxOccurs > 1)):
            relation = node.getRelationOfThisElement('offset')
            if relation is not None and relation.type == 'offset':
                # We need to move this show!
                try:
                    Debug(1, "_handleNode: Found offset relation")
                    Debug(1, "_handleNode: Origional position saved as %d" % (self.parentPos + pos))
                    popPosition = pos
                    pos = int(relation.getValue(True))
                    Debug(1, "_handleNode: Changed position to %d" % (self.parentPos + pos))

                except:
                    raise
            else:
                Debug(1, "_handleNode: Did not find offset relation")

        ## Would be nice to have our current pos in scripting :)
        node.possiblePos = pos

        ## Do the crazy! (aka call specific crack handler)

        # Array handling *MUST* always be first!
        if not doingMinMax and (node.minOccurs < 1 or node.maxOccurs > 1):
            if popPosition is not None:
                raise PeachException("Error: Found an offset relation to an array, this is not allowed!")

            (rating, pos) = self._handleArray(node, buff, pos, parent, doingMinMax)

        elif node.elementType == 'string':
            (rating, pos) = self._handleString(node, buff, pos, parent, doingMinMax)

            # Do we have a transformer, if so decode the data
            if node.transformer is not None:
                try:
                    Debug(1, "_handleNode: String: Found transformer, decoding...")
                    node.defaultValue = node.transformer.transformer.decode(node.defaultValue)

                except:
                    Debug(1, "_handleNode: String: Transformer threw exception!")
                    pass

        elif node.elementType == 'number':
            (rating, pos) = self._handleNumber(node, buff, pos, parent, doingMinMax)

        elif node.elementType in ['block', 'template', 'choice']:
            # First -- Determin if we know the size of this block via a
            #          size-of relation

            length = None
            relation = node.getRelationOfThisElement('size')
            if relation is not None and relation.isOutputOnly:
                relation = None

            if relation is not None and node.parent is not None:
                try:
                    length = relation.getValue(True)
                    Debug(1, "-----> FOUND BLOCK OF RELATION [%s] <-----" % repr(length))
                    fullName = relation.parent.getFullname()
                    Debug(1, "Size-of Fullname: " + fullName)
                    Debug(1, "node Fullname: " + node.getFullname())

                    #length = relation.getValue()
                    Debug(1, "Size-of Length: %s" % length)

                    # Verify we are not inside the "of" portion
                    if fullName.find(node.getFullname() + ".") == 0:
                        length = None
                        Debug(1, "!!! Not using relation, inside of OF element")

                except:
                    length = None

            elif node.hasLength():
                length = node.getLength()
                Debug(1, "-----> Block has known legnth: %d" % length)

            # Only if we have a length, and we are not already the top
            # level element.  This will prevent infinit recursion into
            # the data cracker if we have a <Block length="10" /> type
            # situation.
            if length is not None and node.parent is not None:
                # Make sure we have the data
                if len(buff.data) < (pos + length):
                    if not buff.haveAllData:
                        node.relationOf = None
                        try:
                            buff.read((pos + length) - len(buff.data))
                        #raise NeedMoreData(length, "")
                        except:
                            rating = 4
                            pos = pos + length

                    else:
                        rating = 4
                        pos = pos + length

                if len(buff.data) >= (pos + length):
                    Debug(1, "---- About to Crack internal Block ----")

                    # Parse this node on it's own
                    cracker = DataCracker(self.peach, True)
                    cracker.haveAllData = True
                    cracker.parentPos = pos + self.parentPos
                    data = buff.data[pos:pos + length]

                    # Do we have a transformer, if so decode the data
                    if node.transformer is not None:
                        try:
                            Debug(1, "Found transformer, decoding...")
                            data = node.transformer.transformer.decode(data)

                        except:
                            Debug(1, "Transformer threw exception!")
                            pass

                    # We need to remove the parent temporarily to
                    # avoid a recursion issue.

                    parent = node.parent
                    node.parent = None
                    node.realParent = parent

                    # We need to remove any offset relation temporarily
                    # to avoid running it twice
                    offsetRelation = node.getRelationOfThisElement('offset')
                    if offsetRelation is not None:
                        offsetRelationParent = offsetRelation.parent

                        if offsetRelation in offsetRelationParent.relations:
                            offsetRelationParent.relations.remove(offsetRelation)
                        if offsetRelationParent.has_key(offsetRelation.name):
                            del offsetRelationParent[offsetRelation.name]

                        offsetFromRelation = None
                        for child in node.relations:
                            if child.type == 'offset':
                                offsetFromRelation = child

                                if offsetFromRelation in node.relations:
                                    node.relations.remove(offsetFromRelation)
                                if node.has_key(offsetFromRelation.name):
                                    del node[offsetFromRelation.name]

                    try:
                        newBuff = PublisherBuffer(None, data)
                        (rating, crackpos) = cracker.internalCrackData(node, newBuff, self.method)
                        if rating == 0:
                            rating = 1

                    finally:
                        # We need to update the positions of each child
                        # to be + node.pos.
                        #
                        # Note: We are doing this in a finally to make
                        #   sure the values in peach validation are
                        #   correct.
                        for c in node.getAllChildDataElements():
                            if hasattr(c, 'pos') and c.pos is not None:
                                c.pos += pos

                    # Add back our offset relation
                    if offsetRelation is not None:
                        offsetRelationParent.relations.append(offsetRelation)

                        if offsetFromRelation is not None:
                            node.relations.append(offsetFromRelation)

                    # Add back our parent
                    node.parent = parent
                    delattr(node, "realParent")
                    node.pos = pos
                    node.rating = rating

                    pos += length

                    # Verify we used all the data
                    if crackpos != len(data):
                        Debug(1, "---- Crackpos != len(data): %d != %d ----" % (self.parentPos + crackpos, len(data)))
                        #rating = 4
                    ## !!! NEED TO REMOVE THIS !!!
                    #print "WARNING: Ignoring fact that crackpos != len(data)!!!"

                    Debug(1, "---- Finished with internal block (%d:%d) ----" % (rating, self.parentPos + pos))

            else:
                if node.elementType == 'choice':
                    (rating, pos) = self._handleChoice(node, buff, pos, parent, doingMinMax)
                else:
                    (rating, pos) = self._handleBlock(node, buff, pos, parent, doingMinMax)

        elif node.elementType == 'blob':
            (rating, pos) = self._handleBlob(node, buff, pos, parent, doingMinMax)

            # Do we have a transformer, if so decode the data
            if node.transformer is not None:
                try:
                    Debug(1, "Found transformer, decoding...")
                    node.defaultValue = node.transformer.transformer.decode(node.defaultValue)

                except:
                    Debug(1, "Transformer threw exception!")
                    pass

            Debug(1, "---] pos = %d" % (self.parentPos + pos))
        elif node.elementType == 'custom':
            (rating, pos) = self._handleCustom(node, buff, pos, parent, doingMinMax)
            Debug(1, "---] pos = %d" % (self.parentPos + pos))
        elif node.elementType == 'flags':
            (rating, pos) = self._handleFlags(node, buff, pos, parent, doingMinMax)
        elif node.elementType == 'seek':
            (rating, pos) = self._handleSeek(node, buff, pos, parent, doingMinMax)

        else:
            raise str("Unknown elementType: %s" % node.elementType)

        if popPosition is not None:
            pos = popPosition
            Debug(1, "Popping position back to %d" % (self.parentPos + pos))

        try:
            Debug(1, "_handleNode(%s): type=%s, realpos=%d, pos=%d, rating=%d <<EXIT" % (
                node.name, node.elementType, self.parentPos + pos, pos, rating))
        except:
            print("Caught ODD Exception in CRACKER")
            print("_handleNode(%s): type=%s, realpos=%d, pos=%d <<EXIT" % (
                node.name, node.elementType, self.parentPos + pos, pos))
            rating = 4

        node.relationOf = None
        return rating, pos

    def _verifyParents(self, node):
        print(node.name)
        if node.name == 'Lqcd':
            print("Found Lqcd", node.parent)

        for child in node:
            if child.parent is None:
                print("Child (%s) of (%s) has Null parent" % (child.name, node.name))
            elif child.parent != node:
                print("Child (%s) of (%s) has wrong parent" % (child.name, node.name))

            self._verifyParents(child)

    def _lookAhead(self, node, buff, pos, parent, minMax=True):
        """
        Look ahead one step and get the next rating.  Looking ahead
        from a current node is more complex than it might first seem.

        For example, we might be the 2nd to last element in a block
        that is part of a larger block (but not the last element). We
        will need to be tricky inorder to properly look ahead at the
        rest of the document.
        """

        if node is None:
            return 1

        if pos > len(buff.data):
            Debug(1, "_lookAhead(): pos > len(data), no lookahead")
            return 4

        #print "_lookAhead"
        #traceback.print_stack()

        ## Setup a few variables

        DataCracker._tabLevel += 1

        self.lookAhead = True
        self.lookAheadDepth += 1

        origNode = node
        origParent = parent

        ## First lets copy the data model
        root = origNode.getRootOfDataMap().copy(None)
        node = root.findDataElementByName(origNode.getFullnameInDataModel())
        sibling = self._nextNode(node)

        if node is None:
            raise Exception("Node should not be null here! [%s]" % origNode.getFullnameInDataModel())

        if origParent is not None:
            parent = root.findDataElementByName(origParent.getFullnameInDataModel())

        ## If we could have more than one of the curret node
        ## we will try that node again UNLESS we minMax == False

        # Why are we doing this?  For String Arrays?

        if node.maxOccurs > 1 and minMax:
            Debug(1, "_lookAhead(): look ahead for node")

            #try:
            (rating, pos) = self._handleNode(node, buff, pos, parent)

            # If we have a good rating return it
            if rating < 3:
                self.lookAheadDepth -= 1
                if self.lookAheadDepth == 0:
                    self.lookAhead = False

                self.lookAhead = False
                DataCracker._tabLevel -= 1
                return rating

        ## Now lets try that sibling if we can

        if sibling is None:
            # if no sibling than everything is okay

            Debug(1, "_lookAhead(): node.nextSibling() ==  None, returning 1")
            rating = 1

        else:
            Debug(1, "_lookAhead(): look ahead for node.Sibling(): %s->%s" % (node.name, sibling.name))
            (rating, pos) = self._handleNode(sibling, buff, pos, parent)

        self.lookAheadDepth -= 1
        if self.lookAheadDepth == 0:
            self.lookAhead = False

        DataCracker._tabLevel -= 1
        if pos < len(buff.data):
            return rating + 1

        else:
            return rating

    def _isTokenNext(self, node, fastChoice=False):
        """
        Determine if a token node follows.  Other sized
        nodes can be between them.
        """

        #print "_isTokenNext(%s)" % node.name

        staticNode = None
        length = 0
        n = node
        while True:
            if fastChoice and n.elementType == 'block' and len(n) > 0:
                n = n[0]

            else:
                n = self._nextNode(n)

            if n is None:
                break

            if n.isStatic:
                staticNode = n
                break

            # If we are a choice we fail
            if n.elementType == 'choice':
                # Really we can look into our choice and see
                # if there is a token we can match.

                for child in n:
                    if not hasattr(child, "choiceCache") or child.choiceCache[0] == False:
                        return None

                    # All children are fast checks!
                    return n, length

                return None

            # We fail if array found
            if n.minOccurs != 1 or n.maxOccurs != 1:
                return None

            # If a child flag is token we don't support that
            if n.elementType == 'Flags':
                for child in n:
                    if isinstance(child, 'Flag') and child.isStatic:
                        if fastChoice:
                            return None
                        else:
                            staticNode = n
                            break

            # If we are a block, we need to head into the block.
            if n.elementType == 'block':
                # If no children then size == 0
                if len(n) == 0:
                    continue

                child = n[0]
                if child.isStatic:
                    staticNode = child
                    break

                # If a child flag is token we don't support that
                if n.elementType == 'Flags':
                    for child in n:
                        if isinstance(child, 'Flag') and child.isStatic:
                            if fastChoice:
                                return None
                            else:
                                staticNode = n
                                break

                s = self._hasSize(child)
                if s is None:
                    #print "_isTokenNext: Child has no size, exiting [%s.%s]" % (n.name, child.name)
                    return None

                length += s

                ret = self._isTokenNext(child, fastChoice)
                if ret is None:
                    #print "_isTokenNext: Child has no next token, exiting"
                    return None

                length += ret[1]
                staticNode = ret[0]
                break

            s = self._hasSize(n)
            if s is None:
                #print "_isTokenNext: N has no size, exiting [%s]" % n.name
                return None

            length += s

        # Shouldn't need this check
        if staticNode is None:
            return None

        #print "_isTokenNext: Returning node & length"
        return staticNode, length

    def _isContraintNext(self, node, fastChoice=False):
        """
        Determine if a constraint node follows.
        Other sized nodes can be between them.
        """

        #print "_isContraintNext(%s)" % node.name

        staticNode = None
        length = 0
        n = node
        while True:
            if fastChoice and n.elementType == 'block' and len(n) > 0:
                n = n[0]

            else:
                n = self._nextNode(n)

            if n is None:
                break

            if n.contraint is not None:
                staticNode = n
                break

            # If we are a choice we fail
            if n.elementType == 'choice':
                #print "_isTokenNext: Found choice, exiting"
                return None

            # If a child flag is token we don't support that
            if n.elementType == 'Flags':
                for child in n:
                    if isinstance(child, 'Flag') and child.contraint is not None:
                        if fastChoice:
                            return None
                        else:
                            staticNode = n
                            break

            # If we are a block, we need to
            # head into the block.
            if n.elementType == 'block':
                # If no children then size == 0
                if len(n) == 0:
                    continue

                child = n[0]
                if child.contraint is not None:
                    staticNode = child
                    break

                # If a child flag is token we don't support that
                if n.elementType == 'Flags':
                    for child in n:
                        if isinstance(child, 'Flag') and child.contraint:
                            if fastChoice:
                                return None
                            else:
                                staticNode = n
                                break

                s = self._hasSize(child)
                if s is None:
                    #print "_isTokenNext: Child has no size, exiting [%s.%s]" % (n.name, child.name)
                    return None

                length += s

                ret = self._isConstraintNext(child, fastChoice)
                if ret is None:
                    #print "_isTokenNext: Child has no next token, exiting"
                    return None

                length += ret[1]
                staticNode = ret[0]
                break

            s = self._hasSize(n)
            if s is None:
                #print "_isTokenNext: N has no size, exiting [%s]" % n.name
                return None

            length += s

        # Shouldn't need this check
        if staticNode is None:
            return None

        #print "_isTokenNext: Returning node & length"
        return staticNode, length

    def _isLastUnsizedNode(self, node):
        """
        Determine if the following nodes all have known sizes.
        If they do we can determine our size.
        """

        Debug(1, "_isLastUnsizedNode(%s)" % node.name)

        length = 0
        n = node
        b = False

        while True:
            (n, b) = self._nextNodeOrSizedParent(n)

            if b:
                #Debug(1, "_isLastUnsizedNode: Found sized parent!")
                break

            if n is None:
                #Debug(1, "_isLastUnsizedNode: Next node returned None")
                break

            s = self._hasSize(n)
            if s is None:
                #Debug(1, "_isLastUnsizedNode: returning None due to [%s]" % n.name)
                return None

            length += s

        #Debug(1, "_isLastUnsizedNode: length: %d" % length)
        return length

    def _hasSize(self, node):
        """
        Determine if data element has a size and return it or None
        """

        # TODO:
        #  - Relations
        #  - Custom types?
        #  - Side cases

        if isinstance(node, String) or isinstance(node, Blob):
            if node.length is not None:
                return node.length

            if node.isStatic:
                return len(node.defaultValue)

        elif isinstance(node, Number):
            return int(node.size) / 8

        elif isinstance(node, Block):
            # Check for relation
            relation = node.getRelationOfThisElement('size')
            if relation is not None:
                #Debug(1, "_hasSize(%s): Found relation" % node.name)
                return int(relation.getValue(True))

            # Check each child
            size = 0
            for child in node:
                if isinstance(child, DataElement):
                    ret = self._hasSize(child)
                    if ret is None:
                        return None
                    size += ret

            return size

        elif isinstance(node, Flags):
            return int(node.length) / 8

        elif isinstance(node, Choice):
            # Check for relation
            relation = node.getRelationOfThisElement('size')
            if relation is not None:
                #Debug(1, "_hasSize(%s): Found relation" % node.name)
                return int(relation.getValue(True))

            # Until choice is run we
            # will not know which element
            # was selected.
            return None

        # Check for relation
        relation = node.getRelationOfThisElement('size')
        if relation is not None:
            #Debug(1, "_hasSize(%s): Found relation" % node.name)
            return int(relation.getValue(True))

        return None

    def _doesNodeHaveStatic(self, node):
        """
        Return true if node or it's children is static
        """

        if node.isStatic:
            return True

        for c in node.getAllChildDataElements():
            if c.isStatic:
                return True

        return False

    def _doesNodeHaveConstraint(self, node):
        """
        Return true if node or it's children is static
        """

        if node.constraint is not None:
            return True

        for c in node.getAllChildDataElements():
            if c.constraint is not None:
                return True

        return False

    def _nextStaticNode(self, node):
        """
        Locate the next static node or None
        """

        while node is not None and not node.isStatic:
            node = self._nextNode(node)

        return node

    def _nextNodeOrSizedParent(self, node):
        """
        Find the next node, or sized parent.

        Returns tubple of (Node, Boolean)
        Node - Found node
        Boolean - Is sized parent?
        """

        if node is None:
            return None, False

        #try:
        #	Debug(1, "_nextNodeOrSizedParent(%s)" % node.name)
        #
        #except:
        #	Debug(1, "_nextNodeOrSizedParent: %s" % repr(node))
        #	raise

        if not isinstance(node, Peach.Engine.dom.DataElement) or\
           node.elementType == 'template':
            #Debug(1, "_nextNodeOrSizedParent: not data element or is template, failing")
            return None, False

        # Try and escape Choice blocks.
        while node.parent is not None and node.parent.elementType == 'choice':
            if node.parent.maxOccurs > 1:
                #Debug(1, "_nextNodeOrSizedParent: Returning node.parent due to maxOccurs > 1")
                return node.parent, False

            if self._hasSize(node.parent):
                #Debug(1, "_nextNodeOrSizedParent: Found sized choice parent, this is the last element")
                return node.parent, True

            node = node.parent

        nextNode = node.nextSibling()
        while nextNode is not None and not isinstance(nextNode, Peach.Engine.dom.DataElement):
            nextNode = nextNode.nextSibling()

        if nextNode is not None and isinstance(nextNode, Peach.Engine.dom.DataElement):
            #Debug(1, "_nextNodeOrSizedParent: Found: %s" % nextNode.name)
            return nextNode, False

        if node.parent is not None and self._hasSize(node.parent):
            #Debug(1, "_nextNodeOrSizedParent: Found sized parent, this is the last element")
            return node.parent, True

        #Debug(1, "_nextNodeOrSizedParent: Calling _nextNodeOrSizedParent on parent!")
        return self._nextNodeOrSizedParent(node.parent)


    def _nextNode(self, node):
        """
        Locate the next node.

        1. Do we have a .nextSibling?
        2. Does are parent have .nextSibling?
        ...

        Need to also support escaping Choice blocks!
        """

        if node is None:
            return None

        #try:
        #	Debug(1, "_nextNode(%s)" % node.name)
        #
        #except:
        #	Debug(1, "_nextNode: %s" % repr(node))
        #	raise

        if not isinstance(node, Peach.Engine.dom.DataElement) or\
           node.elementType == 'template':
            #Debug(1, "_nextNode: not data element or is template")

            return None

        # Try and escape Choice blocks.
        while node.parent is not None and node.parent.elementType == 'choice':
            if node.parent.maxOccurs > 1:
                #Debug(1, "_nextNode: Returning node.parent due to maxOccurs > 1.")
                return node.parent

            node = node.parent

        nextNode = node.nextSibling()
        while nextNode is not None and not isinstance(nextNode, Peach.Engine.dom.DataElement):
            nextNode = nextNode.nextSibling()

        if nextNode is not None and isinstance(nextNode, Peach.Engine.dom.DataElement):
            #Debug(1, "_nextNode(): Found: %s" % nextNode.name)
            return nextNode

        #Debug(1, "_nextNode(): Calling _nextNode on parent!")
        return self._nextNode(node.parent)

    def _adjustRating(self, rating, lookAheadRating):
        if lookAheadRating == 2 and rating == 1:
            rating = 2
        elif rating < 3 and lookAheadRating > 2:
            return rating - 1
        elif rating == 3 and lookAheadRating > 3:
            return rating - 1

        return rating

    def _handleChoice(self, node, buff, pos, parent, doingMinMax=False):
        Debug(1, "---> %s (%d)" % (node.name, self.parentPos + pos))

        # Default is failure
        rating = 4
        curpos = pos
        newpos = pos
        node.currentElement = None

        # Our list can shrink/expand as we go
        # so lets copy the list up front.
        children = []
        for child in node._children:
            if isinstance(child, DataElement):
                children.append(child)

        # Look for first child that matches, forget the rest.
        for child in children:
            # Skip any children created during array expantion
            # they should already have values 'n all that good
            # stuff :)
            if hasattr(child, 'array') and child.array is not None:
                continue

            # Try this child

            Debug(1, "_handleChoice(): Trying child [%s]" % child.name)

            fastCheck, fastCheckOffset, fastCheckValue = child.choiceCache

            # Check and see if we need to read more data for check
            if fastCheck and len(fastCheckValue) > (len(buff.data) - (pos + fastCheckOffset)):
                # Need to read some data in if posssible
                if buff.haveAllData:
                    Debug(1, "_handleChoice(): FastCheck: Not enough data to match, NEXT!")
                    continue

                else:
                    size = len(fastCheckValue) - (len(buff.data) - (pos + fastCheckOffset))
                    buff.read(size)
                    if len(fastCheckValue) > (len(buff.data) - (pos + fastCheckOffset)):
                        Debug(1, "_handleChoice(): FastCheck: Not enough data to match, NEXT!")
                        continue

            if fastCheck and buff.data[
                             pos + fastCheckOffset:pos + fastCheckOffset + len(fastCheckValue)] != fastCheckValue:
                Debug(1, "_handleChoice(): FastCheck: [%s] != [%s] NEXT!" % (
                    buff.data[pos + fastCheckOffset:pos + len(fastCheckValue)], fastCheckValue))
                continue

            # Before we actually do this we need to emulate this as the only child.
            node.choice__children = node._children
            node.choice__childrenHash = node._childrenHash
            node.choice_children = node.children
            node._children = []
            node._childrenHash = {}
            node.children = Empty()
            node.append(child)

            (childRating, newpos) = self._handleNode(child, buff, curpos)
            if child.currentValue is not None and len(child.currentValue) > 30:
                Debug(1, "_handleChoice(): Rating: (%d) [%s]: %s = [%s]" % (
                    childRating, highlight.repr(repr(child.defaultValue)), child.name, child.currentValue[:30]))
            else:
                Debug(1, "_handleChoice(): Rating: (%d) [%s]: %s = [%s]" % (
                    childRating, highlight.repr(repr(child.defaultValue)), child.name, child.currentValue))

            # Now lets move it all back
            node._children = node.choice__children
            node._childrenHash = node.choice__childrenHash
            node.children = node.choice_children
            node.choice__children = None
            node.choice__childrenHash = None
            node.choice_children = None

            # Check if we are keeping this child or not
            if childRating > 2:
                Debug(1, "_handleChoice(): Child did not meet requirements, NEXT!")
                continue

            # Keep this child
            Debug(1, "_handleChoice(): Keeping child [%s]" % child.name)
            node.currentElement = child
            rating = childRating
            curpos = newpos

            # TODO: Lets not remove the kids, but for now to keep things
            #       simple, we will look like a block after this so to
            #       speek.
            for c in children:
                if c != node.currentElement:
                    Debug(1, "_handleChoice(): Removing unused child [%s]" % c.name)
                    node.__delitem__(c.name)

            break

        #Debug(1, "Choice rating: %d" % rating)
        if rating < 4:
            Debug(1, highlight.ok("CHOICE RATING: %d" % rating))
        if rating == 4:
            Debug(1, highlight.error("CHOICE RATING: %d" % rating))
        Debug(1, "<--- %s (%d through %d)" % (node.name, self.parentPos + pos, self.parentPos + newpos))

        if rating < 3:
            node.pos = pos
            node.rating = rating

        return rating, curpos

    def _handleBlock(self, node, buff, pos, parent, doingMinMax=False):
        # Not going to handle alignment right now :)

        Debug(1, "---> %s (%d)" % (node.name, self.parentPos + pos))

        rating = 0
        ratingCnt = 0
        ratingTotal = 0
        curpos = pos

        # Our list can shrink/expand as we go
        # so lets copy the list up front.
        children = []
        for child in node._children:
            children.append(child)

        for child in children:
            if not isinstance(child, DataElement) and not isinstance(child, Seek):
                continue

            # Skip any children created during array expantion
            # they should already have values 'n all that good
            # stuff :)
            if hasattr(child, 'array') and child.array is not None:
                continue

            # Do the needfull

            ratingCnt += 1

            (childRating, newpos) = self._handleNode(child, buff, curpos)
            if child is not None and child.currentValue is not None and len(child.currentValue) > 30:
                if child.defaultValue is not None and len(repr(child.defaultValue)) > 30:
                    Debug(1, "_handleBlock(%s): Rating: (%d) [%s]: %s = [%s]" % (
                        node.name, childRating, highlight.repr(repr(child.defaultValue)[:30]), child.name,
                        child.currentValue[:30]))
                else:
                    Debug(1, "_handleBlock(%s): Rating: (%d) [%s]: %s = [%s]" % (
                        node.name, childRating, highlight.repr(repr(child.defaultValue)), child.name,
                        child.currentValue[:30]))
            else:
                if child.defaultValue is not None and len(repr(child.defaultValue)) > 30:
                    Debug(1, "_handleBlock(%s): Rating: (%d) [%s]: %s = [%s]" % (
                        node.name, childRating, highlight.repr(repr(child.defaultValue)[:30]), child.name,
                        repr(child.currentValue)))
                else:
                    Debug(1, "_handleBlock(%s): Rating: (%d) [%s]: %s = [%s]" % (
                        node.name, childRating, highlight.repr(repr(child.defaultValue)), child.name,
                        repr(child.currentValue)))

            if childRating > 2:
                Debug(1, "_handleBlock(%s): Child rating sucks, exiting" % node.name)
                rating = childRating
                break

            ratingTotal += childRating
            if childRating > rating:
                rating = childRating

            curpos = newpos


        #Debug(1, "BLOCK RATING: %d" % rating)
        if rating < 4:
            Debug(1, highlight.ok("BLOCK RATING: %d" % rating))
        if rating == 4:
            Debug(1, highlight.error("BLOCK RATING: %d" % rating))

        Debug(1, "<--- %s (%d)" % (node.name, self.parentPos + pos))

        if rating < 3:
            node.pos = pos
            node.rating = rating

        return rating, curpos

    def _getDataFromFullname(self, dom, name):
        """
        Take a fullname (blah.blah.blah) and locate
        it in our data dom.
        """
        dom = self._getRootParent(dom)
        obj = dom

        for part in name.split('.'):
            Debug(2, "_getDataFromFullname(%s): [%s]" % (name, obj.name))
            if part == obj.name:
                continue

            obj = obj[part]

        return obj[obj.name]

    def _handleString(self, node, buff, pos, parent, doingMinMax=False):
        """
        Returns the rating and string.  The rating is
        how well we matched.

        Rating:

        1 - BEST	If our default matched and look ahead is 1
        2 - GOOD	If our default matched and look ahead is 2
        3 - OK		If our look ahead is 1 or 2
        4 - MPH		If look ahead is 3 or 4
        """

        # We just break from this to return values
        while True:
            Debug(1, "---> %s (%d)" % (node.name, self.parentPos + pos))

            self.deepString += 1

            rating = 0
            newpos = 0
            length = None

            # If we are static we should know our
            # length.
            if node.length is None and node.isStatic:
                try:
                    node.length = len(node.defaultValue)
                except:
                    raise PeachException(
                        "Error: String %s doens't have a default value, yet is marked isStatic." % node.name)

            # Determin if we have a size-of relation
            # and set our length accordingly.
            relation = node.getRelationOfThisElement('size')
            if relation is not None and relation.type == 'size':
                # we have a size-of relation
                Debug(1, "** FOUND SIZE OF RELATION ***")

                fullName = relation.parent.getFullname()
                Debug(1, "Size-of Fullname: " + fullName)

                length = relation.getValue(True)
                Debug(1, "Size-of Length: %s" % length)

                # Value may not be available yet
                try:
                    length = int(length)
                except:
                    pass

            # Do we know our length?
            if node.getLength() is not None or length is not None:
                if length is None:
                    length = node.getLength()

                # If we are null terminated add on to length
                # Urm...!
                if node.nullTerminated:
                    length += 1

                Debug(1, "_handleString: Found length of: %d" % length)

                if node.type == 'wchar':
                    length *= 2

                if len(buff.data) < (pos + length):
                    if not buff.haveAllData:
                        try:
                            buff.read((pos + length) - len(buff.data))

                            # Just make sure that buff.read actually worked.
                            if len(buff.data) < (pos + length):
                                raise Exception("Why didn't that throw???")

                        except:
                            rating = 4
                            value = ""
                            newpos = pos + length
                            Debug(1, "_handleString: Want %d, have %d" % ((pos + length), len(buff.data)))
                            break

                    else:
                        rating = 4
                        value = ""
                        newpos = pos + length
                        Debug(1, "_handleString: Want %d, have %d" % ((pos + length), len(buff.data)))
                        break

                if len(buff.data) >= (pos + length):
                    value = buff.data[pos:pos + length]
                    newpos = pos + length
                    defaultValue = node.defaultValue
                    rating = 2

                    if node.nullTerminated and node.type != 'wchar':
                        if value[-1] != '\0':
                            # Failed to locate null!
                            Debug(1, "%s_handleString: %s: Null not found!" % ('\t' * self.deepString, node.name))
                            rating = 4
                        else:
                            value = value[:-1]

                    elif node.nullTerminated and node.type == 'wchar':
                        if value[-1] != '\0' and value[-2] != '\0':
                            # Failed to locate null!
                            Debug(1, "%s_handleString: %s: Null not found!" % ('\t' * self.deepString, node.name))
                            rating = 4
                        else:
                            value = value[:-2]

                    if node.isStatic:
                        if node.type == 'wchar':
                            # convert to ascii string
                            defaultValue = node.defaultValue.decode("utf-16le")

                        # Handle padding
                        if node.length != len(defaultValue):
                            defaultValue += node.padCharacter * (node.length - len(defaultValue))

                        if value != defaultValue and node.isStatic:
                            Debug(1, "%s_handleString: %s: Bad match, static, but default didn't match [%s != %s]" % (
                                '\t' * self.deepString, node.name, repr(value), repr(defaultValue)))
                            rating = 4

                        else:
                            Debug(1, "%s_handleString: %s: By length [%s]" % (
                                '\t' * self.deepString, node.name, repr(value)))
                            rating = 1

                    break

                raise Exception("We should not be here!")

            # Are we null terminated?
            elif node.nullTerminated:
                value = ''

                newpos = pos
                rating = 666

                if node.type != 'wchar':
                    newpos = -1
                    while True:
                        newpos = buff.data.find('\0', pos)

                        if newpos == -1:
                            if buff.haveAllData:
                                rating = 4
                                value = ''
                                newpos = pos
                                break

                            else:
                                try:
                                    buff.read(1)
                                except:
                                    rating = 4
                                    value = ''
                                    newpos = pos
                                    break

                        else:
                            break

                    if rating == 666:
                        newpos += 1    # find leaves us a position down, need to add one to get the null
                        value = buff.data[pos:newpos]
                        rating = 2

                    break

                elif node.type == 'wchar':
                    newpos = buff.data.find("\0\0", pos)
                    while newpos == -1:
                        if not buff.haveAllData:
                            try:
                                buff.read(1)
                            except:
                                pass

                        elif buff.haveAllData:
                            rating = 4
                            newpos = pos
                            value = ''
                            Debug(1, "data.find(00) returned -1, pos: %d" % pos)
                            break

                        newpos = buff.data.find("\0\0", pos)

                    if rating != 666:
                        break

                    if newpos == pos:
                        Debug(1, "Found empty terminated wchar string: [%s]" % repr(value))
                        value = ""
                        newpos += 2
                        rating = 2
                        break

                    newpos += 3 # find leaves us a position down, need to add one to get the null
                    value = buff.data[pos:newpos - 2]
                    rating = 2

                    if len(value) % 2 != 0:
                        value += '\0'

                    if value == '\0' or value == '\0\0':
                        value = ""

                    # HACK for WCHAR
                    for i in range(1, len(value), 2):
                        if value[i] != '\0':
                            value = value[:i] + '\0' + value[i + 1:]

                    for i in range(0, len(value), 2):
                        if ord(value[i]) > 127:
                            value = value[:i] + 'a' + value[i + 1:]

                    Debug(1, "Found null terminated wchar string: [%s]" % repr(value))
                    Debug(1, "pos: %d; newpos: %d" % (pos, newpos))

                    break

            elif node.isStatic:
                # first, look for our defaultValue
                if node.defaultValue is None:
                    raise PeachException("Error: %s is marked as static but has no default value." % node.name)

                Debug(1, "%s_handleString: %s: Found default value, doing checks" % ('\t' * self.deepString, node.name))

                if node.type == 'wchar':
                    defaultValue = node.defaultValue.decode("utf-16le")

                else:
                    defaultValue = node.defaultValue

                newpos = pos + len(defaultValue)
                value = buff.data[pos:newpos]
                if value == defaultValue:
                    rating = 2
                    break

                else:
                    rating = 4
                    Debug(1, "%s_handleString: %s: No match [%s == %s] @ %d" % (
                        '\t' * self.deepString, node.name, repr(buff.data[newpos:newpos + len(defaultValue)]),
                        repr(defaultValue), pos))
                    break

            else:
                # If we don't have a length, we try for a best fit
                # by adjusting the position until our look ahead has a rating
                # of 1 or 2.

                # Are we the last data element?
                if self._nextNode(node) is None:
                    if not buff.haveAllData:
                        buff.readAll()

                    # Keep all the data :)
                    Debug(1, "_handleString: Have all data, keeping it for me :)")
                    value = buff.data[pos:]
                    newpos = len(buff.data)
                    rating = 1

                elif self._isTokenNext(node) is not None:
                    # Is there an isStatic ahead?

                    staticNode, length = self._isTokenNext(node)

                    Debug(1, "_handleString: self._isTokenNext(%s): %s" % (node.name, staticNode.name))

                    # 1. Locate staticNode position
                    val = staticNode.getValue()
                    Debug(1, "Looking for [%s][%s]" % (repr(val), repr(buff.data[pos:])[:50]))
                    valPos = buff.data[pos:].find(val)
                    while valPos == -1:
                        if buff.haveAllData:
                            newpos = pos
                            value = ""
                            rating = 4
                            Debug(1, " :( Have all data")
                            break

                        try:
                            buff.read(1)
                        except:
                            newpos = pos
                            value = ""
                            rating = 4
                            Debug(1, " :( Have all data")
                            break

                        valPos = buff.data[pos:].find(val)

                    if rating == 4:
                        break

                    # 2. Subtract length
                    newpos = (pos + valPos) - length

                    # 3. Yuppie!
                    value = buff.data[pos:newpos]
                    rating = 1

                    Debug(1, "Found: [%d][%d:%d][%s]" % (length, self.parentPos + pos, self.parentPos + newpos, value))

                elif self._isLastUnsizedNode(node) is not None:
                    # Are all other nodes of deterministic size?

                    Debug(1, "_handleString: self._isLastUnsizedNode(node)")

                    if not buff.haveAllData:
                        buff.readAll()

                    length = self._isLastUnsizedNode(node)
                    newpos = len(buff.data) - length
                    value = buff.data[pos:newpos]
                    rating = 1

                #elif self._isConstraintNext(node) != None:
                ## Is there a constraint ahead?

                #constraintNode, length = self._isConstraintNext(node)

                #Debug(1, "_handleString: self._isConstraintNext(%s): %s" % (node.name, constraintNode.name))
                ##
                ### 1. Locate staticNode position
                ##val = constraintNode.getValue()
                ##Debug(1, "Looking for [%s][%s]" % (repr(val), repr(buff.data[pos:])))
                ##valPos = buff.data[pos:].find(val)
                ##while valPos == -1:
                ##	if buff.haveAllData:
                ##		newpos = pos
                ##		value = ""
                ##		rating = 4
                ##		Debug(1, " :( Have all data")
                ##		break
                ##
                ##	try:
                ##		buff.read(1)
                ##	except:
                ##		newpos = pos
                ##		value = ""
                ##		rating = 4
                ##		Debug(1, " :( Have all data")
                ##		break
                ##
                ##	valPos = buff.data[pos:].find(val)
                ##
                ##if rating == 4:
                ##	break
                ##
                ### 2. Subtract length
                ##newpos = (pos+valPos) - length
                ##
                ### 3. Yuppie!
                ##value = buff.data[pos:newpos]
                ##rating = 1
                ##
                ##Debug(1, "Found: [%d][%d:%d][%s]" % (length, self.parentPos+pos, self.parentPos+newpos, value))


                else:
                    Debug(1, "_handleString: No size for our string.")

                    # Will will suckup bytes one by one check the
                    # look ahead each time to see if we should keep
                    # sucking.
                    #
                    # Note: Turns out running the lookAhead each time is slow.

                    lookRating = 666
                    newpos = pos
                    dataLen = len(buff.data)

                    # If we have a following static just scan
                    # for it instead of calling lookAhead.
                    nextNode = self._nextNode(node)
                    if nextNode.isStatic:
                        nextValue = nextNode.getValue()
                        nextValueLen = len(nextValue)

                        newpos = buff.data.find(nextValue, pos)
                        while newpos == -1:
                            if buff.haveAllData:
                                value = ""
                                rating = 4
                                break

                            try:
                                buff.read(1)
                            except:
                                value = ""
                                rating = 4
                                break

                            newpos = buff.data.find(nextValue, pos)

                        if rating == 4:
                            break

                        value = buff.data[pos:newpos]
                        rating = 2
                        break

                    # This loop is slow! Reading one char at a time!
                    # We should try a reading at least 2-5 chars at once.
                    while lookRating > 2 and newpos < dataLen:
                        newpos += 1
                        lookRating = self._lookAhead(node, buff, newpos, parent)

                    value = buff.data[pos:newpos]

                    if lookRating > 2:
                        rating = 3

                    else:
                        rating = 2

                    break

            break

        # Deal with wchar
        if node.type == 'wchar':
            try:
                value = value.decode("utf-16le")
            except:
                print("Error decoding: %r", value)
                raise

        # contraint
        if node.constraint is not None and rating < 3:
            env = {
                "self": node,
                "pos": pos,
                "newpos": newpos,
                "value": value,
            }

            if not evalEvent(node.constraint, env, node):
                rating = 4
                newpos = pos
                Debug(1, "_handleString: %s" % highlight.error("Constraint failed"))
            else:
                Debug(1, "_handleString: %s" % highlight.ok("Constraint passed"))

        # Set value
        if rating < 3:
            eval("node.%s(value)" % self.method)

        # Are we last?
        if self._nextNode(node) is None:
            # Are we in an array
            obj = node
            inArray = False
            while obj.parent is not None and isinstance(obj.parent, DataElement):
                if obj.maxOccurs > 1:
                    inArray = True
                    break

                obj = obj.parent

            # Note: If doingMinMax then we can't
            # assume we should eat all data even
            # if we are the last node!
            #
            # Note2: maxOccurs can lie if we are doingMinMax!
            #
            if newpos < len(buff.data) and not inArray and not doingMinMax:
                # We didn't use it all up, sad for us!
                Debug(1, "--- Didn't use all data, rating == 4")
                rating = 4

        # Return values

        Debug(1, "<--- %s (%d, %d-%d)" % (node.name, rating, self.parentPos + pos, self.parentPos + newpos))

        if rating < 3:
            node.pos = pos
            node.rating = rating

        self.deepString -= 1
        return rating, newpos

    def _handleNumber(self, node, buff, pos, parent, doingMinMax=False):
        """
        Handle Number.  Return (rating, newpos, value) in tuple.

        Rating:

        1 - BEST	If our default matched and look ahead is 1
        2 - GOOD	If our default matched and look ahead is 2
        3 - OK		If our look ahead is 1 or 2
        4 - MPH		If look ahead is 3 or 4

        """

        Debug(1, "---> %s (%d)" % (node.name, self.parentPos + pos))

        node.rating = 0
        length = node.size / 8

        # See if we have enough data

        if (pos + length) > len(buff.data):
            # need more
            try:
                buff.read((pos + length) - len(buff.data))
            except:
                Debug(1, "_handleNumber(): Read failed: %s" % repr(sys.exc_info()))
                pass

            if (pos + length) > len(buff.data):
                node.rating = None
                return 4, pos

        # Get value based on element length

        value = buff.data[pos:pos + length]
        newpos = pos + length

        # Build format string

        fmt = ''

        if node.endian == 'little':
            fmt = '<'
        else:
            fmt = '>'

        if node.size == 8:
            fmt += 'b'
        elif node.size == 16:
            fmt += 'h'
        #print "Number: %x %x" % (ord(value[0]), ord(value[1]))
        elif node.size == 24:
            fmt += 'i'

            if node.endian == 'little':
                value += '\0'
            else:
                value = '\0' + value

        elif node.size == 32:
            fmt += 'i'
        elif node.size == 64:
            fmt += 'q'

        if not node.signed:
            fmt = fmt.upper()

        # Unpack value

        value = str(struct.unpack(fmt, value)[0])

        # Adjust rating based on defaultValue

        if node.isStatic:
            if value != str(node.defaultValue):
                Debug(1, "_handleNumber: Number is static but did not match, failing. [%s] != [%s]" % (
                    value, node.defaultValue))
                node.rating = 4
            else:
                Debug(1, "_handleNumber: Number is static and matched. [%s] == [%s]" % (value, node.defaultValue))
                node.rating = 1
        else:
            node.rating = 2

        # contraint
        if node.constraint is not None:
            env = {
                "self": node,
                "value": int(value),
                "pos": pos,
                "newpos": newpos,
            }

            if not evalEvent(node.constraint, env, node):
                node.rating = 4
                newpos = pos
                Debug(1, "_handleString: %s" % highlight.error("Constraint failed"))
            else:
                Debug(1, "_handleString: %s" % highlight.ok("Constraint passed"))

        # Set value on data element
        if node.rating < 3:
            eval("node.%s(value)" % self.method)

            # Return all of it
            node.pos = pos

        Debug(1, "<--- %s (%d, %d-%d)" % (node.name, node.rating, self.parentPos + pos, self.parentPos + newpos))
        return node.rating, newpos

    def flipBitsByByte(self, num, size):
        ret = 0
        for n in self.splitIntoBytes(num, size):
            ret <<= 8
            ret += n

        return ret

    def splitIntoBytes(self, num, size):
        ret = []
        for i in range(size / 8):
            ret.append(num & 0xFF)
            num >>= 8

        return ret

    def _handleFlags(self, node, buff, pos, parent, doingMinMax=False):
        """
        Returns the rating and string.  The rating is
        how well we matched.

        Rating:

        1 - BEST	If our default matched and look ahead is 1
        2 - GOOD	If our default matched and look ahead is 2
        3 - OK		If our look ahead is 1 or 2
        4 - MPH		If look ahead is 3 or 4
        """

        Debug(1, "---> %s (%d)" % (node.name, self.parentPos + pos))

        rating = 0
        length = node.length / 8

        if (pos + length) > len(buff.data):
            # need more
            try:
                buff.read((pos + length) - len(buff.data))
            except:
                pass

            if (pos + length) > len(buff.data):
                node.rating = None
                return 4, pos

        value = buff.data[pos:pos + length]
        newpos = pos + length

        if node.padding:
            # Now, unpack the integer

            fmt2 = '>'
            if node.endian == 'little' and not node.rightToLeft:
                fmt = '<'
            elif node.endian == 'little' and node.rightToLeft:
                fmt = '>'

            elif node.endian == 'big' and node.rightToLeft:
                fmt = '<'
            elif node.endian == 'big' and not node.rightToLeft:
                fmt = '>'

            else:
                raise Exception("Error, unable to determine endian for unpack")

            if node.length == 8:
                fmt += 'B'
                fmt2 += 'B'
            elif node.length == 16:
                fmt += 'H'
                fmt2 += 'H'
            elif node.length == 32:
                fmt += 'I'
                fmt2 += 'I'
            elif node.length == 64:
                fmt += 'Q'
                fmt2 += 'Q'

            value = int(struct.unpack(fmt, value)[0])
            value = struct.pack(fmt2, value)

            if node.endian == 'little' and not node.rightToLeft:
                bits = BitBuffer(value, True)
            elif node.endian == 'little' and node.rightToLeft:
                bits = BitBuffer(value, False)

            elif node.endian == 'big' and node.rightToLeft:
                bits = BitBuffer(value, False)
            elif node.endian == 'big' and not node.rightToLeft:
                bits = BitBuffer(value, True)

        else:
            bits = BitBuffer(value, node.endian == 'big')

        rating = 2

        for child in node._children:
            if child.elementType != 'flag':
                continue

            bits.seek(child.position)
            childValue = bits.readbits(child.length)

            Debug(1, "Found child flag %s value of %s" % (child.name, str(childValue)))

            if child.isStatic:
                Debug(1, "Child flag is token %s must eq %s" % (str(childValue), str(child.defaultValue)))
                if str(child.defaultValue) != str(childValue):
                    Debug(1, "Child flag token match failed, setting rating to 4")
                    rating = 4
                    break

                Debug(1, "Child flag token matched!")

            # Set child node value
            eval("child.%s(childValue)" % self.method)
            child.rating = 2
            child.pos = pos
            ##print "[%s] child value:" % child.name, child.getInternalValue()


        # contraint
        if rating >= 2 and node.constraint is not None:
            env = {
                "self": node,
                "pos": pos,
                "newpos": newpos,
            }

            if not evalEvent(node.constraint, env, node):
                rating = 4
                newpos = pos
                Debug(1, "_handleString: %s" % highlight.error("Constraint failed"))
            else:
                Debug(1, "_handleString: %s" % highlight.ok("Constraint passed"))

        Debug(1, "<--- %s (%d, %d-%d)" % (node.name, rating, self.parentPos + pos, self.parentPos + newpos))

        node.pos = pos
        node.rating = rating
        return rating, newpos

    def binaryFormatter(self, num, bits):
        ret = ""
        for i in range(bits - 1, -1, -1):
            ret += str((num >> i) & 1)

        assert len(ret) == bits
        return ret


    def _handleSeek(self, node, buff, pos, parent, doingMinMax=False):
        """
        Handle a Seek element
        """

        Debug(1, "---> SEEK FROM %d" % (self.parentPos + pos))

        # 1. Get the position to jump to

        newpos = node.getPosition(pos, len(buff.data), buff.data)

        # 2. Can we jump there?

        if newpos > buff.data:
            # a. Do we have all the data?
            if not buff.haveAllData:
                # Request more
                try:
                    buff.read((pos + newpos) - len(buff.data))
                except:
                    pass

            if newpos > buff.data:
                # Bad rating
                Debug(1, "<--- SEEK TO %d FAILED, ONLY HAVE %d" % (newpos, len(buff.data)))
                return 4, pos

        elif newpos < 0:
            Debug(1, "<--- SEEK TO %d FAILED, NEGATIVE NOT POSSIBLE" % newpos)
            return 4, pos

        # 3. Jump there!

        Debug(1, "<--- SEEK TO %d" % newpos)
        return 1, newpos

    def _handleCustom(self, node, buff, pos, parent, doingMinMax=False):
        """
        Returns the rating and string.  The rating is
        how well we matched.

        Rating:

        1 - BEST	If our default matched and look ahead is 1
        2 - GOOD	If our default matched and look ahead is 2
        3 - BAD
        4 - BAD
        """

        Debug(1, "---> %s (%d)" % (node.name, self.parentPos + pos))

        rating, newpos = node.handleIncoming(self, buff, pos, parent, doingMinMax)

        # contraint
        if node.constraint is not None and rating < 3:
            env = {
                "self": node,
                "data": buff.data,
                "pos": pos,
                "newpos": newpos,
            }

            if not evalEvent(node.constraint, env, node):
                rating = 4
                newpos = pos
                Debug(1, "_handleString: %s" % highlight.error("Constraint failed"))
            else:
                Debug(1, "_handleString: %s" % highlight.ok("Constraint passed"))

        if rating < 3:
            node.pos = pos
            node.rating = rating

        Debug(1, "<--- %s (%d)" % (node.name, self.parentPos + newpos))
        return rating, newpos

    def _handleBlob(self, node, buff, pos, parent, doingMinMax=False):
        """
        Returns the rating and string.  The rating is
        how well we matched.

        Rating:

        1 - BEST	If our default matched and look ahead is 1
        2 - GOOD	If our default matched and look ahead is 2
        3 - OK		If our look ahead is 1 or 2
        4 - MPH		If look ahead is 3 or 4
        """

        Debug(1, "---> %s (%d)" % (node.name, self.parentPos + pos))

        rating = 0
        newpos = 0
        length = None
        hasSizeofRelation = False
        length = None

        # Determin if we have a size-of relation
        # and set our length accordingly.
        relation = node.getRelationOfThisElement('size')
        if relation is not None and relation.type == 'size':
            # we have a size-of relation
            Debug(1, "** FOUND SIZE OF RELATION ***")

            fullName = relation.parent.getFullname()
            Debug(1, "Size-of Fullname: " + fullName)

            length = relation.getValue(True)
            Debug(1, "Size-of Length: %s" % length)

            # We might not be ready to get this
            # value yet (look head), but try
            try:
                length = int(length)
            except:
                pass
        else:
            Debug(1, "_handleBlob: No relation found")

        # Do we know our length?
        if node.getLength() is not None or length is not None:
            Debug(1, "_handleBlob: Has length")

            if length is None:
                length = node.getLength()

            if (pos + length) > len(buff.data):
                if not buff.haveAllData:
                    try:
                        buff.read((pos + length) - len(buff.data))
                    except:
                        pass

            if (pos + length) > len(buff.data):
                Debug(1, "_handleBlob: Not enough data, rating = 4: %d left" % (len(buff.data) - pos))
                rating = 4

            else:
                value = buff.data[pos:pos + length]
                newpos = pos + length
                rating = 2

                if value == node.defaultValue:
                    rating = 1

                elif node.isStatic:
                    rating = 4

        else:
            Debug(1, "_handleBlob: No length found")
            # If we don't have a sizeof relation, we try for a best fit
            # by adjusting the position until our look ahead has a rating
            # of 1 or 2.

            # Are we the last data element?
            if self._nextNode(node) is None:
                #print "--- Last element, snafing it all :)"
                buff.readAll()
                value = buff.data[pos:]
                newpos = len(buff.data)
                rating = 1
            elif self._isLastUnsizedNode(node) is not None:
                # Are all other nodes of deterministic size?
                Debug(1, "_handleBlob: self._isLastUnsizedNode(node)")
                buff.readAll()
                length = self._isLastUnsizedNode(node)
                newpos = len(buff.data) - length
                value = buff.data[pos:newpos]
                rating = 1

            elif self._isTokenNext(node) is not None:
                # Is there an isStatic ahead?
                staticNode, length = self._isTokenNext(node)
                Debug(1, "_handleBlob: self._isTokenNext(%s): %s" % (node.name, staticNode.name))
                valPos = -1
                if isinstance(staticNode, Choice):
                    for n in staticNode:
                        Debug(1, "Looking from choice for [%s][%s]" % (repr(n.choiceCache[2]), repr(buff.data[pos:])))
                        valPos = buff.data[pos:].find(n.choiceCache[2])
                        if valPos != -1:
                            break
                    if valPos == -1:
                        newpos = pos
                        value = ""
                        rating = 4
                        Debug(1, "Unable to find choice branch in look ahead")
                else:
                    # 1. Locate staticNode position
                    val = staticNode.getValue()
                    Debug(1, "Looking for [%s][%s]" % (repr(val), repr(buff.data[pos:])[:150]))
                    valPos = buff.data[pos:].find(val)
                    while valPos == -1:
                        if buff.haveAllData:
                            newpos = pos
                            value = ""
                            rating = 4
                            Debug(1, " :( Have all data")
                            break
                        try:
                            buff.read(1)
                        except:
                            pass
                        valPos = buff.data[pos:].find(val)
                if valPos != -1:
                    # 2. Subtract length
                    newpos = (pos + valPos) - length
                    # 3. Yuppie!
                    value = buff.data[pos:newpos]
                    rating = 1
                    Debug(1, "Found: [%d][%d:%d][%s]" % (length, self.parentPos + pos, self.parentPos + newpos, value))
            else:
                #if buff.haveAllData:
                #	print "--- Was not last node"

                lookRating = 666
                newpos = pos

                # If we have a following static just scan
                # for it instead of calling lookAhead.
                nextNode = self._nextNode(node)
                if nextNode.isStatic:
                    nextValue = nextNode.getValue()
                    nextValueLen = len(nextValue)
                    newpos = buff.data.find(nextValue, pos)
                    while newpos != -1:
                        if buff.haveAllData:
                            rating = 4
                            value = ""
                            newpos = pos
                            break
                        try:
                            buff.read(1)
                        except:
                            pass
                        newpos = buff.data.find(nextValue, pos)
                    if newpos != -1:
                        value = buff.data[pos:newpos]
                        rating = 2
                else:
                    # Lets try and remove all _lookAhead calls.
                    raise PeachException("Error, unable to determine size of blob [%s] while cracking." %
                                         node.getFullname())
                    while lookRating > 2 and newpos < len(buff.data):
                        #Debug(1, ".")
                        newpos += 1
                        lookRating = self._lookAhead(node, buff, newpos, parent)
                        #Debug(1, "newpos: %d lookRating: %d data: %d" % (newpos, lookRating, len(data)))
                    while lookRating <= 2 and newpos < len(buff.data):
                        #Debug(1, ",")
                        newpos += 1
                        lookRating = self._lookAhead(node, buff, newpos, parent)
                        if lookRating > 2:
                            newpos -= 1
                            #Debug(1, "newpos: %d lookRating: %d data: %d" % (newpos, lookRating, len(data)))
                    #if newpos >= len(data):
                    #	newpos -= 1
                    #	#raise str("Unable to parse out blob %s" % node.name)
                    value = buff.data[pos:newpos]
                    rating = 2
                    #print "Found blob: [%s]" % value

        # contraint
        if node.constraint is not None:
            env = {
                "self": node,
                "value": value,
                "pos": pos,
                "newpos": newpos,
            }
            if not evalEvent(node.constraint, env, node):
                rating = 4
                newpos = pos
                Debug(1, "_handleString: %s" % highlight.error("Constraint failed"))
            else:
                Debug(1, "_handleString: %s" % highlight.ok("Constraint passed"))
        if rating < 3:
            eval("node.%s(value)" % self.method)
        Debug(1, "<--- %s (%d, %d-%d)" % (node.name, rating, self.parentPos + pos, self.parentPos + newpos))
        node.pos = pos
        node.rating = rating
        return rating, newpos


class NeedMoreData(object):
    def __init__(self, amount, msg):
        self.amount = amount
        self.msg = "[%d] %s]" % (amount, msg)

    def __str__(self):
        return self.msg


def printDom(node, level=0):
    tabs = '\t' * level
    if node.currentValue is not None:
        Debug(1, tabs + "%s: [%s]" % (node.name, node.currentValue))
    else:
        Debug(1, tabs + "%s" % node.name)
    try:
        for child in node._children:
            printDom(child, level + 1)
    except:
        pass
