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

    _inherit = 'clouder.container'

    @api.multi
    def hook_deploy_special_args(self, cmd):
        cmd = super(ClouderContainer, self).hook_deploy_special_args(cmd)
        if self.application_id.type_id.name == 'kubernetes':
            cmd.extend(['--net=host'])
        return cmd

    @api.multi
    def hook_deploy_special_cmd(self):
        if self.application_id.type_id.name == 'kubernetes':
            return '/hyperkube kubelet \
                          --api-servers=http://127.0.0.1:8080 \
                          --config=/etc/kubernetes/manifests \
                          --hostname-override=127.0.0.1 \
                          --address=0.0.0.0 \
                          --v=5'
        else:
            return super(ClouderContainer, self).hook_deploy_special_cmd()
