# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
import os
import time

from marionette.errors import TimeoutException
import mozdevice

class LockScreen(object):

    def __init__(self, marionette):
        self.marionette = marionette
        js = os.path.abspath(os.path.join(__file__, os.path.pardir, 'atoms', "gaia_lock_screen.js"))
        self.marionette.import_script(js)

    @property
    def is_locked(self):
        self.marionette.switch_to_frame()
        return self.marionette.execute_script('window.wrappedJSObject.LockScreen.locked')

    def unlock(self):
        self.marionette.switch_to_frame()
        result = self.marionette.execute_async_script('GaiaLockScreen.unlock();')
        assert result, 'Unable to unlock screen'


class GaiaApp(object):

    def __init__(self, origin=None, name=None, frame=None, src=None):
        self.frame = frame
        self.frame_id = frame
        self.src = src
        self.name = name
        self.origin = origin


class GaiaApps(object):
    def __init__(self, marionette):
        self.marionette = marionette
        js = os.path.abspath(os.path.join(__file__, os.path.pardir, 'atoms', "gaia_apps.js"))
        self.marionette.import_script(js)

    def get_permission(self, app_name, permission_name):
        return self.marionette.execute_async_script(
            "return GaiaApps.getPermission('%s', '%s')" % (app_name, permission_name))

    def set_permission(self, app_name, permission_name, value):
        return self.marionette.execute_async_script("return GaiaApps.setPermission('%s', '%s', '%s')" %
                                                    (app_name, permission_name, value))

    def launch(self, name, switch_to_frame=True, url=None):
        self.marionette.switch_to_frame()
        result = self.marionette.execute_async_script("GaiaApps.launchWithName('%s');" % name)
        assert result, "Failed to launch app with name '%s'" % name
        app = GaiaApp(frame=result.get('frame'),
                      src=result.get('src'),
                      name=result.get('name'),
                      origin=result.get('origin'))
        if app.frame_id is None:
            raise Exception("App failed to launch; there is no app frame")
        if switch_to_frame:
            self.switch_to_frame(app.frame_id, url)
        return app

    def uninstall(self, name):
        self.marionette.switch_to_frame()
        self.marionette.execute_async_script("GaiaApps.uninstallWithName('%s');" % name)

    def kill(self, app):
        self.marionette.switch_to_frame()
        js = os.path.abspath(os.path.join(__file__, os.path.pardir, 'atoms', "gaia_apps.js"))
        self.marionette.import_script(js)
        result = self.marionette.execute_async_script("GaiaApps.kill('%s');" % app.origin)
        assert result, "Failed to kill app with name '%s'" % app.name

    def kill_all(self):
        self.marionette.switch_to_frame()
        js = os.path.abspath(os.path.join(__file__, os.path.pardir, 'atoms', "gaia_apps.js"))
        self.marionette.import_script(js)
        self.marionette.execute_async_script("GaiaApps.killAll()")

    def runningApps(self):
        return self.marionette.execute_script("return GaiaApps.getRunningApps();")

    def switch_to_frame(self, app_frame, url=None, timeout=30):
        self.marionette.switch_to_frame(app_frame)
        start = time.time()
        if not url:
            def check(now):
                return "about:blank" not in now
        else:
            def check(now):
                return url in now
        while time.time() - start < timeout:
            if check(self.marionette.get_url()):
                return
            time.sleep(2)
        raise TimeoutException('Could not switch to app frame %s in time' % app_frame)


class GaiaDevice(object):
    def __init__(self, marionette):
        self.marionette = marionette

    @property
    def manager(self):
        if hasattr(self, '_manager') and self._manager:
            return self._manager

        if not self.is_android_build:
            raise Exception('Device manager is only available for devices.')

        dm_type = os.environ.get('DM_TRANS', 'adb')
        if dm_type == 'adb':
            self._manager = mozdevice.DeviceManagerADB()
        elif dm_type == 'sut':
            host = os.environ.get('TEST_DEVICE')
            if not host:
                raise Exception('Must specify host with SUT!')
            self._manager = mozdevice.DeviceManagerSUT(host=host)
        else:
            raise Exception('Unknown device manager type: %s' % dm_type)
        return self._manager

    @property
    def is_android_build(self):
        return 'Android' in self.marionette.session_capabilities['platform']

    def push_file(self, source, count=1, destination='', progress=None):
        if not destination.count('.') > 0:
            destination = '/'.join([destination, source.rpartition(os.path.sep)[-1]])
        self.manager.mkDirs(destination)
        self.manager.pushFile(source, destination)

        if count > 1:
            for i in range(1, count + 1):
                remote_copy = '_%s.'.join(iter(destination.split('.'))) % i
                self.manager._checkCmd(['shell', 'dd', 'if=%s' % destination, 'of=%s' % remote_copy])
                if progress:
                    progress.update(i)
            self.manager.removeFile(destination)

    def restart_b2g(self):
        self.stop_b2g()
        time.sleep(2)
        self.start_b2g()

    def start_b2g(self):
        self.manager.shellCheckOutput(['start', 'b2g'])
        self.marionette.wait_for_port()
        self.marionette.start_session()
        self.marionette.execute_async_script("""
            window.addEventListener('mozbrowserloadend', function mozbrowserloadend(aEvent) {
            window.removeEventListener('mozbrowserloadend', mozbrowserloadend);
            marionetteScriptFinished();
            });""")

    def stop_b2g(self):
        self.manager.shellCheckOutput(['stop', 'b2g'])
        self.marionette.client.close()
        self.marionette.session = None
        self.marionette.window = None