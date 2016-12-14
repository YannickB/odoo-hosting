# -*- coding: utf-8 -*-
# Copyright 2015 Clouder SASU
# License LGPL-3.0 or later (http://gnu.org/licenses/lgpl.html).

from odoo import models, api
import re


class ClouderService(models.Model):
    """
    Add methods to manage the docker service specificities.
    """

    _inherit = 'clouder.service'

    @api.multi
    def write(self, vals):
        """
        Override write method to trigger a deploy_post when we change the
        public key.

        :param vals: The values to update.
        """
        res = super(ClouderService, self).write(vals)
        if 'option_ids' in vals:
            if self.application_id.type_id.name == 'docker' \
                    and 'public_key' in self.options:
                self.deploy_post()
        return res

    @api.model
    def create(self, vals):
        """
        Ensure the ports are correctly configured.

        :param vals: The values which will be used to create the service.
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
                if not re.match(r"^[\d,-]*$", ports):
                    self.raise_error(
                        "Ports can only contains digits, - and ,",
                    )

                for scope in ports.split(','):
                    if re.match(r"^[\d]*$", scope):
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
                            'name': str(i), 'local_port': str(i),
                            'hostport': str(i), 'expose': 'internet'}))
                        i += 1

        return super(ClouderService, self).create(vals)

    @api.multi
    def hook_deploy_special_args(self, cmd):
        cmd = super(ClouderService, self).hook_deploy_special_args(cmd)
        if self.application_id.type_id.name == 'docker':
            cmd.extend(['--privileged'])
        return cmd

    @api.multi
    def deploy_post(self):
        """
        Add the public key to the allowed keys in the service.
        """
        super(ClouderService, self).deploy_post()
        if self.application_id.type_id.name == 'docker':
            if 'public_key' in self.options \
                    and self.options['public_key']['value']:
                ssh = self.connect(self.fullname)
                self.execute(ssh, [
                    'echo "' + self.options['public_key']['value'] +
                    '" > /root/.ssh/authorized_keys2'])
                ssh.close()
