# -*- coding: utf-8 -*-
##############################################################################
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

from openerp import modules
from openerp import models, fields, api, _
import openerp.addons.clouder.clouder_model as clouder_model


class ClouderContainer(models.Model):
    _inherit = 'clouder.container'

    @api.multi
    def create_vals(self):
        vals = super(ClouderContainer, self).create_vals()
        if 'application_id' in vals and vals['application_id']:
            application = self.env['clouder.application'].browse(vals['application_id'])
            if application.type_id.name == 'openldap':
                if not 'option_ids' in vals:
                    vals['options_ids'] = []

                password_option = self.env.ref('clouder_ldap.apptype_openldap_option2').id
                flag = False
                for option in vals['option_ids']:
                    if option[2]['name'] == password_option:
                        if not option[2]['value']:
                            option[2]['value'] = clouder_model.generate_random_password(20)
                        flag = True

                if not flag:
                    vals['option_ids'].append((0,0,{'name': password_option, 'value': clouder_model.generate_random_password(20)}))
        return vals

    @api.multi
    def deploy_post(self):
        super(ClouderContainer, self).deploy_post()
        if self.application_id.type_id.name == 'openldap':
            ssh, sftp = self.connect(self.fullname())

            self.execute(ssh, ['echo "slapd slapd/internal/generated_adminpw password ' + self.options()['password']['value'] + '"', '|', 'debconf-set-selections'])
            self.execute(ssh, ['echo "slapd slapd/password2 password ' + self.options()['password']['value'] + '"', '|', 'debconf-set-selections'])
            self.execute(ssh, ['echo "slapd slapd/internal/adminpw password ' + self.options()['password']['value'] + '"', '|', 'debconf-set-selections'])
            self.execute(ssh, ['echo "slapd slapd/password1 password ' + self.options()['password']['value'] + '"', '|', 'debconf-set-selections'])
            self.execute(ssh, ['echo "slapd shared/organization string ' + self.options()['organization']['value'] + '"', '|', 'debconf-set-selections'])
            self.execute(ssh, ['echo "slapd slapd/domain string ' + self.options()['domain']['value'] + '"', '|', 'debconf-set-selections'])
            self.execute(ssh, ['dpkg-reconfigure', '-f', 'noninteractive', 'slapd'])

            config_file = '/etc/ldap/schema/' + self.options()['domain']['value'] + '.ldif'
            sftp.put(modules.get_module_path('clouder_ldap') + '/res/ldap.ldif', config_file)
            domain_dc = ''
            for dc in self.options()['value'].split('.'):
                if domain_dc:
                    domain_dc += ','
                domain_dc += 'dc=' + dc

            self.execute(ssh, ['sed', '-i', '"s/\$DOMAIN/' + domain_dc + '/g"', config_file])
            self.execute(ssh, ['sed', '-i', '"s/\$PASSWORD/' + self.options()['password']['value'] + '/g"', config_file])
            self.execute(ssh, ['sed', '-i', '"s/\$ORGANIZATION/' + self.options()['organization']['value'] + '/g"', config_file])
            self.execute(ssh, ['sed', '-i', '"s/dc=example,dc=com/' + domain_dc + '/g"', '/etc/phpldapadmin/config.php'])
            ssh.close(), sftp.close()
            self.start()
            ssh, sftp = self.connect(self.container.fullname())
            self.execute(ssh, ['ldapadd', '-Y', 'EXTERNAL', '-H', 'ldapi:///', '-f', config_file])
            ssh.close(), sftp.close()