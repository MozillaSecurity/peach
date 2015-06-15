# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
import os
import shutil

from Peach.agent import Monitor


class CleanupFolder(Monitor):
    """
    This monitor will remove any files created in a folder during a fuzzing
    iteration. Create for removing stale temp files, etc.
    """

    def __init__(self, args):
        """
        Constructor. Arguments are supplied via the Peach XML file.

        @type	args: Dictionary
        @param	args: Dictionary of parameters
        """
        self._name = None
        self._folder = args['Folder'].replace("'''", "")
        self._folderListing = os.listdir(self._folder)

    def OnTestStarting(self):
        """
        Called right after a test case or variation.
        """
        listing = os.listdir(self._folder)
        for item in listing:
            if item not in self._folderListing:
                realName = os.path.join(self._folder, item)
                print("CleanupFolder: Removing '{}'".format(realName))
                try:
                    os.unlink(realName)
                except:
                    pass
                try:
                    shutil.rmtree(realName)
                except:
                    pass


try:
    import win32api, win32con
except:
    pass


class CleanupRegistry(Monitor):
    """
    This monitor will remove any sub-keys for a specified registry key before
    each run. This is useful for removing document recovery keys for fuzzing
    Office.
    """

    def __init__(self, args):
        """
        Constructor. Arguments are supplied via the Peach XML file.

        @type	args: Dictionary
        @param	args: Dictionary of parameters
        """
        self._name = None
        self._key = args['Key'].replace("'''", "")

        if self._key.startswith("HKCU\\"):
            self._root = win32con.HKEY_CURRENT_USER
        elif self._key.startswith("HKCC\\"):
            self._root = win32con.HKEY_CURRENT_CONFIG
        elif self._key.startswith("HKLM\\"):
            self._root = win32con.HKEY_LOCAL_MACHINE
        elif self._key.startswith("HKPD\\"):
            self._root = win32con.HKEY_PERFORMANCE_DATA
        elif self._key.startswith("HKU\\"):
            self._root = win32con.HKEY_USERS
        else:
            print("CleanupRegistry: Error, key must be prefixed with: "
                  "HKCU, HKCC, HKLM, HKPD, or HKU.")
            raise Exception("CleanupRegistry: Error, key must be prefixed "
                            "with: HKCU, HKCC, HKLM, HKPD, or HKU.")
        self._key = self._key[self._key.find("\\") + 1:]

    def OnTestStarting(self):
        self.deleteKey(self._root, self._key)

    def deleteKey(self, hKey, subKey):
        """
        Recursively remove registry keys.
        """
        try:
            hKey = win32api.RegOpenKeyEx(hKey, subKey, 0,
                                         win32con.KEY_ALL_ACCESS)
            try:
                while True:
                    s = win32api.RegEnumKey(hKey, 0)
                    self.deleteKey(hKey, s)
                    print("CleanupRegistry: Removing sub-key '{}'".format(s))
                    win32api.RegDeleteKey(hKey, s)
            except win32api.error:
                pass
            finally:
                win32api.RegCloseKey(hKey)
        except:
            print("Warning: Unable to open registry key!")
            pass
