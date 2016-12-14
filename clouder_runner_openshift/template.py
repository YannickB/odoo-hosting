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

from odoo import models, api


class ClouderContainer(models.Model):

    _inherit = 'clouder.service'

    @api.multi
    def hook_deploy_special_args(self, cmd):
        cmd = super(ClouderContainer, self).hook_deploy_special_args(cmd)
        if self.application_id.type_id.name == 'openshift':
            cmd.extend(['--net=host', '--privileged'])
        return cmd

    @api.multi
    def hook_deploy_special_cmd(self):
        if self.application_id.type_id.name == 'openshift':
            return 'start'
        else:
            return super(ClouderContainer, self).hook_deploy_special_cmd()
