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

from openerp import models, fields, api, http, _
from openerp.exceptions import except_orm
from openerp.http import request

import logging

_logger = logging.getLogger(__name__)


class ClouderContainer(models.Model):
    """
    Adds the creation function to the container
    """

    _inherit = 'clouder.container'

    def create_instance(self, data):
        """
        Creates a clouder container or base using provided data
        """
        # TODO: implement
        _logger.info("\n\nCREATE INSTANCE DATA: {0}\n\n".format(data))

        # TODO: return newly created model
        return 0


class WebsiteClouderCreate(http.Controller):
    """
    Defines a webpage to request creation of clouder container/bases
    """

    def create_form_validate(self, vals):
        """
        Checks that the necessary values are filled correctly
        """
        # TODO: implement
        vals['error'] = {}
        return vals

    @http.route(['/instance/new'], type='http', auth="public", website=True)
    def display_new_form(self, **post):
        """
        Displays the web form to create a new instance
        """
        values = {
            'error': {},
            'form_data': {}
        }

        return request.render("website_clouder_create.create_form", values)

    @http.route('/instance/new/validate', type='http', auth="public", website=True)
    def instance_new_form_validate(self, **post):
        """
        Validates data and launches the instance creation process
        """
        # Check that the form is correct
        values = self.create_form_validate(post)
        # Return to the first form on error
        if 'error' in values and values['error']:
            return request.render("website_clouder_create.create_form", values)

        res = request.env['clouder.container'].create_instance(values)

        return request.render("website_clouder_create.create_validation", {'res': res})
