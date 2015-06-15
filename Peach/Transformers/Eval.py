# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from Peach.transformer import Transformer
from Peach import transformer


class Eval(Transformer):
    """Eval a statement.
    Utility transformer for when all else fails.
    """

    _eval = None

    def __init__(self, eval, anotherTransformer=None):
        transformer.Transformer.__init__(self, anotherTransformer)
        self._eval = eval

    def realEncode(self, data):
        return eval(self._eval % data)
