# -*- coding: utf-8 -*-
##############################################################################
#
#    Author: Yannick Buron
#    Copyright 2015 Yannick Buron
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################


from openerp import models, fields, api, _
from openerp.exceptions import except_orm
from datetime import datetime
import re

import logging
_logger = logging.getLogger(__name__)


class ClouderApplication(models.Model):
    _name = 'clouder.application'

    container_price_partner_month = fields.Float('Price partner/month')
    container_price_user_month = fields.Float('Price partner/month')
    container_price_user_payer = fields.Selection(
        [('partner','Partner'),('user','User')], 'Payer for users')
    service_price_partner_month = fields.Float('Price partner/month')
    service_price_user_month = fields.Float('Price partner/month')
    service_price_user_payer = fields.Selection(
        [('partner','Partner'),('user','User')], 'Payer for users')
    base_price_partner_month = fields.Float('Price partner/month')
    base_price_user_month = fields.Float('Price partner/month')
    base_price_user_payer = fields.Selection(
        [('partner','Partner'),('user','User')], 'Payer for users')


class ClouderContainer(models.Model):
    _inherit = 'clouder.container'

    price_partner_month = fields.Float('Price partner/month')
    price_user_month = fields.Float('Price partner/month')
    price_user_payer = fields.Selection(
        [('partner','Partner'),('user','User')], 'Payer for users')


class ClouderService(models.Model):
    _inherit = 'clouder.service'

    price_partner_month = fields.Float('Price partner/month')
    price_user_month = fields.Float('Price partner/month')
    price_user_payer = fields.Selection(
        [('partner','Partner'),('user','User')], 'Payer for users')


class ClouderBase(models.Model):
    _inherit = 'clouder.base'

    price_partner_month = fields.Float('Price partner/month')
    price_user_month = fields.Float('Price partner/month')
    price_user_payer = fields.Selection(
        [('partner','Partner'),('user','User')], 'Payer for users')