# -*- coding: utf-8 -*-
# Copyright 2016 LasLabs Inc.
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

import mock
import os.path

from contextlib import contextmanager

from ..common import SetUpClouderTest
from ...ssh.environment import Local, SSHEnvironment, SSHEnvironments


MODULE_PATH = 'openerp.addons.clouder.ssh.environment'


class TestSSHEnvironment(SetUpClouderTest):

    def setUp(self):
        super(TestSSHEnvironment, self).setUp()
        SSHEnvironment.reset()

    @contextmanager
    def mock_envs(self):
        """ It mocks SSHEnvironment._local.environments & yields the mock """
        envs = mock.MagicMock()
        SSHEnvironment._local.environments = envs
        yield envs

    @contextmanager
    def mock_paramiko(self):
        """ It mocks paramiko & yields the mock """
        with mock.patch('%s.paramiko' % MODULE_PATH) as paramiko:
            yield paramiko

    @contextmanager
    def mock_environment(
        self, host='host', port=2222, user='user',
        identity_file='identity', connect=True,
    ):
        """ It initializes & yields a new SSHEnvironment """
        self.host = host
        self.port = port
        self.username = user
        self.identity_file = identity_file
        self.connect = connect
        self.args = (1, 2)
        self.kwargs = {'test': 'kwarg'}
        self.eval_args = (host, port, user, identity_file)
        with self.mock_paramiko() as paramiko:
            self.paramiko = paramiko
            yield SSHEnvironment(
                host, port, user, identity_file, connect,
                *self.args, **self.kwargs
            )

    def _test_instance_attr(self, attr, self_attr):
        """ It provides a helper to test instance attrs of env """
        with self.mock_environment() as env:
            self.assertEqual(
                getattr(env, attr),
                getattr(self, self_attr),
            )

    def test_envs(self):
        """ It should return environments if any """
        with self.mock_envs() as envs:
            self.assertEqual(SSHEnvironment.envs, envs)

    def test_envs_create(self):
        """ It should create a new environment if not existing """
        SSHEnvironment._local = Local()
        self.assertIsInstance(
            SSHEnvironment.envs,
            SSHEnvironments,
        )

    def test_reset_cleans_existing(self):
        """ It should clean existing environments if existing """
        with mock.patch.object(SSHEnvironment, '_local') as _local:
            env = mock.MagicMock()
            _local.environments = [env]
            SSHEnvironment.reset()
            env._cleanup.assert_called_once_with()

    def test_reset_creates_new(self):
        """ It should create and assign new Environments """
        SSHEnvironment.reset()
        self.assertIsInstance(
            SSHEnvironment._local.environments,
            SSHEnvironments,
        )

    def test_get_channel_gets_transport(self):
        """ It should get the transport for client """
        with self.mock_environment() as env:
            get_transport = env.client.get_transport
            get_transport.side_effect = self.EndTestException
            with self.assertRaises(self.EndTestException):
                with env.get_channel():
                    pass

    def test_get_channel_opens_session(self):
        """ It should yield an open session context manager """
        with self.mock_environment() as env:
            open_session = env.client.get_transport().open_session
            with env.get_channel() as channel:
                self.assertEqual(
                    channel,
                    open_session().__enter__()
                )

    def test_get_channel_reconnect(self):
        """ It should attempt a reconnect on failure """
        with self.mock_environment() as env:
            get_transport = self.paramiko.SSHClient().get_transport
            get_transport.side_effect = SSHEnvironment.RETRY_EXCEPTIONS[0]
            with mock.patch.object(env, '_connect') as connect:
                connect.side_effect = self.EndTestException
                with self.assertRaises(self.EndTestException):
                    with env.get_channel():
                        pass

    def test_get_channel_reconnect_recurse(self):
        """ It should reattempt channel creation after connect """
        with self.mock_environment() as env:
            get_transport = self.paramiko.SSHClient().get_transport
            other_transport = mock.MagicMock()
            get_transport.side_effect = [SSHEnvironment.RETRY_EXCEPTIONS[0],
                                         other_transport,
                                         ]
            with env.get_channel() as channel:
                self.assertEqual(
                    channel,
                    other_transport.open_session().__enter__(),
                )

    def test_get_channel_no_client(self):
        """ It should attempt a connection if there is no client """
        with self.mock_environment() as env:
            env.client = None
            with mock.patch.object(env, '_connect') as connect:
                connect.side_effect = self.EndTestException
                with self.assertRaises(self.EndTestException):
                    with env.get_channel():
                        pass

    def test_get_channel_retry(self):
        """ It should reattempt channel creation after reconnect """
        with self.mock_environment() as env:
            get_transport = env.client.get_transport
            get_transport.side_effect = [
                SSHEnvironment.RETRY_EXCEPTIONS[0],
                self.EndTestException,
            ]
            with self.assertRaises(self.EndTestException):
                with env.get_channel():
                    pass

    def test_get_channel_infinite(self):
        """ It should not infinitely loop channel failures """
        with self.mock_environment() as env:
            get_transport = env.client.get_transport
            get_transport.side_effect = SSHEnvironment.RETRY_EXCEPTIONS[0]
            with self.assertRaises(SSHEnvironment.RETRY_EXCEPTIONS[0]):
                with env.get_channel():
                    pass

    def test_cleanup_closes_client(self):
        """ It should close existing client connection """
        with self.mock_environment() as env:
            env._cleanup()
            self.paramiko.SSHClient().close.assert_called_once_with()

    def test_cleanup_sets_client_to_none(self):
        """ It should reset client to None on cleanup """
        with self.mock_environment() as env:
            self.assertTrue(env.client)
            env._cleanup()
            self.assertIs(env.client, None)

    def test_connect_cleans_first(self):
        """ It should cleanup existing resources before creating new """
        with self.mock_environment() as env:
            with mock.patch.object(env, '_cleanup') as cleanup:
                cleanup.side_effect = self.EndTestException
                with self.assertRaises(self.EndTestException):
                    env._connect()

    def test_connect_gets_client(self):
        """ It should init a new paramiko.SSHClient as client """
        with self.mock_environment() as env:
            self.assertEqual(
                env.client,
                self.paramiko.SSHClient(),
            )

    def test_connect_sets_policy(self):
        """ It should set the host key policy to AutoAdd """
        with self.mock_environment():
            client = self.paramiko.SSHClient()
            client.set_missing_host_key_policy.assert_called_once_with(
                self.paramiko.AutoAddPolicy(),
            )

    def test_connect_connects(self):
        """ It should connect to SSH node with proper args """
        with self.mock_environment():
            self.paramiko.SSHClient().connect.assert_called_once_with(
                self.host,
                port=self.port,
                username=self.username,
                key_filename=os.path.expanduser(self.identity_file),
            )

    def test_connect_retries(self):
        """ It should retry connection on failure """
        with self.mock_environment(connect=False) as env:
            connect = self.paramiko.SSHClient().connect
            connect.side_effect = [
                SSHEnvironment.RETRY_EXCEPTIONS[0],
                self.EndTestException,
            ]
            with self.assertRaises(self.EndTestException):
                env._connect()

    def test_connect_infinite(self):
        """ It should not attempt to connect infinitely """
        with self.mock_environment(connect=False) as env:
            connect = self.paramiko.SSHClient().connect
            connect.side_effect = SSHEnvironment.RETRY_EXCEPTIONS[0]
            with self.assertRaises(SSHEnvironment.RETRY_EXCEPTIONS[0]):
                env._connect()
            self.assertIs(env.client, None)

    @mock.patch('%s.Lock' % MODULE_PATH)
    def test_getitem_lock_wrap(self, Lock):
        """ It should wrap client methods with a thread lock """
        with self.mock_environment() as env:
            env.open_sftp()
            Lock().acquire.assert_called_once_with(True)

    @mock.patch('%s.Lock' % MODULE_PATH)
    def test_getitem_lock_release(self, Lock):
        """ It should release thread locks after method call """
        with self.mock_environment() as env:
            env.open_sftp()
            Lock().release.assert_called_once_with()

    @mock.patch.object(SSHEnvironment, '_connect')
    def test_getitem_connect_wrap(self, _connect):
        """ It should wrap client methods with a reconnect attempt """
        with self.mock_environment(connect=False) as env:
            env.client = mock.MagicMock()
            env.client.open_sftp.side_effect = [
                SSHEnvironment.RETRY_EXCEPTIONS[0],
                mock.MagicMock(),
            ]
            env.open_sftp()
            _connect.assert_called_once_with()

    def test_getitem_wrap_return(self):
        """ It should return the result of the wrapped methods """
        with self.mock_environment() as env:
            expect = 'expect'
            env.client = mock.MagicMock()
            env.client.open_sftp.return_value = expect
            res = env.open_sftp()
            self.assertEqual(res, expect)

    def test_getitem_wrap_no_call(self):
        """ It should return the result of the wrapped methods """
        with self.mock_environment() as env:
            expect = 'expect'
            env.client = mock.MagicMock()
            env.client.some_text = expect
            res = env.some_text
            self.assertEqual(res, expect)

    def test_new_sets_host(self):
        self._test_instance_attr('host', 'host')

    def test_new_sets_port(self):
        self._test_instance_attr('port', 'port')

    def test_new_sets_username(self):
        self._test_instance_attr('username', 'username')

    def test_new_sets_identity_file(self):
        self._test_instance_attr('identity_file', 'identity_file')

    def test_new_sets_retry_left(self):
        self.retries = 5
        self._test_instance_attr('_retry_left', 'retries')

    def test_new_sets_args(self):
        self._test_instance_attr('_args', 'args')

    def test_new_sets_eval_args(self):
        self._test_instance_attr('_eval_args', 'eval_args')

    @mock.patch('%s.Lock' % MODULE_PATH)
    def test_new_sets_lock(self, Lock):
        self.lock = Lock()
        self._test_instance_attr('_lock', 'lock')

    @mock.patch.object(SSHEnvironment, '_connect')
    def test_new_connect_true(self, _connect):
        """ It should connect to node """
        with self.mock_environment():
            _connect.assert_called_once_with()

    def test_new_connect_false(self):
        """ It should not connect to node """
        with mock.patch.object(SSHEnvironment, '_connect') as _connect:
            with self.mock_environment(connect=False):
                _connect.assert_not_called()

    def test_new_returns_cached(self):
        """ It should return cached object if present """
        with self.mock_environment() as env1:
            with self.mock_environment() as env2:
                self.assertEqual(env1, env2)

    def test_str_can_rebuild(self):
        """ It should provide a properly rebuildable object """
        with self.mock_environment() as env_orig:
            env_new = eval(str(env_orig))  # pylint: disable=W0123
            self.assertIsInstance(env_new, SSHEnvironment)

    @mock.patch.object(SSHEnvironment, '__str__')
    def test_repr(self, __str__):
        """ It should return the result of ``__str__`` """
        __str__.return_value = 'expect'
        with self.mock_environment() as env:
            res = repr(env)
            self.assertEqual(res, 'expect')
