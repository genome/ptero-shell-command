import abc
import os
import platform
import pwd
import requests
import json
import subprocess
import tempfile
import time
import unittest

__all__ = ['BaseAPITest']


class WebhookServer:
    def __init__(self, response_codes):
        self._response_codes = response_codes
        self._webserver = None

    def start(self):
        if self._webserver:
            raise RuntimeError('Cannot start multiple webservers in one test')
        command_line = ['python', self._path,
                        '--stop-after', str(self._timeout), '--response-codes']
        command_line.extend(map(str, self._response_codes))
        self._webserver = subprocess.Popen(
            command_line, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self._wait()
        self._port = int(self._webserver.stderr.readline().rstrip())

    def stop(self):
        if self._webserver is not None:
            stdout, stderr = self._webserver.communicate()
            rc = self._webserver.returncode
            self._webserver = None

            if rc == -14:
                raise RuntimeError('logging_webserver timed out')
            elif rc != 0:
                raise RuntimeError(
                    'logging_webserver failed with return code %s' % rc)

            if stdout:
                return map(json.loads, stdout.split('\n')[:-1])
        return []

    def _wait(self):
        time.sleep(1)

    @property
    def url(self):
        return 'http://localhost:%d/' % self._port

    @property
    def _path(self):
        return os.path.join(os.path.dirname(__file__), 'logging_webserver.py')

    @property
    def _timeout(self):
        return 30


class BaseAPITest(unittest.TestCase):
    __metaclass__ = abc.ABCMeta

    def setUp(self):
        self.api_host = os.environ['PTERO_SHELL_COMMAND_HOST']
        self.api_port = os.environ['PTERO_SHELL_COMMAND_PORT']

        if platform.system() == 'Darwin':
            self.job_working_directory = tempfile.mkdtemp(dir='/private/tmp')
        else:
            self.job_working_directory = tempfile.mkdtemp()

    def tearDown(self):
        os.rmdir(self.job_working_directory)

    def create_webhook_server(self, response_codes):
        server = WebhookServer(response_codes)
        server.start()
        return server

    @property
    def jobs_url(self):
        return 'http://%s:%s/v1/jobs' % (self.api_host, self.api_port)

    @property
    def job_user(self):
        return pwd.getpwuid(os.getuid())[0]

    def get(self, url, **kwargs):
        return _deserialize_response(requests.get(url, params=kwargs))

    def patch(self, url, data):
        return _deserialize_response(
            requests.patch(url, headers={'content-type': 'application/json'},
                           data=json.dumps(data)))

    def post(self, url, data):
        return _deserialize_response(
            requests.post(url, headers={'content-type': 'application/json'},
                          data=json.dumps(data)))

    def put(self, url, data):
        return _deserialize_response(
            requests.put(url, headers={'content-type': 'application/json'},
                         data=json.dumps(data)))

    def delete(self, url):
        return _deserialize_response(requests.delete(url))


def _deserialize_response(response):
    response.DATA = response.json()
    return response
