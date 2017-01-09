# -*- coding: utf-8 -*-
# Copyright 2016 LasLabs Inc.
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

import logging
import os
import subprocess
import unittest

from odoo.tests import common

_logger = logging.getLogger(__name__)


class EndTestException(Exception):
    """ It provides a dummy Exception used to stop tests """
    pass


class SetUpClouderTest(common.TransactionCase):
    """ It provides a base class for common test helpers """

    EndTestException = EndTestException


class SetUpDockerTest(unittest.TestCase):
    """ It provides a base class for Dockerfile tests. """

    def _read_process(self, process):
        """ It live-logs and returns the exit code from process.

        Args:
            process (subprocess.Popen): Process to run.
        Returns:
            int: Exit code from process.
        """
        collected = []
        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
            if output:
                collected.append(output.strip())
                _logger.debug(collected[-1])
            process.poll()
        return process.returncode

    def do_test_lint(self, image_path):
        """ It tests lint of the Dockerfile. """
        env = {'LINT_CHECK': '1'}
        self._do_test(env, image_path)

    def do_test_tests(self, image_path):
        """ It should run tests on the Docker image. """
        env = {'TESTS': '1'}
        self._do_test(env, image_path)

    def _do_test(self, env, image_path, exit_code=0):
        """ It runs the test process & fails if an invalid exit code.
        """
        os_env = os.environ.copy()
        os_env.update(env)
        dqt_path = '%s/docker-quality-tools' % os_env.get('HOME')
        os_env['PATH'] = '%s/travis:%s' % (
            dqt_path, os_env.get('PATH', '/bin'),
        )
        process = subprocess.Popen(
            '%s %s' % (
                os.path.join(dqt_path, 'tests', 'test_all'),
                image_path,
            ),
            shell=True,
            env=os_env,
            stdout=subprocess.PIPE,
        )
        self.assertEqual(
            self._read_process(process),
            exit_code,
        )
        return process.returncode
