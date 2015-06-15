# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
import atexit
import logging

from common import Highlight

#  The engine component does the following:
#
#   1. Accepts a peach XML and parses it
#   2. Configures watchers, loggers
#   3. Connects to Agents and spins up Monitors
#   4. Runs each defined test
#      a. Notifies Agents
#      b. Calls State Engine

class Empty(object):
    pass


class EngineWatcher(object):
    """
    Base for a class that receives callback when events occur in the Peach Engine.
    """

    def setTotalVariations(self, totalVariations):
        self.totalVariations = totalVariations

    def OnCrashOrBreak(self):
        """
        Called on crash or interrupt.
        """
        pass

    def OnRunStarting(self, run):
        """
        Called when a run is starting.
        """
        pass

    def OnRunFinished(self, run):
        """
        Called when a run is finished.
        """
        pass

    def OnTestStarting(self, run, test, totalVariations):
        """
        Called on start of a test. Each test has multiple variations.
        """
        pass

    def OnTestFinished(self, run, test):
        """
        Called on completion of a test.
        """
        pass

    def OnTestCaseStarting(self, run, test, variationCount):
        """
        Called on start of a test case.
        """
        pass

    def OnStateEnter(self, state):
        """
        Called as we enter a state
        """
        pass

    def OnStateExit(self, state):
        """
        Called as we exit a state
        """
        pass

    def OnActionStart(self, action):
        """
        Called as we start an action
        """
        pass

    def OnActionComplete(self, action):
        """
        Called after we completed action
        """
        pass

    def OnTestCaseReceived(self, run, test, variationCount, value):
        """
        Called when data is received from test case.
        """
        pass

    def OnTestCaseException(self, run, test, variationCount, exception):
        """
        Called when an exception occurs during a test case.
        """
        pass

    def OnTestCaseFinished(self, run, test, variationCount, actionValues):
        """
        Called when a test case has completed.
        """
        pass

    def OnFault(self, run, test, variationCount, monitorData, value):
        """
        Called when a fault occurred.
        """
        pass

    def OnStopRun(self, run, test, variationCount, monitorData, value):
        """
        Called when the run stopped.
        """
        pass


class EngineWatchPlexer(EngineWatcher):
    """
    Allows multiple watchers to be attached and will distribute messages out to them.
    """

    def __init__(self):
        self.watchers = []

    def setTotalVariations(self, totalVariations):
        for w in self.watchers:
            w.setTotalVariations(totalVariations)

    def OnRunStarting(self, run):
        for w in self.watchers:
            w.OnRunStarting(run)

    def OnRunFinished(self, run):
        for w in self.watchers:
            w.OnRunFinished(run)

    def OnTestStarting(self, run, test, totalVariations):
        for w in self.watchers:
            w.OnTestStarting(run, test, totalVariations)

    def OnTestFinished(self, run, test):
        for w in self.watchers:
            w.OnTestFinished(run, test)

    def OnTestCaseStarting(self, run, test, variationCount):
        for w in self.watchers:
            w.OnTestCaseStarting(run, test, variationCount)

    def OnTestCaseReceived(self, run, test, variationCount, value):
        for w in self.watchers:
            w.OnTestCaseReceived(run, test, variationCount, value)

    def OnTestCaseException(self, run, test, variationCount, exception):
        for w in self.watchers:
            w.OnTestCaseException(run, test, variationCount, exception)

    def OnTestCaseFinished(self, run, test, variationCount, actionValues):
        for w in self.watchers:
            w.OnTestCaseFinished(run, test, variationCount, actionValues)

    def OnFault(self, run, test, variationCount, monitorData, value):
        for w in self.watchers:
            w.OnFault(run, test, variationCount, monitorData, value)

    def OnStateEnter(self, state):
        for w in self.watchers:
            w.OnStateEnter(state)

    def OnStateExit(self, state):
        for w in self.watchers:
            w.OnStateExit(state)

    def OnActionStart(self, action):
        for w in self.watchers:
            w.OnActionStart(action)

    def OnActionComplete(self, action):
        for w in self.watchers:
            w.OnActionComplete(action)

    def OnStopRun(self, run, test, variationCount, monitorData, value):
        for w in self.watchers:
            w.OnStopRun(run, test, variationCount, monitorData, value)


class StdoutWatcher(EngineWatcher):
    """
    This is the default console interface to Peach it prints out information as tests are performed.
    """

    def OnRunStarting(self, run):
        logging.info('Starting run "%s".' % run.name)

    def OnRunFinished(self, run):
        logging.info('Run "%s" completed.' % run.name)

    def OnTestStarting(self, run, test, totalVariations):
        self.startTime = None
        self.startVariationCount = None
        self.remaingTime = "?"
        self.totalVariations = totalVariations
        logging.info('Test "%s" (%s) is starting.' % (test.name, test.description))

    def OnTestFinished(self, run, test):
        logging.info('Test "%s" completed.' % test.name)

    def OnTestCaseStarting(self, run, test, variationCount):
        prefix = "Heartbeat: %d-%s-%s " % (variationCount, self.totalVariations, self.remaingTime)
        logging.info(prefix + "Element: %s Mutator: %s" % (test.mutator.currentMutator().changedName, test.mutator.currentMutator().name))
        if self.startTime is None and variationCount > 1:
            self.startTime = time.time()
            self.startVariationCount = variationCount
        try:
            if variationCount % 20 == 0:
                count = variationCount - (self.startVariationCount - 1)
                elaps = time.time() - self.startTime
                perTest = elaps / count
                remaining = (int(self.totalVariations) - variationCount) * perTest
                self.remaingTime = str(int((remaining / 60) / 60)) + "hrs"
                if count > 5000:
                    self.startTime = time.time()
                    self.startVariationCount = variationCount
        except:
            pass

    def OnTestCaseReceived(self, run, test, variationCount, value):
        if Engine.verbose:
            print("[%d:%s:%s] Received data: %s" %
                  (variationCount, self.totalVariations, self.remaingTime, repr(value)))
        else:
            print("[%d:%s:%s] Received data" %
                  (variationCount, self.totalVariations, self.remaingTime))

    def OnTestCaseException(self, run, test, variationCount, exception):
        print("[%d:%s:%s] Caught error on receive, ignoring [%s]" %
              (variationCount, self.totalVariations, self.remaingTime, exception))
        return True

    def OnTestCaseFinished(self, run, test, variationCount, actionValues):
        pass


class Engine(object):
    """
    The high level Peach engine.
    The main entry point is Run() which consumes a Peach XML file and performs the fuzzing run.
    """

    debug = False
    relationsNew = False
    justOne = False
    nativeDeepCopy = True
    testRange = None
    context = None

    def __init__(self):
        self.restartFile = None
        self.restartState = None
        self.verbose = False
        self.peach = None
        self.agent = None
        self._agents = {}
        self.startNum = None
        self.configs = {}
        Engine.verbose = False
        Engine.context = self

    def Count(self, peach, runName=None):
        """
        Count the tests of a run.

        @type	uri: String
        @param	uri: URI specifying the filename to use.  Must have protocol prepended (file:, http:, etc)
        @type	runName: String
        @param	runName: Name of run or if None, "DefaultRun" is used.
        """
        self.watcher = EngineWatchPlexer()
        self.peach = peach
        self.agent = AgentPlexer()
        self._agents = {}
        runName = "DefaultRun" if runName is None else runName
        if hasattr(self.peach.runs, runName):
            run = getattr(self.peach.runs, runName)
        else:
            raise PeachException("Can not find <Run> with name %s." % runName)
        totalCount = 0
        for test in run.tests:
            testCount = self._countTest(run, test, True)
            totalCount += testCount
            logging.info("Test with name %s has %d test cases." % (test.name, testCount))
        logging.info("Total test cases for run with name %s is %d." % (runName, totalCount))
        return totalCount

    def Run(self, args):
        runName = "DefaultRun" if args.run is None else args.run
        self.restartFile = args.restartFile
        self.restartState = None
        self.verbose = args.verbose
        Engine.verbose = args.verbose
        if args.pit.find(":") >= 0:
            self.pitFile = args.pit[args.pit.find(":") + 1:]
        else:
            self.pitFile = args.pit
        if self.pitFile.find("/") >= 0:
            self.pitFile = os.path.basename(self.pitFile)
        self.peach = args.parser.asParser(args.pit)
        run = None
        self.agent = AgentPlexer()
        self._agents = {}
        self.startNum = args.skipto
        self.watcher = EngineWatchPlexer()
        if args.watcher is None:
            self.watcher.watchers.append(StdoutWatcher())
        else:
            self.watcher.watchers.append(args.watcher)
        if hasattr(self.peach.runs, runName):
            run = getattr(self.peach.runs, runName)
        else:
            raise PeachException("Can not find run with name %s." % runName)
        loggers = run.getLoggers()
        if loggers is not None:
            for logger in loggers:
                self.watcher.watchers.append(logger)
        try:
            self.watcher.OnRunStarting(run)
        except TypeError as t:
            print(t)
            print(dir(self.watcher))
            print(dir(self.watcher.OnRunStarting))
            raise t
        skipToTest = False
        if self.restartFile is not None:
            logging.info("[Restarting] Loading state file %s." % self.restartFile)
            with open(self.restartFile, "rb+") as fd:
                self.restartState = pickle.loads(fd.read())
            skipToTest = True
            skipToTestName = self.restartState[0]
        if args.parallel is None:
            for test in run.tests:
                self._runPathTest(run, test)
            for test in run.tests:
                if skipToTest and test.name != skipToTestName:
                    continue
                elif skipToTest and test.name == skipToTestName:
                    skipToTest = False
                self._runTest(run, test, False, self.testRange)
        else:
            logging.info("Configuring run with name %s." % runName)
            if len(run.tests) > 1:
                raise PeachException("Only a single test per-run is currently supported for parallel fuzzing.")
            totalMachines = int(args.parallel[0])
            thisMachine = int(args.parallel[1])
            test = run.tests[0]
            # 1. Get our total count. We want to use a copy of everything so we don't pollute the DOM!
            peach = args.parser.asParser(args.pit)
            totalCount = self._countTest(getattr(peach.runs, runName), getattr(peach.runs, runName).tests[0])
            # 2. How many tests per machine?
            perCount = int(totalCount / totalMachines)
            leftOver = totalCount - (perCount * totalMachines)
            # 3. How many for this machine?
            startCount = thisMachine * perCount
            thisCount = perCount
            if thisMachine == totalMachines - 1:
                thisCount += leftOver
            logging.info("This machine will perform chunk %d through %d out of %d total" %
                  (startCount, startCount + thisCount, totalCount))
            self._runTest(run, test, False, [startCount, startCount + thisCount])
        self.watcher.OnRunFinished(run)

    def _startAgents(self, run, test):
        """
        Start up agents listed in test.
        """
        for agent in test:
            if agent.elementType != 'agent':
                continue
            if agent.location == 'local':
                server = "."
            else:
                server = agent.location
            agent_object = self.agent.AddAgent(agent.name, server, agent.password, agent.getPythonPaths(),
                                               agent.getImports(), self.configs)
            self._agents[agent.name] = agent_object
            for monitor in agent:
                if monitor.elementType == 'monitor':
                    agent_object.StartMonitor(monitor.name, monitor.classStr, monitor.params)

    def _stopAgents(self, run, test):
        self.agent.OnShutdown()

    def _countTest(self, run, test, verbose=False):
        """
        Get the total test count of this test
        """
        logging.info("Peach will now count the total amount of test cases, please wait.")
        mutator = self._runTest(run, test, True)
        count = 0 if mutator is None else mutator.getCount()
        if count is None:
            raise PeachException("An error occurred counting total tests.")
        logging.info("Count completed, found %d possible tests." % count)
        return count

    def _runTest(self, run, test, countOnly=False, testRange=None):
        """
        Runs a Test as defined in the Peach XML.

        @type	run: Run object
        @param	run: Run that test is part of
        @type	test: Test object
        @param	test: Test to run
        @type	countOnly: bool
        @param	countOnly: Should we just get total mutator count? Defaults to False.
        @type	testRange: list of numbers
        @param	testRange: Iteration # test ranges.  Only used when performing parallel fuzzing.

        @rtype: number
        @return: the total number of test iterations or None
        """
        stateMachine = test.stateMachine
        stateEngine = StateEngine(self, stateMachine, test.publishers)
        totalTests = "?"
        testCount = 0
        self._startAgents(run, test)
        if not countOnly:
            self.watcher.OnTestStarting(run, test, totalTests)
        for p in test.publishers:
            p.initialize()
        errorCount = 0
        maxErrorCount = 10
        # Get all the mutators we will use
        self.mutators = []
        for m in test.getMutators():
            try:
                self.mutators.append(eval(m.name))
            except:
                try:
                    self.mutators.append(evalEvent("PeachXml_" + m.name, {}, run))
                except:
                    raise PeachException(
                        "Unable to load mutator [%s], please verify it was imported correctly." % m.name)
        mutator = test.mutator
        value = "StateMachine"
        if self.restartState is not None:
            logging.info("State will load in 1 iteration.")
        elif testRange is not None:
            logging.info("Skipping to start of chunk in 1 iteration.")
        # Needs to be off on its own!
        startCount = None
        endCount = None
        if testRange is not None:
            startCount = testRange[0]
            endCount = testRange[1]
        if self.startNum is not None:
            startCount = self.startNum
        redoCount = 0
        saveState = False
        exitImmediate = False
        actionValues = None
        try:
            while True:
                try:
                    testCount += 1
                    # What if we are just counting?
                    if testCount == 2 and countOnly:
                        self._stopAgents(run, test)
                        return mutator
                    # Go through one iteration before we load state.
                    elif testCount == 2 and self.restartState is not None:
                        logging.info("Restoring state.")
                        testCount = self.restartState[1]
                        mutator.setState(self.restartState[2])
                    elif testCount == 2 and startCount is not None and startCount > 2:
                        # Skip ahead to start range, but not if we are restoring saved state.
                        logging.info("Skipping ahead to iteration %d." % startCount)
                        #testCount -= 1
                        for _ in range(testCount, startCount):
                            mutator.next()
                            testCount += 1
                    # Update total test count
                    if testRange is None:
                        totalTests = mutator.getCount()
                    else:
                        # If we are parallel use our endCount which will also cause the estimated time
                        # left to be correct.
                        totalTests = endCount + 1
                    if totalTests == -1 or totalTests is None:
                        totalTests = "?"
                    else:
                        self.watcher.setTotalVariations(totalTests)
                    # Fire some events
                    self.agent.OnTestStarting()
                    if not countOnly:
                        self.watcher.OnTestCaseStarting(run, test, testCount)
                    self.testCount = testCount
                    mutator.onTestCaseStarting(test, testCount, stateEngine)
                    # Run the test
                    try:
                        actionValues = stateEngine.run(mutator)
                    except RedoTestException:
                        raise
                    except MemoryError:
                        # Some tests cause out of memeory exceptions, let skip past them.
                        logging.warning("Out of memory, going to next test.")
                        pass
                    except OverflowError:
                        # Some tests cause out of memeory exceptions, let skip past them.
                        logging.warning("Out of memory, going to next test.")
                        pass
                    except SoftException as e:
                        # In the case of the first iteration we should never fail.
                        if testCount == 1:
                            raise PeachException("Error: First test case failed: ", e)
                        # Otherwise ignore any SoftExceptions and head for next iteration.
                        pass
                    # Pause as needed
                    time.sleep(run.waitTime)
                    mutator.onTestCaseFinished(test, testCount, stateEngine)
                    # Notify
                    if not countOnly:
                        self.watcher.OnTestCaseFinished(run, test, testCount, actionValues)
                    self.agent.OnTestFinished()
                    # Should we repeat this test?
                    if self.agent.RedoTest():
                        logging.warning(highlight.warning("Repeating test"))
                        raise RedoTestException()
                    if self.agent.DetectedFault():
                        logging.warning(highlight.warning("Detected fault! Processing data..."))
                        results = self.agent.GetMonitorData()
                        mutator.onFaultDetected(test, testCount, stateEngine, results, actionValues)
                        self.watcher.OnFault(run, test, testCount, results, actionValues)
                        self.agent.OnFault()
                    # Check for stop event
                    if self.agent.StopRun():
                        logging.warning(highlight.warning("Detected StopRun, bailing!"))
                        self.watcher.OnStopRun(run, test, testCount, None, actionValues)
                        break
                    # Increment our mutator
                    mutator.next()
                    # Reset the redoCounter
                    redoCount = 0
                except RedoTestException as e:
                    if redoCount == 3:
                        raise PeachException(e.message)
                    redoCount += 1
                    testCount -= 1
                except PathException:
                    # Ignore PathException while running tests
                    mutator.next()
                except SoftException:
                    mutator.next()
                # Have we completed our range?
                if (testRange is not None and testCount > endCount) or \
                        (Engine.justOne and startCount is None) or \
                        (Engine.justOne and startCount == testCount):
                    logging.info("Completed iteration range.")
                    break
        except MutatorCompleted:
            pass
        except KeyboardInterrupt:
            logging.warning("User canceled run.")
            saveState = True
            exitImmediate = True
        except PeachException as e:
            if e.msg.find("Unable to reconnect to Agent") > -1:
                results = {
                    "_Bucket": "AgentConnectionFailed"
                }
                self.watcher.OnFault(run, test, testCount, results, actionValues)
            raise
        except:
            # Always save state on exceptions
            saveState = True
            self.watcher.OnTestCaseException(run, test, testCount, None)
            raise
        finally:
            try:
                for publisher in test.publishers:
                    if hasattr(publisher, "hasBeenConnected") and publisher.hasBeenConnected:
                        publisher.close()
                        publisher.hasBeenConnected = False
                    if hasattr(publisher, "hasBeenStarted") and publisher.hasBeenStarted:
                        publisher.stop()
                        publisher.hasBeenStarted = False
                    publisher.finalize()
            except:
                pass
            self._stopAgents(run, test)
        if not countOnly:
            self.watcher.OnTestFinished(run, test)

    def _runPathTest(self, run, test):
        stateMachine = test.stateMachine
        # If no path declaration found then simply skip the validation
        if not len(stateMachine.getRoute()):
            return
        logging.info("Running path validation test for %s." % test.name)
        try:
            stateEngine = StateEngine(self, stateMachine, test.publishers)
            # Create a path validator to check basic validation rules
            mutator = PathValidationMutator()
            pathValidator = PathValidator(stateEngine.pathFinder, mutator)
            try:
                actionValues = stateEngine.run(mutator)
                print("Traced route: ")
                print(" - ".join(["%s" % str(stateName) for stateName in mutator.states]))
                pathValidator.validate()
            except PathException as e:
                raise PeachException(str(e))
        except PeachException as e:
            logging.error("End of path validation test : Validation failed!")
            raise e
        else:
            logging.info("End of path validation test : Successfully passed")


import os, time, pickle, tempfile

from Peach.Engine.state import StateEngine
from Peach.Engine.common import *
from Peach.Engine.common import SoftException
from Peach.Engine.path import *
from Peach.agent import AgentPlexer
from Peach.mutatestrategies import *
from Peach.MutateStrategies import *
from Peach.analyzer import Analyzer
from Peach.Analyzers import *
from Peach.Mutators import *
from Peach.Mutators.path import *
