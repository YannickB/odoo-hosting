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


class ClouderContainer(models.Model):
    """
    Add a property.
    """

    _inherit = 'clouder.container'


    @api.multi
    def hook_deploy_special_args(self, cmd):
        cmd = super(ClouderContainer, self).hook_deploy_special_args(cmd)
        if self.application_id.type_id.name == 'glances':
            cmd.extend(['--pid host'])
        return cmd


class ClouderContainerLink(models.Model):
    """
    Add methods to manage the glances specificities.
    """

    _inherit = 'clouder.container.link'

    @api.multi
    def deploy_link(self):
        """
        Configure postfix to redirect incoming mail to odoo.
        """
        super(ClouderContainerLink, self).deploy_link()
        if self.name.name.code == 'shinken' \
                and self.container_id.application_id.type_id.name == 'glances':

            self.target.deploy_shinken_server(self.container_id)

    @api.multi
    def purge_link(self):
        """
        Purge postfix configuration.
        """
        super(ClouderContainerLink, self).purge_link()
        super(ClouderContainerLink, self).deploy_link()
        if self.name.name.code == 'shinken' \
                and self.container_id.application_id.type_id.name == 'glances':

            self.target.purge_shinken_server(self.container_id)