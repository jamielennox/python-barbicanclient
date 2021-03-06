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
import logging
import os

from keystoneclient.auth.base import BaseAuthPlugin
from keystoneclient import session as ks_session

from barbicanclient import containers
from barbicanclient._i18n import _
from barbicanclient import orders
from barbicanclient import secrets


LOG = logging.getLogger(__name__)
_DEFAULT_SERVICE_TYPE = 'key-manager'
_DEFAULT_SERVICE_INTERFACE = 'public'
_DEFAULT_API_VERSION = 'v1'


class HTTPError(Exception):

    """Base exception for HTTP errors."""

    def __init__(self, message):
        super(HTTPError, self).__init__(message)


class HTTPServerError(HTTPError):

    """Raised for 5xx responses from the server."""
    pass


class HTTPClientError(HTTPError):

    """Raised for 4xx responses from the server."""
    pass


class HTTPAuthError(HTTPError):

    """Raised for 401 Unauthorized responses from the server."""
    pass


class Client(object):

    def __init__(self, session=None, endpoint=None, project_id=None,
                 verify=True, service_type=_DEFAULT_SERVICE_TYPE,
                 service_name=None, interface=_DEFAULT_SERVICE_INTERFACE,
                 region_name=None):
        """
        Barbican client object used to interact with barbican service.

        :param session: An instance of keystoneclient.session.Session that
            can be either authenticated, or not authenticated.  When using
            a non-authenticated Session, you must provide some additional
            parameters.  When no session is provided it will default to a
            non-authenticated Session.
        :param endpoint: Barbican endpoint url. Required when a session is not
            given, or when using a non-authentciated session.
            When using an authenticated session, the client will attempt
            to get an endpoint from the session.
        :param project_id: The project ID used for context in Barbican.
            Required when a session is not given, or when using a
            non-authenticated session.
            When using an authenticated session, the project ID will be
            provided by the authentication mechanism.
        :param verify: When a session is not given, the client will create
            a non-authenticated session.  This parameter is passed to the
            session that is created.  If set to False, it allows
            barbicanclient to perform "insecure" TLS (https) requests.
            The server's certificate will not be verified against any
            certificate authorities.
            WARNING: This option should be used with caution.
        :param service_type: Used as an endpoint filter when using an
            authenticated keystone session. Defaults to 'key-management'.
        :param service_name: Used as an endpoint filter when using an
            authenticated keystone session.
        :param interface: Used as an endpoint filter when using an
            authenticated keystone session. Defaults to 'public'.
        :param region_name: Used as an endpoint filter when using an
            authenticated keystone session.
        """
        LOG.debug("Creating Client object")

        self._session = session or ks_session.Session(verify=verify)

        if self._session.auth is None:
            self._validate_endpoint_and_project_id(endpoint, project_id)

        if endpoint is not None:
            self._barbican_endpoint = self._get_normalized_endpoint(endpoint)
        else:
            self._barbican_endpoint = self._get_normalized_endpoint(
                self._session.get_endpoint(
                    service_type=service_type, service_name=service_name,
                    interface=interface, region_name=region_name
                )
            )

        if project_id is None:
            self._default_headers = dict()
        else:
            # If provided we'll include the project ID in all requests.
            self._default_headers = {'X-Project-Id': project_id}

        self._base_url = '{0}/{1}'.format(self._barbican_endpoint,
                                          _DEFAULT_API_VERSION)

        self.secrets = secrets.SecretManager(self)
        self.orders = orders.OrderManager(self)
        self.containers = containers.ContainerManager(self)

    def _validate_endpoint_and_project_id(self, endpoint, project_id):
        if endpoint is None:
            raise ValueError('Barbican endpoint url must be provided when not '
                             'using auth in the Keystone Session.')
        if project_id is None:
            raise ValueError('Project ID must be provided when not using auth '
                             'in the Keystone Session')

    def _get_normalized_endpoint(self, endpoint):
        if endpoint.endswith('/'):
            endpoint = endpoint[:-1]
        return endpoint

    def _get(self, href, params=None):
        headers = {'Accept': 'application/json'}
        headers.update(self._default_headers)
        resp = self._session.get(href, params=params, headers=headers)
        self._check_status_code(resp)
        return resp.json()

    def _get_raw(self, href, headers):
        headers.update(self._default_headers)
        resp = self._session.get(href, headers=headers)
        self._check_status_code(resp)
        return resp.content

    def _delete(self, href, json=None):
        headers = dict()
        headers.update(self._default_headers)
        resp = self._session.delete(href, headers=headers, json=json)
        self._check_status_code(resp)

    def _post(self, path, data):
        url = '{0}/{1}/'.format(self._base_url, path)
        headers = {'Content-Type': 'application/json'}
        headers.update(self._default_headers)
        resp = self._session.post(url, data=json.dumps(data), headers=headers)
        self._check_status_code(resp)
        return resp.json()

    def _check_status_code(self, resp):
        status = resp.status_code
        LOG.debug('Response status {0}'.format(status))
        if status == 401:
            LOG.error('Auth error: {0}'.format(self._get_error_message(resp)))
            raise HTTPAuthError('{0}'.format(self._get_error_message(resp)))
        if not status or status >= 500:
            LOG.error('5xx Server error: {0}'.format(
                self._get_error_message(resp)
            ))
            raise HTTPServerError('{0}'.format(self._get_error_message(resp)))
        if status >= 400:
            LOG.error('4xx Client error: {0}'.format(
                self._get_error_message(resp)
            ))
            raise HTTPClientError('{0}'.format(self._get_error_message(resp)))

    def _get_error_message(self, resp):
        try:
            response_data = resp.json()
            message = response_data['title']
        except ValueError:
            message = resp.content
        return message


def env(*vars, **kwargs):
    """Search for the first defined of possibly many env vars

    Returns the first environment variable defined in vars, or
    returns the default defined in kwargs.

    Source: Keystone's shell.py
    """
    for v in vars:
        value = os.environ.get(v, None)
        if value:
            return value
    return kwargs.get('default', '')
