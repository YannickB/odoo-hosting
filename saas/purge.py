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

class saas_container(osv.osv):
    _inherit = 'saas.container'

    def purge(self, cr, uid, id, vals, context={}):
        context.update({'saas-self': self, 'saas-cr': cr, 'saas-uid': uid})
        container = self.browse(cr, uid, id, context=context)
        ssh, sftp = execute.connect(vals['server_domain'], vals['server_ssh_port'], 'root', context)
        execute.execute(ssh, ['sudo','docker', 'stop', container.name], context)
        execute.execute(ssh, ['sudo','docker', 'rm', container.name], context)
        ssh.close()
        sftp.close()
        return

#sudo docker run -d -P --name test img_postgres
# class saas_service(osv.osv):
    # _inherit = 'saas.service'

    # def deploy_post_instance(self, cr, uid, vals, context=None):
        # return


    # def deploy(self, cr, uid, vals, context=None):

        # ssh, sftp = connect(vals['service_server_name'], vals['apptype_system_user'], context=context)

        # if sftp.stat(vals['service_fullpath']):
            # _logger.error('Service already exist')
            # return

        # execute(ssh, 'mkdir ' + vals['service_fullpath'], context=context)

        # sftp.put(vals['app_archive_path']/vals['app_name']/vals['archive']/archive.tar.gz, vals['service_fullpath']/)

        # execute(ssh, 'cd ' + vals['service_fullpath'] + '; tar -xf archive.tar.gz -c ' + vals['service_fullpath'] + '/', context=context)
        # execute(ssh, 'rm + ' + vals['service_fullpath'] + '/archive.tar.gz', context=context)
        # ssh.close()

        # log('Creating database user', context=context)

        # _logger.info('db_type %s', vals['service_bdd'])
        #SI postgres, create user
        # if vals['service_bdd'] != 'mysql':
            # ssh = connect(vals['bdd_server_domain'], 'postgres', context=context)
            # execute(ssh, 'psql; CREATE USER ' + vals['service_db_user'] + ' WITH PASSWORD ' + vals['service_db_password'] + ' CREATEDB;\q', context=context)
            # ssh.close()

            # ssh = connect(vals['service_server_name'], vals['apptype_system_user'], context=context)
            # execute(ssh, 'sed -i "/:*:' + vals['service_db_user'] + ':/d" ~/.pgpass', context=context)
            # execute(ssh, 'echo "' + vals['bdd_server_domain'] + ':5432:*:' + vals['service_db_user'] + ':' +  + vals['service_db_passwd'] + '" >> ~/.pgpass', context=context)
            # execute(ssh, 'chmod 700 ~/.pgpass', context=context)
            # ssh.close()

        # else:
            # ssh = connect(vals['bdd_server_domain'], vals['apptype_system_user'], context=context)
            # execute(ssh, "mysql -u root -p'" + vals['bdd_server_mysql_password'] + "' -se 'create user '" + vals['service_db_user'] + "' identified by '" + vals['service_db_passwd'] + ";'", context=context)
            # ssh.close()

        # log('Database user created', context=context)

        # self.deploy_post_instance(cr, uid, vals, context=context)

        # ssh, sftp = connect(vals['service_server_name'], vals['apptype_system_user'], context=context)
        # if sftp.stat(vals['service_fullpath']):
            # log('Service ok', context=context)
        # else:
            # log('There was an error while creating the instance', context=context)
            # context['log_state'] == 'ko'
            # ko_log(context=context)
        # ssh.close()

