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
import paramiko
import execute

import logging
_logger = logging.getLogger(__name__)

class saas_domain(osv.osv):
    _inherit = 'saas.domain'

    def purge(self, cr, uid, vals, context={}):
        context.update({'saas-self': self, 'saas-cr': cr, 'saas-uid': uid})
        ssh, sftp = execute.connect(vals['dns_server_domain'], vals['dns_ssh_port'], 'root', context)
        execute.execute(ssh, ['rm', vals['domain_configfile']], context)
        execute.execute(ssh, ['/etc/init.d/bind9', 'reload'], context)
        ssh.close()
        sftp.close()

class saas_server(osv.osv):
    _inherit = 'saas.server'

    def purge(self, cr, uid, vals, context={}):
        context.update({'saas-self': self, 'saas-cr': cr, 'saas-uid': uid})
        if 'shinken_server_domain' in vals:
            ssh, sftp = execute.connect(vals['shinken_server_domain'], vals['shinken_ssh_port'], 'root', context)
            execute.execute(ssh, ['rm', vals['server_shinken_configfile']], context)
            execute.execute(ssh, ['/etc/init.d/shinken', 'reload'], context)
            ssh.close()
            sftp.close()

class saas_container(osv.osv):
    _inherit = 'saas.container'

    def purge(self, cr, uid, vals, context={}):
        context.update({'saas-self': self, 'saas-cr': cr, 'saas-uid': uid})
#        container = self.browse(cr, uid, id, context=context)
        ssh, sftp = execute.connect(vals['server_domain'], vals['server_ssh_port'], 'root', context)
        execute.execute(ssh, ['sudo','docker', 'stop', vals['container_name']], context)
        execute.execute(ssh, ['sudo','docker', 'rm', vals['container_name']], context)
        ssh.close()
        sftp.close()
        return


class saas_service(osv.osv):
    _inherit = 'saas.service'


    def purge_pre_service(self, cr, uid, vals, context=None):
        return

    def purge(self, cr, uid, id, vals, context={}):
        context.update({'saas-self': self, 'saas-cr': cr, 'saas-uid': uid})

        self.purge_pre_service(cr, uid, vals, context)

        if vals['app_bdd'] != 'mysql':
            ssh, sftp = execute.connect(vals['database_server_domain'], vals['database_ssh_port'], 'postgres', context)
            execute.execute(ssh, ['psql', '-c', '"DROP USER ' + vals['service_db_user'] + ';"'], context)
            ssh.close()
            sftp.close()

            ssh, sftp = execute.connect(vals['server_domain'], vals['container_ssh_port'], vals['apptype_system_user'], context)
            execute.execute(ssh, ['sed', '-i', '"/:*:' + vals['service_db_user'] + ':/d" ~/.pgpass'], context)
            ssh.close()
            sftp.close()

        else:
            ssh, sftp = execute.connect(vals['bdd_server_domain'], vals['bdd_server_ssh_port'], vals['apptype_system_user'], context)
            execute.execute(ssh, ["mysql -u root -p'" + vals['bdd_server_mysql_password'] + "' -se 'drop user '" + vals['service_db_user'] + ";'"], context)
            ssh.close()
            sftp.close()

        service_ids = self.search(cr, uid, [('application_version_id', '=', vals['app_version_id']),('container_id.server_id','=',vals['server_id'])], context=context)
        service_ids.remove(vals['service_id'])
        if not service_ids:
            ssh, sftp = execute.connect(vals['server_domain'], vals['server_ssh_port'], 'root', context)
            execute.execute(ssh, ['rm', '-rf', vals['app_version_full_hostpath']], context)
            ssh.close()
            sftp.close()

        return



class saas_base(osv.osv):
    _inherit = 'saas.base'


    def purge_post(self, cr, uid, vals, context=None):
        return

    def purge(self, cr, uid, vals, context={}):
        context.update({'saas-self': self, 'saas-cr': cr, 'saas-uid': uid})

        ssh, sftp = execute.connect(vals['shinken_server_domain'], vals['shinken_ssh_port'], 'root', context)
        execute.execute(ssh, ['rm', vals['base_shinken_configfile']], context)
        execute.execute(ssh, ['/etc/init.d/shinken', 'reload'], context)
        ssh.close()
        sftp.close()


        ssh, sftp = execute.connect(vals['dns_server_domain'], vals['dns_ssh_port'], 'root', context)
        execute.execute(ssh, ['sed', '-i', '"/' + vals['base_name'] + '\sIN\sCNAME/d"', vals['domain_configfile']], context)
        execute.execute(ssh, ['/etc/init.d/bind9', 'reload'], context)
        ssh.close()
        sftp.close()

        ssh, sftp = execute.connect(vals['proxy_server_domain'], vals['proxy_ssh_port'], 'root', context)
        execute.execute(ssh, ['a2dissite', vals['base_unique_name']], context)
        execute.execute(ssh, ['rm', vals['base_apache_configfile']], context)
        execute.execute(ssh, ['/etc/init.d/apache2', 'reload'], context)
        ssh.close()
        sftp.close()

        if vals['app_bdd'] != 'mysql':
            ssh, sftp = execute.connect(vals['database_server_domain'], vals['database_ssh_port'], 'postgres', context)
            execute.execute(ssh, ['psql', '-c', '"update pg_database set datallowconn = \'false\' where datname = \'' + vals['base_unique_name_'] + '\'; SELECT pg_terminate_backend(procpid) FROM pg_stat_activity WHERE datname = \'' + vals['base_unique_name_'] + '\';"'], context)
            execute.execute(ssh, ['dropdb', vals['base_unique_name_']], context)

            ssh.close()
            sftp.close()

        else:
            ssh, sftp = execute.connect(vals['bdd_server_domain'], vals['bdd_server_ssh_port'], vals['apptype_system_user'], context)
            execute.execute(ssh, ["mysql -u root -p'" + vals['bdd_server_mysql_password'] + "' -se 'drop database '" + vals['base_unique_name_'] + ";'"], context)
            ssh.close()
            sftp.close()

        self.purge_post(cr, uid, vals, context)

# if [[ $saas != 'demo' ]]
# then

####TODO This part is not crossplatform because recover the variable will be difficult. When we will move piwik, consider open the post mysql to www server ip so we can continue query it directly.
####ssh $piwik_server << EOF
# piwik_id=$(mysql piwik -u piwik -p$piwik_password -se "select idsite from piwik_site WHERE name = '$saas.$domain' LIMIT 1")
####EOF
# echo piwik_id $piwik_id
# fi

# if [[ $piwik_id != '' ]]
# then
# ssh $piwik_server << EOF
  # mysql piwik -u piwik -p$piwik_password -se "UPDATE piwik_site SET name = 'droped_$piwik_id'  WHERE idsite = $piwik_id;"
  # mysql piwik -u piwik -p$piwik_password -se "DELETE FROM piwik_access WHERE idsite = $piwik_id;"
# EOF
# fi

#}


