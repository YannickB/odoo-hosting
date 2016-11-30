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

from openerp import models, api


class ClouderServer(models.Model):
    """
    Add methods to manage the postgres specificities.
    """

    _inherit = 'clouder.server'

    @api.multi
    def oneclick_deploy_exec(self):

        super(ClouderServer, self).oneclick_deploy_exec()

        for oneclick in self.oneclick_ids:
            if oneclick.code == 'drupal':
                self.oneclick_deploy_element('service', 'drupal-all')
                self.oneclick_deploy_element(
                    'base', 'drupal', code_service='drupal-all-drupal')

    @api.multi
    def oneclick_purge_exec(self):

        service_obj = self.env['clouder.service']

        service_obj.search([('environment_id', '=', self.environment_id.id),
                            ('suffix', '=', 'drupal-all')]).unlink()

        super(ClouderServer, self).oneclick_purge_exec()
