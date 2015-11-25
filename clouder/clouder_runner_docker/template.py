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

from openerp import models, api, _
from openerp.exceptions import except_orm
import re


class ClouderContainer(models.Model):
    """
    Add methods to manage the docker container specificities.
    """

    _inherit = 'clouder.container'

    @api.multi
    def write(self, vals):
        """
        Override write method to trigger a deploy_post when we change the
        public key.

        :param vals: The values to update.
        """
        res = super(ClouderContainer, self).write(vals)
        if 'option_ids' in vals:
            if self.application_id.type_id.name == 'docker' \
                    and 'public_key' in self.options:
                self.deploy_post()
        return res

    @api.model
    def create(self, vals):
        """
        Ensure the ports are correctly configured.

        :param vals: The values which will be used to create the container.
        """

        application = 'application_id' in vals \
            and self.env['clouder.application'].browse(vals['application_id'])

        if application and application.type_id.name == 'docker':

            ports = ''
            type_option_obj = self.env['clouder.application.type.option']
            if 'option_ids' in vals:
                for option in vals['option_ids']:
                    option = option[2]
                    type_option = type_option_obj.browse(option['name'])
                    if type_option.name == 'ports':
                        ports = option['value']
            if ports:
                if not re.match("^[\d,-]*$", ports):
                    raise except_orm(
                        _('Data error!'),
                        _("Ports can only contains digits, - and ,"))

                for scope in ports.split(','):
                    if re.match("^[\d]*$", scope):
                        start_port = scope
                        end_port = scope
                    else:
                        start_port = scope.split('-')[0]
                        end_port = scope.split('-')[1]

                    start_port = int(start_port)
                    end_port = int(end_port)
                    if start_port > end_port:
                        start_port_temp = start_port
                        start_port = end_port
                        end_port = start_port_temp

                    i = start_port
                    while i <= end_port:
                        vals['port_ids'].append((0, 0, {
                            'name': str(i), 'localport': str(i),
                            'hostport': str(i), 'expose': 'internet'}))
                        i += 1

        return super(ClouderContainer, self).create(vals)

    @api.multi
    def hook_deploy_special_args(self, cmd):
        cmd = super(ClouderContainer, self).hook_deploy_special_args(cmd)
        if self.application_id.type_id.name == 'docker':
            cmd.extend(['--privileged'])
        return cmd

    @api.multi
    def deploy_post(self):
        """
        Add the public key to the allowed keys in the container.
        """
        super(ClouderContainer, self).deploy_post()
        if self.application_id.type_id.name == 'docker':
            if 'public_key' in self.options \
                    and self.options['public_key']['value']:
                ssh = self.connect(self.fullname)
                self.execute(ssh, [
                    'echo "' + self.options['public_key']['value'] +
                    '" > /root/.ssh/authorized_keys2'])
                ssh.close()

