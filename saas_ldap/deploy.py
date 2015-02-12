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


from openerp import netsvc
from openerp import pooler
from openerp.osv import fields, osv, orm
from openerp.tools.translate import _

import time
from datetime import datetime, timedelta
import subprocess
import openerp.addons.saas.execute as execute
import erppeek

import logging
_logger = logging.getLogger(__name__)



class saas_container(osv.osv):
    _inherit = 'saas.container'

    def create_vals(self, cr, uid, vals, context=None):
        vals = super(saas_container, self).create_vals(cr, uid, vals, context=context)
        if 'application_id' in vals and vals['application_id']:
            application = self.pool.get('saas.application').browse(cr, uid, vals['application_id'], context=context)
            if application.type_id.name == 'openldap':
                if not 'option_ids' in vals:
                    vals['options_ids'] = []

                password_option = self.pool.get('ir.model.data').get_object(cr, uid, 'saas_ldap', 'apptype_openldap_option2').id
                flag = False
                for option in vals['option_ids']:
                    if option[2]['name'] == password_option:
                        if not option[2]['value']:
                            option[2]['value'] = execute.generate_random_password(20)
                        flag = True

                if not flag:
                    vals['option_ids'].append((0,0,{'name': password_option, 'value': execute.generate_random_password(20)}))
        return vals

    def deploy_post(self, cr, uid, vals, context):
        super(saas_container, self).deploy_post(cr, uid, vals, context)
        context.update({'saas-self': self, 'saas-cr': cr, 'saas-uid': uid})
        if vals['apptype_name'] == 'openldap':
            ssh, sftp = execute.connect(vals['container_fullname'], context=context)

            execute.execute(ssh, ['echo "slapd slapd/internal/generated_adminpw password ' + vals['container_options']['password']['value'] + '"', '|', 'debconf-set-selections'], context)
            execute.execute(ssh, ['echo "slapd slapd/password2 password ' + vals['container_options']['password']['value'] + '"', '|', 'debconf-set-selections'], context)
            execute.execute(ssh, ['echo "slapd slapd/internal/adminpw password ' + vals['container_options']['password']['value'] + '"', '|', 'debconf-set-selections'], context)
            execute.execute(ssh, ['echo "slapd slapd/password1 password ' + vals['container_options']['password']['value'] + '"', '|', 'debconf-set-selections'], context)
            execute.execute(ssh, ['echo "slapd shared/organization string ' + vals['container_options']['organization']['value'] + '"', '|', 'debconf-set-selections'], context)
            execute.execute(ssh, ['echo "slapd slapd/domain string ' + vals['container_options']['domain']['value'] + '"', '|', 'debconf-set-selections'], context)
            execute.execute(ssh, ['dpkg-reconfigure', '-f', 'noninteractive', 'slapd'], context)

            config_file = '/etc/ldap/schema/' + vals['container_options']['domain']['value'] + '.ldif'
            sftp.put(vals['config_conductor_path'] + '/saas_ldap/res/ldap.ldif', config_file)
            domain_dc = ''
            for dc in vals['container_options']['domain']['value'].split('.'):
                if domain_dc:
                    domain_dc += ','
                domain_dc += 'dc=' + dc

            execute.execute(ssh, ['sed', '-i', '"s/\$DOMAIN/' + domain_dc + '/g"', config_file], context)
            execute.execute(ssh, ['sed', '-i', '"s/\$PASSWORD/' + vals['container_options']['password']['value'] + '/g"', config_file], context)
            execute.execute(ssh, ['sed', '-i', '"s/\$ORGANIZATION/' + vals['container_options']['organization']['value'] + '/g"', config_file], context)
            execute.execute(ssh, ['sed', '-i', '"s/dc=example,dc=com/' + domain_dc + '/g"', '/etc/phpldapadmin/config.php'], context)
            ssh.close()
            sftp.close()
            self.start(cr, uid, vals, context=context)
            ssh, sftp = execute.connect(vals['container_fullname'], context=context)
            execute.execute(ssh, ['ldapadd', '-Y', 'EXTERNAL', '-H', 'ldapi:///', '-f', config_file], context)
            ssh.close()
            sftp.close()