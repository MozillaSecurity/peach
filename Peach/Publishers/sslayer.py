# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
import sys
import ssl
import socket
import tlslite.api

from Peach.Publishers.tcp import TcpListener
from Peach.publisher import PublisherSoftException
from Peach.Engine.common import PeachException


class SSL(TcpListener):
    def __init__(self, host, port, cert, pkey, timeout=0.25):
        TcpListener.__init__(self, host, port, timeout)

        self.cert = cert
        self.pkey = pkey

    def accept(self):
        print("[*] Waiting for incoming connection")
        client, addr = self._listen.accept()
        print("[*] Client:", addr[0], addr[1])

        print("[*] Wrapping socket to TLS/SSL")
        try:
            self._socket = ssl.wrap_socket(client,
                                           server_side=True,
                                           certfile=self.cert,
                                           keyfile=self.pkey,
                                           do_handshake_on_connect=False)
        except ssl.SSLError as e:
            raise PeachException(str(e))

        print("[*] Performing TLS/SSL handshake")
        try:
            self._socket.do_handshake()
        except ssl.SSLError as e:
            raise PeachException(str(e))

    def close(self):
        try:
            if self._socket is not None:
                self._socket.shutdown(socket.SHUT_RDWR)
                self._socket.close()
        except:
            pass
        finally:
            self._socket = None


class TLSLiteServer(TcpListener):
    def __init__(self, host, port, version, cert, pkey, timeout=0.25):
        TcpListener.__init__(self, host, port, timeout)

        self.cert = cert
        self.pkey = pkey
        self.version = version

        try:
            with open(self.cert) as fd:
                cert_content = fd.read()
        except IOError:
            raise PeachException("Unable to open %s" % self.cert)

        x509 = tlslite.api.X509()
        x509.parse(cert_content)
        self.certChain = tlslite.api.X509CertChain([x509])

        try:
            with open(self.pkey) as fd:
                pkey_content = fd.read()
        except IOError:
            raise PeachException("Unable to open %s" % self.pkey)

        self.privateKey = tlslite.api.parsePEMKey(pkey_content, private=True)

    def accept(self):
        print("[*] Waiting for incoming connection")
        sys.stdout.flush()
        client, addr = self._listen.accept()

        print("[*] Connected by %s:%s" % (addr[0], str(addr[1])))
        print("[*] Wrapping socket to TLS/SSL")
        try:
            self._socket = tlslite.api.TLSConnection(client)
        except:
            client.close()
            value = sys.exc_info()[1]
            msg = "[!] Wrapping socket failed, reason: %s" % value
            raise PublisherSoftException(msg)

        print("[*] Performing TLS/SSL handshake)")
        try:
            self._socket.handshakeServer(certChain=self.certChain,
                                         privateKey=self.privateKey,
                                         #reqCert=True,
                                         nextProtos=[self.version])
        except:
            self.close()
            value = sys.exc_info()[1]
            msg = "[!] Performing TLS/SSL handshake failed, reason: %s" % value
            raise PublisherSoftException(msg)
        print("done!")


class SPDYPublisher(TLSLiteServer):
    def __init__(self, host, port, cert, pkey, timeout=0.25):
        TLSLiteServer.__init__(self, host, port, cert, pkey, timeout)
