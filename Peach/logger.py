# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
import os
import sys
import uuid
import socket
import base64
import logging
import subprocess
try:
    # Python 2
    import xmlrpclib
except ImportError:
    # Python 3
    import xmlrpc.client as xmlrpclib
from time import *

from Peach.Engine.engine import EngineWatcher
from Peach.Engine.engine import Engine
from Peach.Utilities.common import *


class Logger(EngineWatcher):
    """
    Parent class for all logger implementations.
    """

    def OnCrashOrBreak(self):
        """
        Called when we are exiting due to crash or Ctrl+BREAK/Ctrl+C.
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
        Called on start of a test.  Each test has multiple variations.
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
        pass

    def OnStopRun(self, run, test, variationCount, monitorData, value):
        pass


class Filesystem(Logger):
    """
    A file system logger.
    """

    def __init__(self, params):
        self.name = str(uuid.uuid1())
        self.elementType = 'logger'
        self.params = params
        self.heartBeat = 512
        self.file = None
        self.lastTestCount = 0
        self.firstIter = True

    def _writeMsg(self, line):
        self.file.write(asctime() + ": " + line + "\n")
        self.file.flush()

    def OnCrashOrBreak(self):
        """
        Called when we are exiting due to crash or Ctrl+BREAK/Ctrl+C.
        """
        if self.file is not None:
            self._writeMsg("FORCED EXIT OR CRASH!")
            self._writeMsg("Last test #: %d" % self.lastTestCount)

    def OnRunStarting(self, run):
        suppliedPath = str(self.params['path']).replace("'''", "")
        pitFile = os.path.splitext(os.path.basename(Engine.context.pitFile))[0]

        self.path = os.path.join(suppliedPath, pitFile + "." + run.name + "_" + strftime("%Y-%j_%H-%M-%S", localtime()))

        self.faultPath = os.path.join(self.path, "Faults")
        try:
            os.makedirs(suppliedPath)
        except:
            pass
        try:
            os.mkdir(self.path)
        except:
            pass

        if self.file is not None:
            self.file.close()

        self.file = open(os.path.join(self.path, "status.txt"), "w")

        self.file.write("Peach Fuzzer Run\n")
        self.file.write("=================\n\n")
        self.file.write("Command line: ")
        for arg in sys.argv:
            self.file.write("%s " % arg)
        self.file.write("\n")

        self.file.write("Date of run: " + asctime() + "\n")

        if Engine.context.SEED is not None:
            self.file.write("SEED: %s\n" % Engine.context.SEED)

        self.file.write("Pit File: %s\n" % pitFile)
        self.file.write("Run name: " + run.name + "\n\n")

        self.lastTestCount = 0
        self.firstIter = True


    def OnRunFinished(self, run):
        self.file.write("\n\n== Run completed ==\n" + asctime() + "\n")
        self.file.close()
        self.file = None
        self.lastTestCount = 0

    def OnTestStarting(self, run, test, totalVariations):
        self._writeMsg("")
        self._writeMsg("Test starting: " + test.name)
        #self._writeMsg("Test has %d variations" % totalVariations)
        self._writeMsg("")
        self.firstIter = True

    def OnTestFinished(self, run, test):
        self._writeMsg("")
        self._writeMsg("Test completed: " + test.name)
        self._writeMsg("")

    def OnTestCaseException(self, run, test, variationCount, exception):
        pass

    def OnFault(self, run, test, variationCount, monitorData, actionValues):
        self._writeMsg("Fault was detected on test %d" % variationCount)

        # Look for Bucket information
        bucketInfo = None
        for key in monitorData.keys():
            if key.find("_Bucket") > -1:
                bucketInfo = monitorData[key]
                break

        # Build folder structure
        try:
            os.mkdir(self.faultPath)
        except:
            pass

        if bucketInfo is not None:
            logging.debug("BucketInfo:", bucketInfo)

            bucketInfos = bucketInfo.split(os.path.sep)
            path = self.faultPath
            for p in bucketInfos:
                path = os.path.join(path, p)
                try:
                    os.mkdir(path)
                except:
                    pass

            path = os.path.join(path, str(variationCount))
            try:
                os.mkdir(path)
            except:
                pass

        else:
            try:
                path = os.path.join(self.faultPath, "Unknown")
                os.mkdir(path)
            except:
                pass

            path = os.path.join(self.faultPath, "Unknown", str(variationCount))

        try:
            os.mkdir(path)
        except:
            pass

        # Expand actionValues

        for i in range(len(actionValues)):
            fileName = os.path.join(path, "data_%d_%s_%s.txt" % (i, actionValues[i][1], actionValues[i][0]))

            if len(actionValues[i]) > 2:
                fout = open(fileName, "w+b")
                fout.write(actionValues[i][2])

                if len(actionValues[i]) > 3 and actionValues[i][1] != 'output':
                    fout.write(repr(actionValues[i][3]))

                fout.close()

                # Output filename from data set if we have it.
                if len(actionValues[i]) > 3 and actionValues[i][1] == 'output':
                    self._writeMsg("Original file name: " + actionValues[i][3])

                    fileName = os.path.join(path,
                                            "data_%d_%s_%s_fileName.txt" % (i, actionValues[i][1], actionValues[i][0]))
                    fout = open(fileName, "w+b")
                    fout.write(actionValues[i][3])
                    fout.close()

        for key in monitorData.keys():
            if key.find("_Bucket") == -1:
                fout = open(os.path.join(path, key), "wb")
                fout.write(monitorData[key])
                fout.close()

    def OnStopRun(self, run, test, variationCount, monitorData, value):
        self._writeMsg("")
        self._writeMsg("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        self._writeMsg("!!!! TEST ABORTING AT %d" % variationCount)
        self._writeMsg("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        self._writeMsg("")

    def OnTestCaseStarting(self, run, test, variationCount):
        """
        Called on start of a test case.
        """
        if self.firstIter or variationCount > (self.lastTestCount + 1) or variationCount % self.heartBeat == 0:
            self._writeMsg("On test variation # %d" % variationCount)
            self.firstIter = False
        self.lastTestCount = variationCount


class KeyValue(object):
    def __init__(self, key=None, value=None):
        self.key = key
        self.value = value

try:
    import json
    import StringIO
    import zipfile
    import tempfile
    import platform
    sys.path.append("Peach/Utilities/FuzzManager")
    from FTB.ProgramConfiguration import ProgramConfiguration
    from FTB.Signatures.CrashInfo import CrashInfo
    from Collector.Collector import Collector
except ImportError as ex:
    print("FuzzManager is missing or one of its dependencies: %s" % ex)

try:
    class FuzzManager(Logger):
        def __init__(self, args):
            self.args = args

            self.name = str(uuid.uuid1())
            self.elementType = 'logger'
            self.heartBeat = 512
            self.maxRetry = 10
            self.waitRetry = 2.0
            self.totalVariations = 0

            self.target_binary = getStringAttribute(self.args, "TargetBinary")

        def OnRunStarting(self, run):
            pass

        def OnStopRun(self, run, test, variationCount, monitorData, value):
            pass

        def OnRunFinished(self, run):
            pass

        def OnTestStarting(self, run, test, totalVariations):
            pass

        def OnTestCaseStarting(self, run, test, variationCount):
            pass

        def OnTestFinished(self, run, test):
            pass

        def OnTestCaseException(self, run, test, variationCount, exception):
            pass

        def _get_value_by_key(self, data, name, alt=None):
            if not alt:
                alt = ""
            v = [v for k, v in data.items() if k.endswith(name)]
            if not len(v):
                return alt
            return v[0]

        def OnFault(self, run, test, variationCount, monitorData, actionValues):
            # Setup FuzzManager with information about target and platform data.
            program_configuration = ProgramConfiguration.fromBinary(self.target_binary)

            # Prepare FuzzManager with target and crash information.
            stdout = self._get_value_by_key(monitorData, "stdout.txt", "N/A")
            stderr = self._get_value_by_key(monitorData, "stderr.txt", "N/A")
            auxdat = self._get_value_by_key(monitorData, "auxdat.txt", "N/A")

            crash_info = CrashInfo.fromRawCrashData(stdout, stderr, program_configuration, auxdat)

            collector = Collector(tool="peach")

            # Write testcase content and any additional meta information to a temporary ZIP archive.
            buffer = StringIO.StringIO()
            zip_buffer = zipfile.ZipFile(buffer, 'w')

            # Collect |actionValues| crash information from Peach.
            for i in range(len(actionValues)):
                if len(actionValues[i]) > 2:
                    data = actionValues[i][2]
                    fileName = "data_%d_%s_%s.txt" % (i, actionValues[i][1], actionValues[i][0])
                    zip_buffer.writestr(fileName, data)

                    if len(actionValues[i]) > 3 and actionValues[i][1] != 'output':
                        data = repr(actionValues[i][3])
                        fileName = "data_%d_%s_%s_action.txt" % (i, actionValues[i][1], actionValues[i][0])
                        zip_buffer.writestr(fileName, data)

                    if len(actionValues[i]) > 3 and actionValues[i][1] == 'output':
                        fileName = "data_%d_%s_%s_fileName.txt" % (i, actionValues[i][1], actionValues[i][0])
                        data = actionValues[i][3]
                        zip_buffer.writestr(fileName, data)

            # Collect |monitorData| crash information from Peach.
            for k, v in monitorData.items():
                zip_buffer.writestr(k, v)

            zip_buffer.close()
            with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as testcase:
                buffer.seek(0)
                testcase.write(buffer.getvalue())
                testcase.close()
                # Submit crash report with testcase to FuzzManager.
                collector.submit(crash_info, testcase.name, metaData=None)

        def OnCrashOrBreak(self):
            pass

except Exception:
    print("FuzzManager is deactivated!")

