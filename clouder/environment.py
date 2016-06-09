# -*- coding: utf-8 -*-
##############################################################################
#
# Author: Yannick Buron
# Copyright 2015, TODAY Clouder SASU
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License with Attribution
# clause as published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License with
# Attribution clause along with this program. If not, see
# <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp import models, fields, api, _
from openerp.exceptions import except_orm
from openerp import modules

import model

import re

import time
from datetime import datetime, timedelta

import logging
_logger = logging.getLogger(__name__)


class ClouderEnvironment(models.Model):
    """
    Define the environment object, which represent the environment where
    the container are created and link them to the allowed users.
    """

    _name = 'clouder.environment'

    name = fields.Char('Name', required=True)
    partner_id = fields.Many2one('res.partner', 'Partner', required=True)
    prefix = fields.Char('Prefix', required=False)
    user_ids = fields.Many2many(
        'res.users', 'clouder_environment_user_rel',
        'environment_id', 'user_id', 'Users')
    container_ids = fields.One2many(
        'clouder.container', 'environment_id', 'Containers')

    _sql_constraints = [
        ('name_uniq', 'unique(name)',
         'Name must be unique!'),
        ('prefix_uniq', 'unique(prefix)',
         'Prefix must be unique!'),
    ]

    @api.one
    @api.constrains('prefix')
    def _validate_data(self):
        """
        Check that the prefix does not contain any forbidden
        characters.
        """
        if self.prefix and not re.match("^[\w]*$", self.prefix):
            raise except_orm(
                _('Data error!'),
                _("Prefix can only contains letters"))
