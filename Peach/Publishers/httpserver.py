# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
import urllib
import urlparse
import base64
import threading

from Peach.Publishers.websocket import WebSocketFilePublisher
from Peach.Utilities.network import getUnboundPort


class HeaderReflectHandler(BaseHTTPRequestHandler):
    """
    A handler that reflects data in requests params to response headers
    """
    def _write_header(self, header, value):
        self.send_header(header, value)

    def do_GET(self):
        """
        Handle a GET request. Takes 2 request params; 'header' (the response
        header to write) and 'data' (base64 encoded data to be written to that
        header)
        """
        qs = {}
        path = self.path
        self.send_response(200)
        if '?' in path:
            path, tmp = path.split('?', 1)
            qs = urlparse.parse_qs(tmp)
        if qs['data'] and qs['header']:
            self._write_header(qs['header'][0], base64.b64decode(qs['data'][0]))
        self.end_headers()
        self.wfile.write('<html>Wow! Such fuzz!</html>')
        return


class HttpHeaderPublisher(WebSocketFilePublisher):
    """
    A publisher for serving headers from an HTTP server.
    """
    def initialize(self):
        WebSocketFilePublisher.initialize(self)
        # find a port we can bind for our webserver
        self.webserver_port = getUnboundPort()
        self.debug("attempting to bind %i for webserver" % self.webserver_port)
        server = HTTPServer(('0.0.0.0', self.webserver_port), HeaderReflectHandler)
        self._running = True

        # TODO: start the webserver
        def run_server():
            while self._running:
                server.handle_request()

        t = threading.Thread(target=run_server)
        t.daemon = True
        t.start()

    def _prepareBrowserTemplate(self, data):
        if self._publish == "base64":
            data = self._contentTemplate.substitute(FILE=base64.b64encode(data), PORT=self.webserver_port)
        else:
            data = self._contentTemplate.substitute(FILE=urlparse.urljoin(self._publish, self._storagePath), PORT=self.webserver_port)
        data = urllib.quote(data)
        return data

    def finalize(self):
        WebSocketFilePublisher.finalize(self)
        self._running = False
