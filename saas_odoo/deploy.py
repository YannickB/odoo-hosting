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

import logging
_logger = logging.getLogger(__name__)


class saas_container(osv.osv):
    _inherit = 'saas.container'
    def add_links(self, cr, uid, vals, context={}):
        res = super(saas_container, self).add_links(cr, uid, vals, context=context)
        if 'application_id' in vals and 'server_id' in vals:
            application = self.pool.get('saas.application').browse(cr, uid, vals['application_id'], context=context)
            if application.type_id.name == 'odoo':
                if not 'linked_container_ids' in vals:
                    vals['linked_container_ids'] = []
                container_ids = self.search(cr, uid, [('application_id.type_id.name','=','postgres'),('server_id','=',vals['server_id'])], context=context)
                for container in self.browse(cr, uid, container_ids, context=context):
                    vals['linked_container_ids'].append((4,container.id))
        return vals

class saas_service(osv.osv):
    _inherit = 'saas.service'

    def deploy_post_service(self, cr, uid, vals, context):
        super(saas_service, self).deploy_post_service(cr, uid, vals, context)
        context.update({'saas-self': self, 'saas-cr': cr, 'saas-uid': uid})
        if vals['apptype_name'] == 'odoo':
            ssh, sftp = execute.connect(vals['server_domain'], vals['container_ssh_port'], vals['apptype_system_user'], context)
            execute.execute(ssh, ['ln', '-s', vals['app_version_full_localpath'], '/opt/odoo/services/' + vals['service_name']], context)
            execute.execute(ssh, ['mkdir', '/opt/odoo/extra/' + vals['service_name']], context)

            config_file = '/opt/odoo/etc/' + vals['service_name'] + '.config'
            sftp.put(vals['config_conductor_path'] + '/saas/saas_odoo/res/openerp.config', config_file)
            addons_path = '/opt/odoo/services/' + vals['service_name'] + '/parts/odoo/addons,/opt/odoo/extra/' + vals['service_name'] + ','
            for dir in  sftp.listdir('/opt/odoo/services/' + vals['service_name'] + '/extra'):
                addons_path += '/opt/odoo/services/' + vals['service_name'] + '/extra/' + dir + ','
            execute.execute(ssh, ['sed', '-i', '"s/ADDONS_PATH/' + addons_path.replace('/','\/') + '/g"', config_file], context)
            execute.execute(ssh, ['sed', '-i', 's/SERVICE/' + vals['service_name'] + '/g', config_file], context)
            execute.execute(ssh, ['sed', '-i', 's/DATABASE_SERVER/' + vals['database_server'] + '/g', config_file], context)
            execute.execute(ssh, ['sed', '-i', 's/DBUSER/' + vals['service_db_user'] + '/g', config_file], context)
            execute.execute(ssh, ['sed', '-i', 's/DATABASE_PASSWORD/' + vals['service_db_password'] + '/g', config_file], context)
            execute.execute(ssh, ['sed', '-i', 's/PORT/' + vals['service_options']['port']['value'] + '/g', config_file], context)

            execute.execute(ssh, ['echo "[program:' + vals['service_name'] + ']" >> /opt/odoo/supervisor.conf'], context)
            execute.execute(ssh, ['echo "command=su odoo -c \'/opt/odoo/services/' + vals['service_name'] + '/parts/odoo/odoo.py -c ' + config_file  + '\'" >> /opt/odoo/supervisor.conf'], context)
#            execute.execute(ssh, ['echo "command=su odoo -c \'/opt/odoo/services/'  + vals['service_name'] + '/sandbox/bin/python /opt/odoo/services/' + vals['service_name'] + '/bin/start_odoo -c ' + config_file  + '\'" >> /opt/odoo/supervisor.conf'], context)

            ssh.close()
            sftp.close()

        return


class saas_base(osv.osv):
    _inherit = 'saas.base'

    def deploy_create_database(self, cr, uid, vals, context=None):
        res = super(saas_base, self).deploy_create_database(cr, uid, vals, context)
        context.update({'saas-self': self, 'saas-cr': cr, 'saas-uid': uid})
        if vals['apptype_name'] == 'odoo':
            ssh, sftp = execute.connect(vals['server_domain'], vals['container_ssh_port'], vals['apptype_system_user'], context)
            execute.execute(ssh, ['mkdir', '-p', '/opt/filestore/' + vals['base_unique_base_']], context)
            if vals['base_build'] == 'build':
                cmd = ['/usr/local/bin/erppeek', '--server', 'http://' + vals['server_domain'] + ':' + vals['service_port'], ';']
                cmd.extend(["client.create_database('" + vals['service_db_password'] + "', '" + vals['base_unique_name_'] + "', demo=" + vals['base_test'] + ", lang='fr_FR', user_password='" + vals['base_admin_passwd'] + "')"])
                cmd.extend(['exit'])
                execute.execute(ssh, cmd, context)
                return True
        return res

    def deploy_build(self, cr, uid, vals, context=None):
        res = super(saas_base, self).deploy_build(cr, uid, vals, context)
        context.update({'saas-self': self, 'saas-cr': cr, 'saas-uid': uid})
        if vals['apptype_name'] == 'odoo':
            ssh, sftp = execute.connect(vals['server_domain'], vals['container_ssh_port'], vals['apptype_system_user'], context)
            cmd_connect = ['/usr/local/bin/erppeek', '--server', 'http://' + vals['server_domain'] + ':' + vals['service_port'], '-u', vals['apptype_admin_name'], '-p', vals['base_admin_passwd'], '-d', vals['base_unique_name_'], ';']
            cmd = cmd_connect
            cmd.extend(["client.install('account_accountant', 'account_chart_install', 'l10n_fr')"])
            cmd.extend(["client.execute('account.chart.template', 'install_chart', 'l10n_fr', 'l10n_fr_pcg_chart_template', 1, 1)"])
            cmd.extend(["client.install('community')"])
            cmd.extend(['exit'])
            execute.execute(ssh, cmd, context)

            cmd = cmd_connect
            cmd.extend(["extended_group_id = client.search('res.groups', [('name','=','Technical Features')])[0]"])
            cmd.extend(["model('res.groups').write([extended_group_id], {'users': [(4, 1)]})"])
            cmd.extend(['exit'])
            extended_group_id = execute.execute(ssh, cmd, context)

        return

    def deploy_test(self, cr, uid, vals, context=None):
        res = super(saas_base, self).deploy_test(cr, uid, vals, context)
        context.update({'saas-self': self, 'saas-cr': cr, 'saas-uid': uid})
        if vals['apptype_name'] == 'odoo':
            ssh, sftp = execute.connect(vals['server_domain'], vals['container_ssh_port'], vals['apptype_system_user'], context)
            cmd_connect = ['/usr/local/bin/erppeek', '--server', 'http://' + vals['server_domain'] + ':' + vals['service_port'], '-u', vals['apptype_admin_name'], '-p', vals['base_admin_passwd'], '-d', vals['base_unique_name_'], ';']
            cmd.extend(["client.install('community_blog', 'community_crm', 'community_event', 'community_forum', 'community_marketplace', 'community_project')"])
            cmd.extend(['exit'])
            execute.execute(ssh, cmd, context)

        return
