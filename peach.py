#!/usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
import os
import re
import sys
import time
import random
import atexit
import logging
import argparse
import tempfile
import subprocess

import twisted
from lxml import etree

from Peach.Engine.engine import *
from Peach.Engine.common import *
from Peach.analyzer import Analyzer
from Peach.Analyzers import *
from Peach.agent import Agent

p = os.path.dirname(os.path.abspath(sys.executable))
sys.path.append(p)
sys.path.append(os.path.normpath(os.path.join(p, "..")))
sys.path.append(".")

peach_pids = []

@atexit.register
def cleanup():
    try:
        Engine.context.watcher.watchers[-1].OnCrashOrBreak()
    except:
        pass
    for pidfile in peach_pids:
        try:
            os.remove(pidfile)
        except OSError:
            pass


def save_peach_pid(agent=False):
    pid = os.getpid()
    filename = os.path.join(tempfile.gettempdir(), 'peach.%s%d' % ('' if not agent else 'agent.', pid))
    with open(filename, 'w') as fd:
        fd.write(str(pid))
    peach_pids.append(filename)


def fatal(msg):
    logging.error(highlight.error(msg))
    sys.exit(-1)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Peach Runtime')
    parser.add_argument('-pit', metavar='path', help='pit file')
    parser.add_argument('-run', metavar='name', help='run name')
    parser.add_argument('-analyzer', nargs="+", help='load analyzer.')
    parser.add_argument('-parser', help='use specific parser.')
    parser.add_argument('-target', help='select a target pit.')
    parser.add_argument('-macros', nargs='+', default=tuple(), help='override configuration macros')
    parser.add_argument('-seed', metavar='#', default=time.time(), help='seed')
    parser.add_argument('-debug', action='store_true', help='turn on debugging. (default: %(default)s)')
    parser.add_argument('-new', action='store_true', help='use new relations.')
    parser.add_argument('-1', dest='single', action='store_true', help='run single test case.')
    parser.add_argument('-range', nargs=2, type=int, metavar='#', help='run range of test cases.')
    parser.add_argument('-test', action='store_true', help='validate pit file.')
    parser.add_argument('-count', action='store_true', help='count test cases for deterministic strategies.')
    parser.add_argument('-skipto', metavar='#', type=int, help='skip to a test case number.')
    parser.add_argument('-parallel', nargs=2, metavar=('#', '#'), help='use parallelism.')
    parser.add_argument('-agent', nargs=2, metavar=('#', '#'), help='start agent.')
    parser.add_argument('-logging', metavar='#', default=20, type=int, choices=range(10, 60, 10),
                        help='verbosity level of logging')
    parser.add_argument('-check', nargs=2, metavar=('model', 'samples'),
                        help='validate a data model against a set of samples.')
    parser.add_argument('-verbose', action='store_true',
                        help='turn verbosity on. (default: %(default)s)') # Use -vvv action=count
    parser.add_argument('-clean', action='store_true', help='remove python object files.')
    parser.add_argument('-version', action='version', version='%(prog)s 1.0')
    args = parser.parse_args()

    logging.basicConfig(format='[Peach.%(name)s] %(message)s', level=args.logging)

    if args.pit and not args.pit.startswith('file:'):
        args.pit = 'file:' + args.pit
    if args.target and not args.target.startswith('file:'):
        args.target = 'file:' + args.target

    args.configs = {}
    for mac in args.macros:
        k, v = mac.split('=', 1)
        args.configs[k.strip()] = v.strip()
    args.configs['_target'] = args.pit
    args.pit = args.target

    args.watcher = None
    args.restartFile = None
    peachrun = Engine()
    peachrun.configs = args.configs
    peachrun.SEED = args.seed
    random.seed(peachrun.SEED)

    if args.debug:
        Engine.debug = True

    if args.clean:
        if sys.platform == "darwin" or sys.platform == "linux2":
            subprocess.call(["find", ".", "-name", ".DS_Store", "-delete"])
            subprocess.call(["find", ".", "-name", "*.pyc", "-delete"])
        elif sys.platform == "win32":
            subprocess.call(["del", "/S", "*.pyc"])
        sys.exit(0)

    if args.analyzer:
        try:
            cls = eval("%s()" % args.analyzer[0])
        except Exception as e:
            fatal("Loading analyzer failed: {}".format(e))
        if hasattr(cls, "supportCommandLine"):
            logging.info("Using %s as analyzer class." % args.analyzer[0])
            a = {}
            for pair in args.analyzer[1:]:
                key, val = pair.split("=")
                a[key] = val
            try:
                cls.asCommandLine(a)
            except Exception as e:
                fatal(e)
        else:
            fatal("Analyzer does not support command line usage.")
        sys.exit(0)

    if args.parser:
        try:
            cls = eval(args.parser)
        except Exception as e:
            fatal("Loading parser class failed: {}".format(e))
        if hasattr(cls, "supportParser"):
            logging.info("Using {} as parser.".format(args.parser))
            args.parser = cls()
        else:
            fatal("Analyzer does not support parser usage.")
    else:
        args.parser = PitXmlAnalyzer()
    args.parser.configs = args.configs

    if args.new:
        Engine.relationsNew = True

    if args.check and args.pit:
        from Peach.Engine.incoming import DataCracker
        dataModelName = args.check[0]
        samplesPath = args.check[1]
        samples = []
        if os.path.isdir(samplesPath):
            for fp in os.listdir(samplesPath):
                samples.append(os.path.join(samplesPath, fp))
        else:
            samples = glob.glob(samplesPath)
        peach = args.parser.asParser(args.pit)
        dataModel = peach.templates[dataModelName]
        for sample in samples:
            dataModel = peach.templates[dataModelName].copy(peach)
            with open(sample, "rb") as fd:
                data = fd.read()
            buff = PublisherBuffer(None, data, True)
            cracker = DataCracker(peach)
            cracker.optmizeModelForCracking(dataModel, True)
            cracker.crackData(dataModel, buff)
            if dataModel.getValue() == data:
                result = highlight.ok("passed")
            else:
                result = highlight.error("failed")
            logging.info("[%s] cracking: '%s'" % (result, sample))
        logging.info("Done.")
        sys.exit(0)

    if args.single:
        logging.info("Performing a single iteration.")
        Engine.justOne = True

    if args.range:
        if args.range[0] < 0:
            fatal("Count for start must be positive.")
        if args.range[0] >= args.range[1]:
            fatal("Range must be 1 or larger.")
        logging.info("Performing tests from {} -> {}".format(args.range[0], args.range[1]))
        Engine.testRange = args.range

    if args.parallel:
        if args.parallel[0] < 1:
            fatal("Machine count must be >= 2.")
        if args.parallel[0] <= args.parallel[1]:
            fatal("The total number of machines must be less than current machine.")
        logging.debug("Parallel total machines: {}".format(args.parallel[0]))
        logging.debug("Parallel our machine   : {}".format(args.parallel[1]))

    if not args.pit and not args.agent:
        logging.error("You must provide a pit or an agent.")
        sys.exit(-1)

    if args.test:
        try:
            args.parser.asParser(args.pit)
            logging.debug(highlight.ok("File parsed without errors."))
        except PeachException as e:
            logging.exception(e.msg)
        except etree.LxmlError as e:
            logging.exception("An error occurred while parsing the XML file: {}".format(e))
        except:
            raise
        sys.exit(0)

    if args.count:
        try:
            peachrun.Count(args.parser.asParser(args.pit), args.run)
        except PeachException as e:
            logging.error("Counting test cases only works with deterministic strategies.")
            fatal(e)
        sys.exit(0)

    if args.agent:
        save_peach_pid(agent=True)
        try:
            port = int(args.agent[0])
        except ValueError as e:
            fatal("Agent port is not a valid number.")
        password = args.agent[1]
        try:
            logging.info("Attempting to start Agent ...")
            agent = Agent(password, port)
        except twisted.internet.error.CannotListenError as e:
            fatal(e)
        sys.exit(0)
    else:
        save_peach_pid(agent=False)

    logging.info("Using random seed: %s" % peachrun.SEED)
    try:
        peachrun.Run(args)
    except PeachException as e:
        logging.exception(e.msg)
    except etree.LxmlError as e:
        logging.exception("An error occurred while parsing the XML file: {}".format(e))
    except:
        raise
    finally:
        if DomBackgroundCopier.copyThread is not None:
            DomBackgroundCopier.stop.set()
            DomBackgroundCopier.needcopies.set()
            DomBackgroundCopier.copyThread.join()
            DomBackgroundCopier.copyThread = None
