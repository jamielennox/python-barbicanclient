# Copyright (c) 2013 Rackspace, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json

from mock import MagicMock
import unittest2 as unittest

from barbicanclient import client
from barbicanclient.common.exceptions import ClientException


class WhenTestingClient(unittest.TestCase):
    def setUp(self):
        self.auth_endpoint = 'https://keystone.com/v2'
        self.user = 'user'
        self.password = 'password'
        self.tenant = 'tenant'
        
        self.key = 'key'
        self.endpoint = 'http://localhost:9311/v1/'
        self.auth_token = 'token'
        self.href = 'http://localhost:9311/v1/12345/orders'

        self.fake_env = MagicMock()
        self.fake_env.return_value = None
        self.authenticate = MagicMock()
        self.authenticate.return_value = (self.endpoint, self.auth_token)
        self.request = MagicMock()
        self.request.return_value.content = json.dumps(
            {
                "secret_ref": "http://localhost:9311/None/secrets"
                              "/8502cea9-9d35-46d7-96f5-80e43905e4c5"
            }
        )
        self.request.return_value.headers = {
            'content-length': '92',
            'content-type': 'application/json; charset=utf-8',
            'location': 'http://localhost:9311/None/'
                        'secrets/8502cea9-9d35-46d7-96f5-80e43905e4c5',
            'x-openstack-request-id':
            'req-6c19d09e-1167-445c-b435-d6b0818b59b9'
        }
        self.request.return_value.ok = True
        self.client = client.Client(auth_endpoint=self.auth_endpoint, 
                                    user=self.user,
                                    key=self.key, tenant=self.tenant,
                                    token=self.auth_token,
                                    authenticate=self.authenticate,
                                    request=self.request,
                                    endpoint=self.endpoint,
                                    auth=False)

    def test_authenticated_client_requires_endpoint_user_pw_tenant(self):
        with self.assertRaises(ValueError):
            c = client.Client(auth=True)
        with self.assertRaises(ValueError):
            c = client.Client()  # default auth=True
        c=client.Client(auth_endpoint=self.auth_endpoint, user=self.user,
                        password=self.password, tenant=self.tenant,
                        #TODO(dmend): remove authenticate below
                        authenticate=self.authenticate)

    def test_should_connect_with_token(self):
        self.assertFalse(self.authenticate.called)

    def test_should_connect_without_token(self):
        self.client = client.Client(auth=False,
                                    auth_endpoint=self.auth_endpoint,
                                    user=self.user,
                                    key=self.key,
                                    tenant=self.tenant,
                                    authenticate=self.authenticate,
                                    endpoint=self.endpoint)
        self.authenticate\
            .assert_called_once_with(self.auth_endpoint,
                                     self.user,
                                     self.key,
                                     self.tenant,
                                     service_type='key-store',
                                     endpoint=self.endpoint,
                                     cacert=None
                                     )
        self.assertEqual(self.auth_token, self.client.auth_token)
        self.assertEqual(self.auth_endpoint, self.client._auth_endpoint)
        self.assertEqual(self.user, self.client._user)
        self.assertEqual(self.key, self.client._key)
        self.assertEqual(self.tenant, self.client._tenant)
        self.assertEqual(self.endpoint, self.client._endpoint)

    def test_should_raise_for_bad_args(self):
        with self.assertRaises(ClientException):
            self.client = client.Client(auth=False, 
                                        auth_endpoint=None, 
                                        user=self.user,
                                        key=self.key,
                                        tenant=self.tenant,
                                        fake_env=self.fake_env,
                                        token=self.auth_token,
                                        authenticate=self.authenticate,
                                        request=self.request,
                                        endpoint=self.endpoint)

    def test_should_create_secret(self):
        body = {'status': "ACTIVE",
                'updated': '2013-06-07T16:13:38.889857',
                'cypher_type': 'cbc',
                'name': 'test_secret',
                'algorithm': 'aes',
                'created': '2013-06-07T16:13:38.889851',
                'secret_ref': 'http://localhost:9311/v1/None/secrets/e6e7d'
                              'b5e-3738-408e-aaba-05a7177cade5',
                'expiration': '2015-06-07T16:13:38.889851',
                'bit_length': 256,
                'payload_content_type': 'text/plain'
                }

        secret = client.Secret(self.client, body)
        self.request.return_value.content = json.dumps(body)
        created = self.client.create_secret(name='test_secret',
                                            payload='Test secret',
                                            algorithm='aes',
                                            bit_length=256,
                                            cypher_type='cbc',
                                            expiration='2015-06-07T16:13'
                                                       ':38.889851',
                                            payload_content_type=
                                            'text/plain')
        self.assertTrue(self._are_equivalent(secret, created))

    def test_should_create_order(self):
        body = {"status": "ACTIVE",
                "secret_ref": "http://localhost:9311/v1/12345/secrets/5706054"
                              "9-2fcf-46eb-92bb-bf49fcf5d089",
                "updated": "2013-06-07T19:00:37.338386",
                "created": "2013-06-07T19:00:37.298704",
                "secret": {
                    'cypher_type': 'cbc',
                    'name': 'test_secret',
                    'algorithm': 'aes',
                    'created': '2013-06-07T16:13:38.889851',
                    'expiration': '2015-06-07T16:13:38.889851',
                    'bit_length': 256,
                    'payload_content_type': 'application/octet-stream'
                },
                "order_ref": "http://localhost:9311/v1/12345/orders/003f2b91-"
                             "2f53-4c0a-a0f3-33796671efc3"
                }

        order = client.Order(self.client, body)
        self.request.return_value.content = json.dumps(body)
        created = self.client.create_order(
            name='test_secret',
            payload_content_type='application/octet-stream',
            algorithm='aes',
            bit_length=256,
            cypher_type='cbc'
        )
        self.assertTrue(self._are_equivalent(order, created))

    def test_list_no_secrets(self):
        body0 = {'secrets': []}
        secrets = []
        self.request.return_value.content = json.dumps(body0)
        secret_list, prev_ref, next_ref = self.client.list_secrets(0, 0)
        self.assertTrue(self._are_equivalent(secrets, secret_list))
        self.assertIsNone(prev_ref)
        self.assertIsNone(next_ref)

    def test_list_single_secret(self):
        limit = 1
        body1 = {'secrets': [{'status': 'ACTIVE',
                             'content_types': {'default': 'text/plain'},
                             'updated': '2013-06-03T21:16:58.349230',
                             'cypher_type': None,
                             'name': 'test_1',
                             'algorithm': None,
                             'created': '2013-06-03T21:16:58.349222',
                             'secret_ref': 'http://localhost:9311/v1/'
                                           'None/secrets/bbd2036f-730'
                                           '7-4090-bbef-bbb6025e5e7b',
                             'expiration': None,
                             'bit_length': None,
                             'mime_type': 'text/plain'}],
                 'next': "{0}/{1}?limit={2}&offset={2}".format(self.client.
                                                               _tenant,
                                                               self.client.
                                                               SECRETS_PATH,
                                                               limit)}
        secrets = [client.Secret(self.client, body1['secrets'][0])]
        self.request.return_value.content = json.dumps(body1)
        secret_list, prev_ref, next_ref = self.client.list_secrets(limit, 0)
        self.assertTrue(self._are_equivalent(secrets, secret_list))
        self.assertIsNone(prev_ref)
        self.assertEqual(body1['next'], next_ref)

    def test_list_multiple_secrets(self):
        limit = 2
        body1 = {'secrets': [{'status': 'ACTIVE',
                 'content_types': {'default': 'text/plain'},
                 'updated': '2013-06-03T21:16:58.349230',
                 'cypher_type': None,
                 'name': 'test_1',
                 'algorithm': None,
                 'created': '2013-06-03T21:16:58.349222',
                 'secret_ref': 'http://localhost:9311/v1/'
                               'None/secrets/bbd2036f-730'
                               '7-4090-bbef-bbb6025e5e7b',
                 'expiration': None,
                 'bit_length': None,
                 'mime_type': 'text/plain'}],
                 'previous': "{0}/{1}?limit={2}&offset={2}".format(
                             self.client._tenant,
                             self.client.
                             SECRETS_PATH,
                             limit)}

        body2 = body1
        body2['secrets'][0]['name'] = 'test_2'
        body2['secrets'][0]['secret_ref'] = 'http://localhost:9311/v1/No'\
                                            + 'ne/secrets/bbd2036f-7307-'\
                                            + '4090-bbef-bbb6025eabcd'
        body2['previous'] = 'http://localhost:9311/v1/None/secrets/19106'\
                            + 'b6e-4ef1-48d1-8950-170c1a5838e1'
        body2['next'] = None

        secrets = [client.Secret(self.client, b['secrets'][0])
                   for b in (body1, body2)]
        body2['secrets'].insert(0, body1['secrets'][0])
        self.request.return_value.content = json.dumps(body2)
        secret_list, prev_ref, next_ref = self.client.list_secrets(limit, 1)
        self.assertTrue(self._are_equivalent(secrets, secret_list))
        self.assertEqual(body2['previous'], prev_ref)
        self.assertIsNone(next_ref)

    def test_list_no_orders(self):
        body0 = {'orders': []}
        orders = []
        self.request.return_value.content = json.dumps(body0)
        order_list, prev_ref, next_ref = self.client.list_orders(0, 0)
        self.assertTrue(self._are_equivalent(orders, order_list))
        self.assertIsNone(prev_ref)
        self.assertIsNone(next_ref)

    def test_list_single_order(self):
        limit = 1
        body1 = {'orders': [{'status': 'PENDING',
                             'updated': '2013-06-05T15:15:30.904760',
                             'created': '2013-06-05T15:15:30.904752',
                             'order_ref': 'http://localhost:9311/v1/'
                                          'None/orders/9f651441-3ccd'
                                          '-45b3-bc60-3051656d5168',
                             'secret_ref': 'http://localhost:9311/'
                                           'v1/None/secrets/????',
                             'secret': {'cypher_type': None,
                                        'name': 'test_1',
                                        'algorithm': None,
                                        'expiration': None,
                                        'bit_length': None,
                                        'mime_type': 'text/plain'}}],
                 'next': "{0}/{1}?limit={2}&offset={2}".format(self.client.
                                                               _tenant,
                                                               self.client.
                                                               ORDERS_PATH,
                                                               limit)}
        orders = [client.Order(self.client, body1['orders'][0])]
        self.request.return_value.content = json.dumps(body1)
        order_list, prev_ref, next_ref = self.client.list_orders(limit, 0)
        self.assertTrue(self._are_equivalent(orders, order_list))
        self.assertIsNone(prev_ref)
        self.assertEqual(body1['next'], next_ref)

    def test_list_multiple_orders(self):
        limit = 2
        body1 = {'orders': [{'status': 'PENDING',
                             'updated': '2013-06-05T15:15:30.904760',
                             'created': '2013-06-05T15:15:30.904752',
                             'order_ref': 'http://localhost:9311/v1/'
                                          'None/orders/9f651441-3ccd'
                                          '-45b3-bc60-3051656d5168',
                             'secret_ref': 'http://localhost:9311/'
                                           'v1/None/secrets/????',
                             'secret': {'cypher_type': None,
                                        'name': 'test_1',
                                        'algorithm': None,
                                        'expiration': None,
                                        'bit_length': None,
                                        'mime_type': 'text/plain'}}],
                 'previous': "{0}/{1}?limit={2}&offset={2}".format(
                             self.client._tenant,
                             self.client.
                             SECRETS_PATH,
                             limit)}
        body2 = body1
        body2['orders'][0]['order_ref'] = 'http://localhost:9311/v1/No'\
                                          + 'ne/orders/9f651441-3ccd-4'\
                                          + '5b3-bc60-3051656382fj'
        body2['orders'][0]['secret']['name'] = 'test_2'

        body2['orders'][0]['name'] = 'test_2'
        body2['orders'][0]['secret_ref'] = 'http://localhost:9311/v1/No'\
                                           + 'ne/secrets/bbd2036f-7307-'\
                                           + '4090-bbef-bbb6025eabcd'
        body2['previous'] = 'http://localhost:9311/v1/None/orders/19106'\
                            + 'b6e-4ef1-48d1-8950-170c1a5838e1'
        body2['next'] = None

        orders = [client.Order(self.client, b['orders'][0])
                  for b in (body1, body2)]
        body2['orders'].insert(0, body1['orders'][0])
        self.request.return_value.content = json.dumps(body2)
        order_list, prev_ref, next_ref = self.client.list_orders(limit, 1)
        self.assertTrue(self._are_equivalent(orders, order_list))
        self.assertEqual(body2['previous'], prev_ref)
        self.assertIsNone(next_ref)

    def test_should_get_response(self):
        self._setup_request()
        headers, body = self.client._perform_http('GET', self.href)
        self.assertEqual(self.request.return_value.headers, headers)
        self.assertEqual(json.loads(self.request.return_value.content), body)

    def test_should_parse_json(self):
        self._setup_request()
        headers, body = self.client._perform_http('GET', self.href,
                                                  parse_json=True)
        self.assertEqual(json.loads(self.request.return_value.content), body)

    def test_should_not_parse_json(self):
        self._setup_request()
        headers, body = self.client._perform_http('GET', self.href,
                                                  parse_json=False)
        self.assertEqual(self.request.return_value.content, body)

    def test_should_raise_for_bad_response(self):
        self._setup_request()
        self.request.return_value.ok = False
        self.request.return_value.status_code = 404
        with self.assertRaises(ClientException) as e:
            self.client._perform_http('GET', self.href)
        exception = e.exception
        self.assertEqual(404, exception.http_status)

    def _setup_request(self):
        self.request.return_value.headers = {'Accept': 'application/json'}
        self.request.return_value.content = '{"test": "response"}'
        self.href = 'http://localhost:9311/v1/12345/orders'

    def _are_equivalent(self, a, b):
        if isinstance(a, list) and isinstance(b, list):
            return all([self._are_equivalent(x, y) for x, y in zip(a, b)])
        else:
            return (a.__dict__ == b.__dict__)