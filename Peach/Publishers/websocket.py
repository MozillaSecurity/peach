# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
import os
import sys
import time
import json
import urllib
import base64
import socket
import string
import struct
import hashlib
import logging
import urlparse
import email.message
import email.parser

from Peach.publisher import Publisher
from Peach.Engine.common import PeachException
from Peach.Utilities.network import getUnboundPort

logger = logging.getLogger("WebSocket")

_str_t = str if sys.version_info[0] == 3 else lambda a, b: str(a).encode(b)


class WebSocketFilePublisher(Publisher):
    _opcodes = {
        0: 'continue',
        1: 'text',
        2: 'binary',
        8: 'close',
        9: 'ping',
        10: 'pong'
    }

    # TODO: Make it possible to support **kwargs for Publishers
    def __init__(self, host, port, template, publish, storage=None):
        Publisher.__init__(self)

        self._host = host
        self._template = template
        self._publish = publish
        self._storagePath = storage
        self._server = None
        self._initialStart = True
        self._possiblePeerCrash = False
        self._client = None
        self._clientAddr = None
        self._contentTemplate = None

        try:
            socket.gethostbyaddr(self._host)
        except socket.error as msg:
            raise PeachException("Websocket publisher host not reachable: %s" % msg)

        try:
            self._port = int(port)
        except ValueError:
            raise PeachException("WebSocket publisher port is not a valid number: %s" % port)

        if self._publish != "base64" and not self._storagePath:
            raise PeachException(
                "Publisher's storage parameter needs to be set if not using Base64.")

    def initialize(self):
        if not self._port:
            self._port = getUnboundPort()

        logger.debug("Loading template {}".format(self._template))
        try:
            with open(self._template, "rb") as fd:
                self._contentTemplate = string.Template(fd.read())
        except IOError as msg:
            raise PeachException("Loading template failed, reason: %s" % msg)

        logger.debug("Initialize WebSocket publisher.")

    def start(self):
        if not self._server:
            logger.debug("Binding socket. ({}:{})".format(self._host, self._port))
            for _ in range(6):
                try:
                    self._server = socket.socket()
                    self._server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    self._server.bind((self._host, self._port))
                    self._server.listen(2)
                    exception = None
                    break
                except socket.error as msg:
                    self._server = None
                    exception = msg
                time.sleep(5)
            if self._server is None:
                raise PeachException("TCP bind attempt failed: %s" % exception)
            logger.debug("Socket created.")
        if self._possiblePeerCrash or self._initialStart:
            logger.debug("Waiting for incoming connection ...")
            self._client, self._clientAddr = self._server.accept()
            logger.debug("Connected by {}:{}".format(self._clientAddr[0], self._clientAddr[1]))
            #logger.debug("Status: {}".format(self._client.recv(256)))
            self._initialStart = False
            self._possiblePeerCrash = False

            self._client.settimeout(0.01)
            while True:
                try:
                    _, headers = _str_t(self._client.recv(1024), 'ascii').split('\r\n', 1)
                    break
                except socket.timeout:
                    continue
            headers = email.parser.HeaderParser().parsestr(headers)
            #logger.debug(headers)
            # TODO(jschwartzentruber): validate request/headers
            hresponse = hashlib.sha1(headers['sec-websocket-key'].encode('ascii'))
            hresponse.update(b'258EAFA5-E914-47DA-95CA-C5AB0DC85B11')
            resp = email.message.Message()
            resp.add_header('Upgrade', 'websocket')
            resp.add_header('Connection', 'Upgrade')
            resp.add_header('Sec-WebSocket-Accept', _str_t(base64.b64encode(hresponse.digest()), 'ascii'))
            resp = resp.as_string(unixfrom=False).replace('\n', '\r\n')
            self._client.sendall('HTTP/1.1 101 Switching Protocols\r\n{}'.format(resp).encode('ascii'))


    def _storeTestcase(self, rawTestcase):
        try:
            os.makedirs(os.path.dirname(self._storagePath))
        except OSError as e:
            if str(e).find("File exist") == -1:
                raise PeachException("Unable to create temporary storage folder: %s" % e)
        logger.debug("Saving raw test case to {}".format(self._storagePath))
        try:
            with open(self._storagePath, 'wb') as fd:
                fd.write(rawTestcase)
        except IOError as msg:
            raise PeachException("Storing test case failed: {}".format(msg))

    def _prepareBrowserTemplate(self, data):
        if self._publish == "base64":
            data = self._contentTemplate.substitute(FILE=base64.b64encode(data))
        else:
            data = self._contentTemplate.substitute(FILE=urlparse.urljoin(self._publish, self._storagePath))
        data = urllib.quote(data)
        return data

    def _send(self, opcode, data):
        length = len(data)
        out = bytearray()
        out.append(0x80 | opcode)
        if length <= 125:
            out.append(length)
        elif length <= 65535:
            out.append(126)
            out.extend(struct.pack('!H', length))
        else:
            out.append(127)
            out.extend(struct.pack('!Q', length))
        if length:
            out.extend(data)
        self._client.sendall(out)

    def send(self, data):
        if self._storagePath:
            self._storeTestcase(data)

        templateData = self._prepareBrowserTemplate(data)

        logger.debug("Sending packet to %s:%d" % (self._clientAddr[0], self._clientAddr[1]))
        try:
            self._send(1, ('{"type":"template", "content": "%s"}\n' % templateData).encode('utf8'))
            self._send(1, '{"type":"msg", "content": "evaluate"}\n'.encode('utf8'))
        except socket.error as msg:
            logger.debug("Send failed! Reason: %s" % msg)
            self._setPossiblePeerCrash()
            return
        logger.debug("Sent successfully! ({} bytes)".format(len(templateData)))

        self.receive()

    def receive(self):
        buf = []
        buf_op = None
        response = ""
        try:
            while True:
                try:
                    data = struct.unpack('BB', self._client.recv(2))
                except socket.timeout:
                    # no data
                    continue
                except struct.error:
                    break  # chrome doesn't send a close-frame
                fin, mask = bool(data[0] & 0x80), bool(data[1] & 0x80)
                opcode = self._opcodes[data[0] & 0xF]
                if opcode == 'close':
                    break
                elif opcode == 'pong':
                    continue
                length = data[1] & 0x7F
                if length == 126:
                    length = struct.unpack('!H', self._client.recv(2))[0]
                elif length == 127:
                    length = struct.unpack('!Q', self._client.recv(8))[0]
                mask = bytearray(self._client.recv(4)) if mask else None
                data = bytearray(self._client.recv(length))
                if mask is not None:
                    data = bytearray((b ^ mask[i % 4]) for (i, b) in enumerate(data))
                if opcode == 'continue':
                    if not buf:
                        raise PeachException('Received unexpected Websocket "continue" frame.')
                    opcode = buf_op
                elif opcode == 'ping':
                    self._send(10, data)
                    continue
                elif buf:
                    logger.debug('WARNING: Received a new frame while waiting for another to finish, '
                               'discarding {} bytes of {}'.format(len("".join(buf)), buf_op))
                    buf = []
                    buf_op = None
                if opcode == 'text':
                    data = _str_t(data, 'utf8')
                elif opcode != 'binary':
                    logger.debug('WARNING: Unknown websocket opcode {}'.format(opcode))
                    continue
                if not buf:
                    buf_op = opcode
                buf.append(data)
                if fin:
                    response = "".join(buf)
                    break
        except socket.error as msg:
            logger.debug("Receive failed! Reason: %s" % msg)
            self._setPossiblePeerCrash()
            return ""

        if not len(response):
            logger.debug("WARNING: Host is probably alive but response is empty. "
                       "Treating empty response as crash.")
            self._setPossiblePeerCrash()
            return response

        try:
            parsedResponse = json.loads(response)
        except ValueError as msg:
            logger.debug("WARNING: JSON object is corrupted: {!r}".format(response))
            return response

        if parsedResponse.get("msg", None) == "Evaluation complete":
            logger.debug("Response: {}".format(parsedResponse.get("msg")))
        else:
            logger.debug("WARNING: Unexpected response: {!r}".format(response))

        return response

    def _setPossiblePeerCrash(self):
        logger.debug("Let's try to accept() while the Agent is going to spawn the process again.")
        self._possiblePeerCrash = True

    def connect(self):
        pass

    def close(self):
        pass

    def stop(self):
        pass

    def finalize(self):
        logger.debug("Destroying WebSocket Publisher.")
        if self._client:
            self._client.close()
        if self._server:
            self._server.close()
        logger.debug("Destroyed.")

