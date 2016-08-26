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
from .. import model


class ClouderServer(models.Model):
    """
    """

    _inherit = 'clouder.server'


    @api.multi
    def deploy(self):
        """
        """

        super(ClouderServer, self).deploy()

        application = self.env.ref('clouder.app_salt_minion')
        self.env['clouder.container'].create({
            'environment_id': self.environment_id.id,
            'suffix': 'salt-minion',
            'application_id': application.id,
            'server_id': self.id,
            'image_id': application.default_image_id.id
        })

    @api.multi
    def purge(self):
        """
        """

        salt = self.env['clouder.container'].search([('environment_id', '=', self.environment_id.id), ('server_id', '=', self.id), ('suffix', '=', 'salt-minion')])
        salt.unlink()

        super(ClouderServer, self).purge()

class ClouderContainer(models.Model):
    """
    """

    _inherit = 'clouder.container'

    @api.multi
    def deploy_post(self):
        super(ClouderContainer, self).deploy_post()
        if self.application_id.type_id.name == 'salt-minion':
            config_file = '/etc/salt/minion'
            self.execute(['sed', '-i', '"s/#master: salt/master: ' + self.env.ref('clouder.clouder_settings').salt_host + '/g"', config_file])
            self.execute(['sed', '-i', '"s/#master_port: 4506/master_port: ' + self.env.ref('clouder.clouder_settings').salt_port + '/g"', config_file])