# -*- coding: utf-8 -*-
# Copyright 2016 LasLabs Inc.
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

import os

from .common import SetUpDockerTest


class TestDockerClouderBase(SetUpDockerTest):

    def setUp(self):
        super(TestDockerClouderBase, self).setUp()
        self.image_path = os.path.abspath(os.path.join(
            os.path.dirname(__file__), '..', 'images', 'base'
        ))

    def test_lint(self):
        self.do_test_lint(self.image_path)

    def test_tests(self):
        self.do_test_tests(self.image_path)
