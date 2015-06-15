# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from Peach.strategy import *


class StaticStrategy(Strategy):

    def __init__(self, stateMachine, routeDescriptor, params=None):
        Strategy.__init__(self, stateMachine, routeDescriptor)

    def _findRoute(self, start, destination):
        if destination is None:
            return [start]
        return [start, destination]
