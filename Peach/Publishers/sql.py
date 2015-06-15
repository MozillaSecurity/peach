# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from types import *

import sys

try:
    import dbi, odbc
except ImportError:
    pass

from Peach.publisher import Publisher

#__all__ = ["Odbc"]


class Odbc(Publisher):
    """
    Publisher for ODBC connections.  Generated data sent as a SQL query via
    execute.  Calling receave will return a string of all row data concatenated
    together with \t as field separator.

    Currently this Publisher makes use of the odbc package which is some what
    broken in that you must create an actual ODBC DSN via the ODBC manager.
    Check out mxODBC which is not open source for another alterative.

    Note:  Each call to start/stop will create and close the SQL connection and
    cursor.
    """

    def __init__(self, dsn):
        """
        @type	dsn: string
        @param	dsn: DSN must be in format of "dsn/user/password" where DSN is a DSN name.
        """
        Publisher.__init__(self)
        self._dsn = dsn
        self._sql = None
        self._cursor = None
        self._sql = None

    def start(self):
        """
        Create connection to server.
        """
        self._sql = odbc.odbc(self._dsn)

    def stop(self):
        """
        Close any open cursors, and close connection to server.
        """
        self._cursor.close()
        self._cursor = None
        self._sql.close()
        self._sql = None

    def call(self, method, args):
        """
        Create cursor and execute data.
        """
        self._cursor = self._sql.cursor()

        try:
            self._cursor.execute(method, args)
        except:
            print("Warning: execute failed: %s" % sys.exc_info())
            pass

        ret = ''
        try:
            row = self._cursor.fetchone()
            for i in range(len(row)):
                retType = type(row[i])
                if retType is IntType:
                    ret += "\t%d" % row[i]
                elif retType is FloatType:
                    ret += "\t%f" % row[i]
                elif retType is LongType:
                    ret += "\t%d" % row[i]
                elif retType is StringType:
                    ret += "\t%s" % row[i]

        except:
            pass

        return ret
