# -*- coding: utf-8 -*-
# Copyright 2016 LasLabs Inc.
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

import logging
import os
import socket

from contextlib import contextmanager
from threading import Lock

from openerp.tools import classproperty
from werkzeug.local import Local

_logger = logging.getLogger(__name__)

try:
    import paramiko
except ImportError:
    _logger.warning('Cannot import paramiko.')


class SSHEnvironments(set):
    """ It provides a common object for all environments for a request """


class SSHEnvironment(object):
    """ It provides an environment for thread-safe management of SSH sessions

    Attributes:
        RETRY_EXCEPTIONS: (list) Exceptions that will cause an SSH
            reconnection attempt.
        RETRY_MAX: (int) Maximum amount of consecutive SSH connection
            reconnection attempts before failure.
        client: (paramiko.Client|None) Raw Paramiko SSH connection. None if
            not connected.
        host: (str) Node Hostname/IP that is used for connection.
        port: (int) Port number used for connection.
        username: (str) Username used for authentication.
        identify_file: (str) Path to the SSH identity file

    TODO:
        * Create a transport registry
        * Add locking at transport level
        * Allow host key policy configuration
    """

    RETRY_EXCEPTIONS = [
        paramiko.ssh_exception.SSHException,
        paramiko.ssh_exception.ChannelException,
        socket.error,
    ]
    RETRY_MAX = 5
    _local = Local()

    @classproperty
    def envs(cls):
        """ It returns the current, or creates new, Environments """
        try:
            return cls._local.environments
        except AttributeError:
            cls.reset()
            return cls._local.environments

    @classmethod
    def reset(cls):
        """ It creates a new set of Environments and scrubs the old """
        _logger.debug('Resetting SSHEnvironment')
        try:
            for env in cls._local.environments:
                env._cleanup()
        except AttributeError:
            pass
        cls._local.environments = SSHEnvironments()

    @contextmanager
    def get_channel(self, retry=True):
        """ It provides context manager yielding a new Paramiko channel """
        try:
            transport = self.client.get_transport()
            with transport.open_session() as channel:
                yield channel
        except tuple(self.RETRY_EXCEPTIONS + [AttributeError]):
            if retry:
                self._connect()
                with self.get_channel(False) as channel:
                    yield channel
            else:
                raise

    def _cleanup(self):
        """ It provides a handler to close existing resources """
        if self.client:
            try:
                self.client.close()
            except:  # pragma: no cover
                _logger.info('Client close failed for %s', self.client)
        self.client = None

    def _connect(self):
        """ It creates an SSH connection to remote node """
        self._cleanup()
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            self.client.connect(
                self.host,
                port=self.port,
                username=self.username,
                key_filename=os.path.expanduser(self.identity_file),
            )
            self._retry_left = self.RETRY_MAX
        except tuple(self.RETRY_EXCEPTIONS):
            if self._retry_left:
                self._retry_left -= 1
                self._connect()
            else:
                self.client = None
                raise

    def __wrap_method(self, method):
        """ It injects a lock and a reconnect onto the method """
        locked = self.__inject_lock(method)
        return self.__inject_reconnect(locked)

    def __inject_lock(self, method):
        """ It injects a thread lock onto the method """

        def __call_method(*args, **kwargs):
            self._lock.acquire(True)
            try:
                return method(*args, **kwargs)
            finally:
                self._lock.release()

        return __call_method

    def __inject_reconnect(self, method):
        """ It injects a reconnector onto the method """

        def __call_method(*args, **kwargs):
            try:
                return method(*args, **kwargs)
            except tuple(self.RETRY_EXCEPTIONS):
                self._connect()
                return method(*args, **kwargs)

        return __call_method

    def __new__(cls, host, port=22, username=None, identity_file=None,
                connect=True, *args, **kwargs
                ):
        """ It returns a cached SSHEnvironment, or creates a new one.

        The bulk of this method is only called once when the SSHEnvironment
        is instantiated for the first time. Subsequent instantiations will
        return a cached SSHEnvironment & skip the initiatizations.

        Params:
            host: (str) Host or IP of remote node.
            post: (int) Remote SSH port.
            username: (str|None) Username for connection. None for shell
                default.
            identity_file: (str|None) Path to the SSH identity file
            connect: (bool) If a connection should be initiated automatically
        """

        eval_args = (host, port, username, identity_file)

        for env in cls.envs:
            if env._eval_args == eval_args:
                return env

        self = object.__new__(cls, *args, **kwargs)
        cls.envs.add(self)

        self.host = host
        self.port = port
        self.username = username
        self.identity_file = identity_file
        self.client = None
        self._retry_left = self.RETRY_MAX
        self._args = args
        self._kwargs = kwargs
        self._eval_args = eval_args
        self._lock = Lock()

        if connect:
            self._connect()

        return self

    def __init__(self, *args, **kwargs):
        """ It initializes a new SSHEnvironment.

        Note that ``__init__`` will be run the first time an Environment is
        used in a session, regardless of whether it was cached. This method
        currently does nothing, but could be useful for environment prep

        Params:
            host: (str) Host or IP of remote node.
            post: (int) Remote SSH port.
            username: (str|None) Username for connection. None for shell
                default.
            identity_file: (str|None) Path to the SSH identity file
            connect: (bool) If a connection should be initiated automatically
        """
        pass

    def __getattr__(self, key):
        """ Provide passthrough to paramiko Client while locking the conn """
        try:
            return super(SSHEnvironment, self).__getattr__(key)
        except AttributeError:
            pass
        method = getattr(self.client, key)
        if not callable(method):
            return method
        return self.__wrap_method(method)

    def __str__(self):
        """ Allow object rebuilds """
        return '%(class)s(*%(args)r, **%(kwargs)r)' % {
            'class': self.__class__.__name__,
            'args': self._eval_args + self._args,
            'kwargs': self._kwargs,
        }

    def __repr__(self):
        return self.__str__()
