# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
import os
import uuid
import subprocess
import re
import atexit
import shutil
import logging
import shlex

from Peach.Utilities import network


def getInstanceProvider(name):
    if name not in globals():
        raise Exception("Invalid instance provider in configuration: " + name)
    return globals()[name]


class FirefoxProfile(object):
    instances = {}

    def __init__(self, identifier, config):
        firefox_binary = shlex.split(config["DefaultBrowser"])
        self.profile_name = identifier + "-" + str(uuid.uuid4())
        output = subprocess.check_output(firefox_binary + 
                                         ['-no-remote',
                                          '-CreateProfile', self.profile_name],
                                         stderr=subprocess.STDOUT)
        output = output.strip()
        if "Success: created profile" not in output:
            raise Exception("Unexpected output while creating Firefox profile: %s" % output)
        self.profile_prefs_path = re.findall("'.+?'", output)[1].strip("'")
        pref_path = config['DefaultFirefoxPrefs']
        logging.debug(self.profile_prefs_path)
        shutil.copyfile(pref_path, self.profile_prefs_path)
        logging.debug("Successfully created temporary Firefox profile at %s" % self.profile_prefs_path)

    @staticmethod
    def getInstanceById(identifier, config):
        if identifier not in FirefoxProfile.instances:
            FirefoxProfile.instances[identifier] = FirefoxProfile(identifier, config)
        return FirefoxProfile.instances[identifier]

    @staticmethod
    @atexit.register
    def cleanInstances():
        for instance in FirefoxProfile.instances.values():
            instance.destroy()

    def __repr__(self):
        return self.profile_name

    def destroy(self):
        if self.profile_prefs_path.endswith('/prefs.js'):
            profile_path = os.path.dirname(self.profile_prefs_path)
            logging.debug("Deleting temporary Firefox profile at %s" % profile_path)
            shutil.rmtree(profile_path)


class TCPPort(object):
    instances = {}

    def __init__(self, identifier, config):
        self.port_number = network.getUnboundPort(assignOnlyOnce=True)
        if self.port_number < 0:
            raise Exception("Unable to allocate free TCP port")

    @staticmethod
    def getInstanceById(identifier, config):
        if identifier not in TCPPort.instances:
            TCPPort.instances[identifier] = TCPPort(identifier, config)
        return TCPPort.instances[identifier]

    def __repr__(self):
        return str(self.port_number)
