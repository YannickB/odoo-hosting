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

import openerp.addons.saas.execute as execute

import logging
_logger = logging.getLogger(__name__)


class saas_base_link(osv.osv):
    _inherit = 'saas.base.link'

    def deploy_link(self, cr, uid, vals, context={}):
        super(saas_base_link, self).deploy_link(cr, uid, vals, context=context)
        if vals['link_target_app_code'] == 'proxy':
            if not vals['base_sslonly']:
                file = 'proxy.config'
            else:
                file = 'proxy-sslonly.config'
            ssh, sftp = execute.connect(vals['link_target_container_fullname'], context=context)
            execute.send(sftp, vals['config_conductor_path'] + '/saas/saas_' + vals['apptype_name'] + '/res/' + file, vals['base_nginx_configfile'], context)
            execute.execute(ssh, ['sed', '-i', '"s/BASE/' + vals['base_name'] + '/g"', vals['base_nginx_configfile']], context)
            execute.execute(ssh, ['sed', '-i', '"s/DOMAIN/' + vals['domain_name'] + '/g"', vals['base_nginx_configfile']], context)
            execute.execute(ssh, ['sed', '-i', '"s/SERVER/' + vals['server_domain'] + '/g"', vals['base_nginx_configfile']], context)
            if 'port' in vals['service_options']:
                execute.execute(ssh, ['sed', '-i', '"s/PORT/' + vals['service_options']['port']['hostport'] + '/g"', vals['base_nginx_configfile']], context)
            # self.deploy_prepare_apache(cr, uid, vals, context)
            cert_file = '/etc/ssl/certs/' + vals['base_name'] + '.' + vals['domain_name'] + '.crt'
            key_file = '/etc/ssl/private/' + vals['base_name'] + '.' + vals['domain_name'] + '.key'
            if vals['base_certcert'] and vals['base_certkey']:
                execute.execute(ssh, ['echo', '"' + vals['base_certcert'] + '"', '>', cert_file], context)
                execute.execute(ssh, ['echo', '"' + vals['base_certkey'] + '"', '>', key_file], context)
            elif vals['domain_certcert'] and vals['domain_certkey']:
                execute.execute(ssh, ['echo', '"' + vals['domain_certcert'] + '"', '>', cert_file], context)
                execute.execute(ssh, ['echo', '"' + vals['domain_certkey'] + '"', '>', key_file], context)
            else:
                execute.execute(ssh, ['openssl', 'req', '-x509', '-nodes', '-days', '365', '-newkey', 'rsa:2048', '-out', cert_file, ' -keyout',  key_file, '-subj', '"/C=FR/L=Paris/O=' + vals['domain_organisation'] + '/CN=' + vals['base_name'] + '.' + vals['domain_name'] + '"'], context)
            execute.execute(ssh, ['ln', '-s', vals['base_nginx_configfile'], '/etc/nginx/sites-enabled/' + vals['base_unique_name']], context)
            execute.execute(ssh, ['/etc/init.d/nginx', 'reload'], context)
            ssh.close()
            sftp.close()

    def purge_link(self, cr, uid, vals, context={}):
        super(saas_base_link, self).purge_link(cr, uid, vals, context=context)
        if vals['link_target_app_code'] == 'proxy':
            ssh, sftp = execute.connect(vals['link_target_container_fullname'], context=context)
            execute.execute(ssh, ['rm', '/etc/nginx/sites-enabled/' + vals['base_unique_name']], context)
            execute.execute(ssh, ['rm', vals['base_nginx_configfile']], context)
            execute.execute(ssh, ['rm', '/etc/ssl/certs/' + vals['base_name'] + '.' + vals['domain_name'] + '.*'], context)
            execute.execute(ssh, ['rm', '/etc/ssl/private/' + vals['base_name'] + '.' + vals['domain_name'] + '.*'], context)
            execute.execute(ssh, ['/etc/init.d/nginx', 'reload'], context)
            ssh.close()
            sftp.close()