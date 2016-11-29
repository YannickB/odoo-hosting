# -*- coding: utf-8 -*-
# Copyright 2016 LasLabs Inc.
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from openerp.tests import common


class EndTestException(Exception):
    """ It provides a dummy Exception used to stop tests """
    pass


class SetUpClouderTest(common.TransactionCase):
    """ It provides a base class for common test helpers """

    EndTestException = EndTestException
