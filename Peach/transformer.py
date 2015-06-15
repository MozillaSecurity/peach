# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


class Transformer(object):
    """
    Transformers encode or decode some form of input e.g. Base64 string.
    Chained transformer run after this transformer.
    """

    def __init__(self, anotherTransformer=None):
        """Create a Transformer object.

        :param anotherTransformer: a transformer to run next
        :type anotherTransformer: Transformer
        """
        self._anotherTransformer = anotherTransformer

    def changesSize(self):
        return True

    def encode(self, data):
        """Transform data and call next transformer in chain if provided.

        :param data: data to transform
        :type data: str
        :returns: transformed data
        :rtype: str
        """
        ret = self.realEncode(data)
        if self._anotherTransformer is not None:
            return self._anotherTransformer.encode(ret)
        return ret

    def decode(self, data):
        """Perform reverse transformation if possible.

        :param data: data to transform
        :type data: str
        :returns: transformed data
        :rtype: str
        """
        if self._anotherTransformer is not None:
            data = self._anotherTransformer.decode(data)
        return self.realDecode(data)

    def getTransformer(self):
        """Gets the next transformer in the chain.

        :returns: next transformer in chain or None
        :rtype: Transformer
        """
        return self._anotherTransformer

    def addTransformer(self, transformer):
        """Set the next transformer in the chain.

        :param transformer: transformer to set
        :type transformer: Transformer
        :returns: this transformer
        :rtype: Transformer
        """
        self._anotherTransformer = transformer
        return self

    def realEncode(self, data):
        """Override this method to implement your transform.

        :param data: data to transform
        :type data: str
        :returns: transformed data
        :rtype: str
        """
        raise Exception("realEncode(): Transformer does not work both ways.")

    def realDecode(self, data):
        """Override this method to implement your transform.

        :param data: data to transform
        :type data: str
        :returns: transformed data
        :rtype: str
        """
        raise Exception("realDecode(): Transformer does not work both ways.")
