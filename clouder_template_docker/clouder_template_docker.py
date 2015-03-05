# -*- coding: utf-8 -*-
# #############################################################################
#
#    Author: Yannick Buron
#    Copyright 2013 Yannick Buron
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


class ClouderContainer(models.Model):
    _inherit = 'clouder.container'

    @api.multi
    def write(self, vals):
        res = super(ClouderContainer, self).write(vals)
        if 'option_ids' in vals:
            if self.application_id.type_id.name == 'docker' \
                    and 'public_key' in self.options():
                self.deploy_post()
        return res

    @api.multi
    def create_vals(self, vals):
        super(ClouderContainer, self).create_vals(vals)
        if self.env.context['apptype_name'] == 'docker':
            start_port = ''
            end_port = ''
            type_option_obj = self.env['clouder.application.type.option']
            if 'option_ids' in vals:
                for option in vals['option_ids']:
                    option = option[2]
                    type_option = type_option_obj.browse(option['name'])
                    if type_option.name == 'start_port':
                        start_port = option['value']
                    if type_option.name == 'end_port':
                        end_port = option['value']
            if start_port and end_port:
                start_port = int(start_port)
                end_port = int(end_port)
                if start_port < end_port:
                    i = start_port
                    while i <= end_port:
                        vals['port_ids'].append((0, 0, {
                            'name': str(i), 'localport': str(i),
                            'hostport': str(i), 'expose': 'internet'}))
                        i += 1
                else:
                    raise except_orm(
                        _('Data error!'),
                        _("Start port need to be inferior to end port"))
            else:
                raise except_orm(_('Data error!'),
                                 _("You need to specify a start and end port"))

        return vals

    @api.multi
    def deploy_post(self):
        super(ClouderContainer, self).deploy_post()
        if self.application_id.type_id.name == 'docker':
            if 'public_key' in self.options():
                ssh = self.connect(self.fullname)
                self.execute(ssh, [
                    'echo "' + self.options()['public_key']['value'] +
                    '" > /root/.ssh/authorized_keys2'])
                ssh.close()

