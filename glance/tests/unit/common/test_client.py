# Copyright 2013 Red Hat, Inc.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import datetime
import http.client
from pathlib import Path
import ssl
from unittest import mock

from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives import serialization
from cryptography import x509
from cryptography.x509.oid import NameOID
import fixtures
from oslo_log.fixture import logging_error as log_fixture
import testtools

from glance.common import auth
from glance.common import client
from glance.tests.unit import fixtures as glance_fixtures
from glance.tests import utils


_DEFAULT_CA_ERROR = 'Default CA trust was loaded'


class TestClient(testtools.TestCase):

    def setUp(self):
        super(TestClient, self).setUp()
        self.endpoint = 'example.com'
        self.client = client.BaseClient(self.endpoint, port=9191,
                                        auth_token='abc123')

        # Limit the amount of DeprecationWarning messages in the unit test logs
        self.useFixture(glance_fixtures.WarningsFixture())

        # Make sure logging output is limited but still test debug formatting
        self.useFixture(log_fixture.get_logging_handle_error_fixture())
        self.useFixture(glance_fixtures.StandardLogging())

    def test_make_auth_plugin(self):
        creds = {'strategy': 'keystone'}
        insecure = False

        with mock.patch.object(auth, 'get_plugin_from_strategy'):
            self.client.make_auth_plugin(creds, insecure)

    @mock.patch.object(http.client.HTTPConnection, "getresponse")
    @mock.patch.object(http.client.HTTPConnection, "request")
    def test_http_encoding_headers(self, _mock_req, _mock_resp):
        # Lets fake the response
        # returned by http.client
        fake = utils.FakeHTTPResponse(data=b"Ok")
        _mock_resp.return_value = fake

        headers = {"test": 'ni\xf1o'}
        resp = self.client.do_request('GET', '/v1/images/detail',
                                      headers=headers)
        self.assertEqual(fake, resp)

    @mock.patch.object(http.client.HTTPConnection, "getresponse")
    @mock.patch.object(http.client.HTTPConnection, "request")
    def test_http_encoding_params(self, _mock_req, _mock_resp):
        # Lets fake the response
        # returned by http.client
        fake = utils.FakeHTTPResponse(data=b"Ok")
        _mock_resp.return_value = fake

        params = {"test": 'ni\xf1o'}
        resp = self.client.do_request('GET', '/v1/images/detail',
                                      params=params)
        self.assertEqual(fake, resp)

    def _make_tls_files(self):
        # Generate current test material without weakening TLS defaults.
        cert_dir = Path(self.useFixture(fixtures.TempDir()).path)
        cert_file = cert_dir / 'cert.pem'
        key_file = cert_dir / 'key.pem'
        key = ec.generate_private_key(ec.SECP256R1())
        name = x509.Name([
            x509.NameAttribute(NameOID.COMMON_NAME, self.endpoint)])
        now = datetime.datetime.now(datetime.timezone.utc)
        validity = datetime.timedelta(days=1)
        cert = (x509.CertificateBuilder()
                .subject_name(name)
                .issuer_name(name)
                .public_key(key.public_key())
                .serial_number(x509.random_serial_number())
                .not_valid_before(now - validity)
                .not_valid_after(now + validity)
                .add_extension(
                    x509.BasicConstraints(ca=True, path_length=None),
                    critical=True)
                .sign(key, hashes.SHA256()))
        cert_file.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
        key_file.write_bytes(key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption()))
        return cert_file, key_file

    def _connect_tls(self, connection):
        raw_socket = mock.Mock()
        with mock.patch.object(client.socket, 'create_connection',
                               return_value=raw_socket), \
                mock.patch.object(ssl.SSLContext, 'wrap_socket',
                                  autospec=True) as wrap_socket:
            connection.connect()

        context = wrap_socket.call_args.args[0]
        wrap_socket.assert_called_once_with(
            context, raw_socket, server_hostname=self.endpoint)
        self.assertIs(wrap_socket.return_value, connection.sock)
        return context

    def test_connect_cert_chain(self):
        cert_file, key_file = self._make_tls_files()
        connection = client.HTTPSClientAuthConnection(
            self.endpoint, http.client.HTTPS_PORT, key_file=key_file,
            cert_file=cert_file, ca_file=cert_file)

        context = self._connect_tls(connection)

        self.assertTrue(context.check_hostname)
        self.assertEqual(ssl.CERT_REQUIRED, context.verify_mode)

    def test_connect_custom_ca(self):
        cert_file, _ = self._make_tls_files()
        with mock.patch.object(
                ssl.SSLContext, 'load_default_certs',
                side_effect=AssertionError(_DEFAULT_CA_ERROR)):
            connection = client.HTTPSClientAuthConnection(
                self.endpoint, http.client.HTTPS_PORT, key_file=None,
                cert_file=None, ca_file=cert_file)
            context = self._connect_tls(connection)

        expected_ca = ssl.PEM_cert_to_DER_cert(cert_file.read_text())
        self.assertEqual([expected_ca],
                         context.get_ca_certs(binary_form=True))
        self.assertTrue(context.check_hostname)
        self.assertEqual(ssl.CERT_REQUIRED, context.verify_mode)

    def test_connect_no_ca(self):
        with mock.patch.object(
                ssl.SSLContext, 'load_default_certs',
                side_effect=AssertionError(_DEFAULT_CA_ERROR)):
            connection = client.HTTPSClientAuthConnection(
                self.endpoint, http.client.HTTPS_PORT, key_file=None,
                cert_file=None, ca_file=None)
            context = self._connect_tls(connection)

        self.assertEqual([], context.get_ca_certs())
        self.assertTrue(context.check_hostname)
        self.assertEqual(ssl.CERT_REQUIRED, context.verify_mode)

    def test_connect_reloads_ca(self):
        cert_file, _ = self._make_tls_files()
        replacement, _ = self._make_tls_files()
        connection = client.HTTPSClientAuthConnection(
            self.endpoint, http.client.HTTPS_PORT, key_file=None,
            cert_file=None, ca_file=cert_file)
        previous_context = self._connect_tls(connection)

        # Removed CAs must not remain trusted after reconnecting.
        cert_file.write_bytes(replacement.read_bytes())
        context = self._connect_tls(connection)

        expected_ca = ssl.PEM_cert_to_DER_cert(cert_file.read_text())
        self.assertEqual([expected_ca],
                         context.get_ca_certs(binary_form=True))
        self.assertIsNot(previous_context, context)

    def test_connect_insecure(self):
        ca_dir = Path(self.useFixture(fixtures.TempDir()).path)
        ca_file = ca_dir / 'missing.pem'
        with mock.patch.object(
                ssl.SSLContext, 'load_default_certs',
                side_effect=AssertionError(_DEFAULT_CA_ERROR)):
            connection = client.HTTPSClientAuthConnection(
                self.endpoint, http.client.HTTPS_PORT, key_file=None,
                cert_file=None, ca_file=ca_file, insecure=True)
            context = self._connect_tls(connection)

        self.assertEqual([], context.get_ca_certs())
        self.assertFalse(context.check_hostname)
        self.assertEqual(ssl.CERT_NONE, context.verify_mode)
