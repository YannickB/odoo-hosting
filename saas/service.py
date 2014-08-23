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


    def name_get(self,cr,uid,ids,context=None):
        res=[]
        for service in self.browse(cr, uid, ids, context=context):
            res.append((service.id,service.name + ' [' + service.container_id.name + '_' + service.container_id.server_id.name +  ']'))
        return res

    def name_search(self, cr, user, name='', args=None, operator='ilike', context=None, limit=100):
        if not args:
            args = []
        # container_obj = self.pool.get('saas.container')
        if name:
            #
            # container_ids = container_obj.search(cr, user, ['|',('name','=',name),('domain_id.name','=',name)]+ args, limit=limit, context=context)
            # if container_ids:
            #     containers = self.browse(cr, user, container_ids, context=context)
            #     ids = [s.id for s in containers.service_ids]
            # else
            ids = self.search(cr, user, ['|',('name','like',name),'|',('container_id.name','like',name),('container_id.server_id.name','like',name)]+ args, limit=limit, context=context)
        else:
            ids = self.search(cr, user, args, limit=limit, context=context)
        result = self.name_get(cr, user, ids, context=context)
        return result


    _columns = {
        'name': fields.char('Name', size=64, required=True),
        'application_id': fields.related('container_id', 'application_id', type='many2one', relation='saas.application', string='Application', readonly=True),
        'application_version_id': fields.many2one('saas.application.version', 'Version', domain="[('application_id.container_ids','in',container_id)]", required=True),
        'database_container_id': fields.many2one('saas.container', 'Database container', required=True),
        'database_password': fields.char('Database password', size=64, required=True),
        'container_id': fields.many2one('saas.container', 'Container', required=True),
        'skip_analytics': fields.boolean('Skip Analytics?'),
        'option_ids': fields.one2many('saas.service.option', 'service_id', 'Options'),
        'base_ids': fields.one2many('saas.base', 'service_id', 'Bases'),
        'parent_id': fields.many2one('saas.service', 'Parent Service'),
        'sub_service_name': fields.char('Subservice Name', size=64),
        'custom_version': fields.boolean('Custom Version?'),
    }

    _defaults = {
      'database_password': execute.generate_random_password(20),
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
            'service_full_localpath': vals['apptype_localpath_services'] + '/' + service.name,
            'service_options': options,
            'database_server': database_server,
            'service_subservice_name': service.sub_service_name,
            'service_custom_version': service.custom_version
        })

        return vals


    def write(self, cr, uid, ids, vals, context={}):
        if 'application_version_id' in vals:
            services_old = []
            for service in self.browse(cr, uid, ids, context=context):
                services_old.append(self.get_vals(cr, uid, service.id, context=context))
        res = super(saas_service, self).write(cr, uid, ids, vals, context=context)
        if 'application_version_id' in vals:
            for service_vals in services_old:
                self.check_files(cr, uid, service_vals, context=context)
        _logger.info('vals %s', vals)
        if 'application_version_id' in vals or 'custom_version' in vals:
            for service in self.browse(cr, uid, ids, context=context):
                _logger.info('deploy files')
                vals = self.get_vals(cr, uid, service.id, context=context)
                self.deploy_files(cr, uid, vals, context=context)
        return res


    def unlink(self, cr, uid, ids, context={}):
        base_obj = self.pool.get('saas.base')
        for service in self.browse(cr, uid, ids, context=context):
            base_obj.unlink(cr, uid, [b.id for b in service.base_ids], context=context)
        return super(saas_service, self).unlink(cr, uid, ids, context=context)

    def install_formation(self, cr, uid, ids, context={}):
        self.write(cr, uid, ids, {'sub_service_name': 'formation'}, context=context)
        self.install_subservice(cr, uid, ids, context=context)

    def install_test(self, cr, uid, ids, context={}):
        self.write(cr, uid, ids, {'sub_service_name': 'test'}, context=context)
        self.install_subservice(cr, uid, ids, context=context)

    def install_subservice(self, cr, uid, ids, context={}):
        base_obj = self.pool.get('saas.base')
        for service in self.browse(cr, uid, ids, context=context):
            if not service.sub_service_name or service.sub_service_name == service.name:
                continue
            service_ids = self.search(cr, uid, [('name','=',service.sub_service_name),('container_id','=',service.container_id.id)],context=context)
            self.unlink(cr, uid, service_ids,context=context)
            options = []
            type_ids = self.pool.get('saas.application.type.option').search(cr, uid, [('apptype_id','=',service.container_id.application_id.type_id.id),('name','=','port')], context=context)
            if type_ids:
                if service.sub_service_name == 'formation':
                    options =[(0,0,{'name': type_ids[0], 'value': 'port-formation'})]
                if service.sub_service_name == 'test':
                    options = [(0,0,{'name': type_ids[0], 'value': 'port-test'})]
            service_vals = {
                'name': service.sub_service_name,
                'container_id': service.container_id.id,
                'database_container_id': service.database_container_id.id,
                'application_version_id': service.application_version_id.id,
                'parent_id': service.id,
                'option_ids': options
            }
            service_id = self.create(cr, uid, service_vals, context=context)
            for base in service.base_ids:
                base_obj._reset_base(cr, uid, [base.id], base_name=service.sub_service_name + '-' + base.name, service_id=service_id)
        self.write(cr, uid, ids, {'sub_service_name': False}, context=context)


    def deploy_to_parent(self, cr, uid, ids, context={}):
        for service in  self.browse(cr, uid, ids, context=context):
            if not service.parent_id:
                continue
            vals = {}
            if not service.parent_id.custom_version:
                vals['application_version_id'] = service.application_version_id.id
            else:
                context['files_from_service'] = service.name
                vals['custom_version'] = True
            _logger.info('vals %s', vals)
            self.write(cr, uid, [service.parent_id.id], vals, context=context)

    def deploy_post_service(self, cr, uid, vals, context=None):
        return


    def deploy(self, cr, uid, vals, context=None):
        container_obj = self.pool.get('saas.container')
        context.update({'saas-self': self, 'saas-cr': cr, 'saas-uid': uid})
        self.purge(cr, uid, vals, context=context)

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

        self.deploy_files(cr, uid, vals, context=context)
        self.deploy_post_service(cr, uid, vals, context)

        container_obj.restart(cr, uid, vals, context=context)

        time.sleep(3)

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
        self.purge_files(cr, uid, vals, context=context)
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

        return


    def check_files(self, cr, uid, vals, context={}):
        context.update({'saas-self': self, 'saas-cr': cr, 'saas-uid': uid})
        service_ids = self.search(cr, uid, [('application_version_id', '=', vals['app_version_id']),('container_id.server_id','=',vals['server_id'])], context=context)
        service_ids.remove(vals['service_id'])
        if not service_ids:
            ssh, sftp = execute.connect(vals['server_domain'], vals['server_ssh_port'], 'root', context)
            execute.execute(ssh, ['rm', '-rf', vals['app_version_full_hostpath']], context)
            ssh.close()
            sftp.close()


    def deploy_files(self, cr, uid, vals, context={}):
        context.update({'saas-self': self, 'saas-cr': cr, 'saas-uid': uid})
        base_obj = self.pool.get('saas.base')
        self.purge_files(cr, uid, vals, context=context)
        ssh, sftp = execute.connect(vals['server_domain'], vals['server_ssh_port'], 'root', context)

        if not execute.exist(sftp, vals['app_version_full_hostpath']):
            execute.execute(ssh, ['mkdir', '-p', vals['app_version_full_hostpath']], context)
            sftp.put(vals['app_version_full_archivepath_targz'], vals['app_version_full_hostpath'] + '.tar.gz')
            execute.execute(ssh, ['tar', '-xf', vals['app_version_full_hostpath'] + '.tar.gz', '-C', vals['app_version_full_hostpath']], context)
            execute.execute(ssh, ['rm', vals['app_full_hostpath'] + '/' + vals['app_version_name'] + '.tar.gz'], context)

        ssh.close()
        sftp.close()

        ssh, sftp = execute.connect(vals['container_fullname'], username=vals['apptype_system_user'], context=context)
        if 'files_from_service' in context:
            execute.execute(ssh, ['cp', '-R', vals['apptype_localpath_services'] + '/' + context['files_from_service'], vals['service_full_localpath']], context)
        elif vals['service_custom_version']:
            execute.execute(ssh, ['cp', '-R', vals['app_version_full_localpath'], vals['service_full_localpath']], context)
        else:
            execute.execute(ssh, ['ln', '-s', vals['app_version_full_localpath'], vals['service_full_localpath']], context)
        service = self.browse(cr, uid, vals['service_id'], context=context)
        for base in service.base_ids:
            base_obj.save(cr, uid, [base.id], context=context)
            base_vals = base_obj.get_vals(cr, uid, base.id, context=context)
            base_obj.update_base(cr, uid, base_vals, context=context)

        ssh.close()
        sftp.close()

    def purge_files(self, cr, uid, vals, context={}):
        context.update({'saas-self': self, 'saas-cr': cr, 'saas-uid': uid})
        ssh, sftp = execute.connect(vals['container_fullname'], username=vals['apptype_system_user'], context=context)
        execute.execute(ssh, ['rm', '-rf', vals['service_full_localpath']], context)
        ssh.close()
        sftp.close()

        self.check_files(cr, uid, vals, context=context)


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
