# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


class Fixup(object):
    """
    Fixup of values in the data model. This is done by keeping an internal
    list of references that can be resolved during fixup(). Helper functions
    are provided in this base class for resolving elements in the data model.
    """

    def __init__(self):
        self.context = None
        self.is_in_self = False

    def do_fixup(self):
        """Wrapper around fixup() to prevent endless recursion."""
        if not self.is_in_self:
            try:
                self.is_in_self = True
                return self.fixup()
            finally:
                self.is_in_self = False

    def _getRef(self):
        """
        After incoming data is cracked some elements move around. Peach will
        auto update parameters called "ref" but you will need to re-fetch the
        value using this method.
        """
        for param in self.context.fixup:
            if param.name == "ref":
                return eval(param.defaultValue)

    def fixup(self):
        """Performs the required fixup."""
        raise Exception("Fixup not implemented yet!")
