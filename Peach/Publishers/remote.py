# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from Peach.Engine.engine import Engine
from Peach.publisher import *


class RemotePublisher(Publisher):
    """
    Load a publisher on a remote Agent
    """

    def __init__(self, agentName, name, cls, *args):
        Publisher.__init__(self)
        self._agentName = agentName
        self._name = name
        self._cls = cls
        self._args = args
        self._initialized = False

    def start(self):
        if not self._initialized:
            self._agent = Engine.context.agent[self._agentName]
            self._agent.PublisherInitialize(self._name, self._cls, self._args)
            self._initialized = True

        self._agent.PublisherStart(self._name)

    def stop(self):
        self._agent.PublisherStop(self._name)

    def send(self, data):
        self._agent.PublisherSend(self._name, data)

    def receive(self, size=None):
        self._agent.PublisherReceive(self._name, size)

    def call(self, method, args):
        self._agent.PublisherCall(self._name, method, args)

    def property(self, property, value=None):
        self._agent.PublisherProperty(self._name, value)

    def connect(self):
        self._agent.PublisherConnect(self._name)

    def accept(self):
        self._agent.PublisherAccept(self._name)

    def close(self):
        self._agent.PublisherClose(self._name)
