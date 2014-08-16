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


class saas_service(osv.osv):
    _name = 'saas.service'
    _inherit = ['saas.model']

    _columns = {
        'name': fields.char('Name', size=64, required=True),
        'application_id': fields.related('container_id', 'application_id', type='many2one', relation='saas.application', string='Application', readonly=True),
        'application_version_id': fields.many2one('saas.application.version', 'Version', domain="[('application_id.container_ids','in',container_id)]", required=True),
        'database_container_id': fields.many2one('saas.container', 'Database container', required=True),
        'database_password': fields.char('Database password', size=64, required=True),
        'container_id': fields.many2one('saas.container', 'Container', required=True),
        'prod': fields.boolean('Prod?', readonly=True),
        'skip_analytics': fields.boolean('Skip Analytics?'),
        'option_ids': fields.one2many('saas.service.option', 'service_id', 'Options'),
        'base_ids': fields.one2many('saas.base', 'service_id', 'Bases'),
    }

    _defaults = {
      'prod': True,
      'database_password': '#g00gle!'
    }

    _sql_constraints = [
        ('name_uniq', 'unique(container_id,name)', 'Name must be unique per container!'),
    ]

    def _check_application(self, cr, uid, ids, context=None):
        for s in self.browse(cr, uid, ids, context=context):
            if s.application_id.id != s.container_id.application_id.id:
                return False
        return True


    def _check_application_version(self, cr, uid, ids, context=None):
        for s in self.browse(cr, uid, ids, context=context):
            if s.application_id.id != s.application_version_id.application_id.id:
                return False
        return True

    _constraints = [
        (_check_application, "The application of service must be the same than the application of container." , ['container_id']),
        (_check_application_version, "The application of application version must be the same than the application of service." , ['application_id','application_version_id']),
    ]



    def get_vals(self, cr, uid, id, context=None):

        vals = {}

        service = self.browse(cr, uid, id, context=context)

        vals.update(self.pool.get('saas.application.version').get_vals(cr, uid, service.application_version_id.id, context=context))

        vals.update(self.pool.get('saas.container').get_vals(cr, uid, service.container_id.id, context=context))


        database_vals = self.pool.get('saas.container').get_vals(cr, uid, service.database_container_id.id, context=context)
        vals.update({
            'database_id': database_vals['container_id'],
            'database_fullname': database_vals['container_fullname'],
            'database_ssh_port': database_vals['container_ssh_port'],
            'database_server_id': database_vals['server_id'],
            'database_server_domain': database_vals['server_domain'],
        })

        options = {}
        for option in service.container_id.application_id.type_id.option_ids:
            if option.type == 'service':
                options[option.name] = {'id': option.id, 'name': option.name, 'value': option.default}
        for option in service.option_ids:
            options[option.name.name] = {'id': option.id, 'name': option.name.name, 'value': option.value}

        database_server = vals['database_server_domain']
        if vals['server_id'] == vals['database_server_id'] and vals['database_id'] in vals['container_links']:
            database_server = vals['container_links'][vals['database_id']]['name']

        service_fullname = vals['container_name'] + '-' + service.name
        vals.update({
            'service_id': service.id,
            'service_name': service.name,
            'service_fullname': service_fullname,
            'service_db_user': service_fullname.replace('-','_'),
            'service_db_password': service.database_password,
            'service_skip_analytics': service.skip_analytics,
            'service_full_localpath': vals['app_full_localpath'] + '/' + service.name,
            'service_options': options,
            'database_server': database_server
        })

        return vals


    def deploy_post_service(self, cr, uid, vals, context=None):
        return


    def deploy(self, cr, uid, vals, context=None):
        context.update({'saas-self': self, 'saas-cr': cr, 'saas-uid': uid})
        self.purge(cr, uid, vals, context=context)
        ssh, sftp = execute.connect(vals['server_domain'], vals['server_ssh_port'], 'root', context)

        if not execute.exist(sftp, vals['app_version_full_hostpath']):
            execute.execute(ssh, ['mkdir', '-p', vals['app_version_full_hostpath']], context)
            sftp.put(vals['app_version_full_archivepath_targz'], vals['app_version_full_hostpath'] + '.tar.gz')
            execute.execute(ssh, ['tar', '-xf', vals['app_version_full_hostpath'] + '.tar.gz', '-C', vals['app_version_full_hostpath']], context)
            execute.execute(ssh, ['rm', vals['app_full_hostpath'] + '/' + vals['app_version_name'] + '.tar.gz'], context)

        ssh.close()
        sftp.close()

        execute.log('Creating database user', context=context)

        #SI postgres, create user
        if vals['app_bdd'] != 'mysql':
            ssh, sftp = execute.connect(vals['database_fullname'], username='postgres', context=context)
            execute.execute(ssh, ['psql', '-c', '"CREATE USER ' + vals['service_db_user'] + ' WITH PASSWORD \'' + vals['service_db_password'] + '\' CREATEDB;"'], context)
            ssh.close()
            sftp.close()

            ssh, sftp = execute.connect(vals['container_fullname'], username=vals['apptype_system_user'], context=context)
            execute.execute(ssh, ['sed', '-i', '"/:*:' + vals['service_db_user'] + ':/d" ~/.pgpass'], context)
            execute.execute(ssh, ['echo "' + vals['database_server'] + ':5432:*:' + vals['service_db_user'] + ':' + vals['service_db_password'] + '" >> ~/.pgpass'], context)
            execute.execute(ssh, ['chmod', '700', '~/.pgpass'], context)
            ssh.close()
            sftp.close()

        else:
            ssh, sftp = execute.connect(vals['bdd_server_domain'], vals['bdd_server_ssh_port'], vals['apptype_system_user'], context)
            execute.execute(ssh, ["mysql -u root -p'" + vals['bdd_server_mysql_password'] + "' -se 'create user '" + vals['service_db_user'] + "' identified by '" + vals['service_db_password'] + ";'"], context)
            ssh.close()
            sftp.close()

        execute.log('Database user created', context)

        self.deploy_post_service(cr, uid, vals, context)

        ssh, sftp = execute.connect(vals['server_domain'], vals['server_ssh_port'], 'root', context)
        execute.execute(ssh, ['sudo', 'docker', 'restart', vals['container_name']], context)
        ssh.close()
        sftp.close()

        # ssh, sftp = connect(vals['server_domain'], vals['apptype_system_user'], context=context)
        # if sftp.stat(vals['service_fullpath']):
            # log('Service ok', context=context)
        # else:
            # log('There was an error while creating the instance', context=context)
            # context['log_state'] == 'ko'
            # ko_log(context=context)
        # ssh.close()


    def purge_pre_service(self, cr, uid, vals, context=None):
        return

    def purge(self, cr, uid, vals, context={}):
        context.update({'saas-self': self, 'saas-cr': cr, 'saas-uid': uid})

        self.purge_pre_service(cr, uid, vals, context)

        if vals['app_bdd'] != 'mysql':
            ssh, sftp = execute.connect(vals['database_fullname'], username='postgres', context=context)
            execute.execute(ssh, ['psql', '-c', '"DROP USER ' + vals['service_db_user'] + ';"'], context)
            ssh.close()
            sftp.close()

            ssh, sftp = execute.connect(vals['container_fullname'], username=vals['apptype_system_user'], context=context)
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


class saas_service_option(osv.osv):
    _name = 'saas.service.option'

    _columns = {
        'service_id': fields.many2one('saas.service', 'Service', ondelete="cascade", required=True),
        'name': fields.many2one('saas.application.type.option', 'Option', required=True),
        'value': fields.text('Value'),
    }

    _sql_constraints = [
        ('name_uniq', 'unique(server_id,name)', 'Option name must be unique per service!'),
    ]
