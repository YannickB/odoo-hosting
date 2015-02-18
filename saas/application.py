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


class saas_application_type(osv.osv):
    _name = 'saas.application.type'

    _columns = {
        'name': fields.char('Name', size=64, required=True),
        'system_user': fields.char('System User', size=64, required=True),
        'localpath': fields.char('Localpath', size=128),
        'localpath_services': fields.char('Localpath Services', size=128),
        'option_ids': fields.one2many('saas.application.type.option', 'apptype_id', 'Options'),
        'application_ids': fields.one2many('saas.application', 'type_id', 'Applications'),
        'symlink': fields.boolean('Use Symlink by default?'),
        'multiple_databases': fields.char('Multiples databases?', size=128),
    }

    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'Name must be unique!'),
    ]

    def get_vals(self, cr, uid, id, context={}):

        vals = {}

        apptype = self.browse(cr, uid, id, context=context)

        config = self.pool.get('ir.model.data').get_object(cr, uid, 'saas', 'saas_settings') 
        vals.update(self.pool.get('saas.config.settings').get_vals(cr, uid, context=context))

        options = {
            'application': {},
            'container': {},
            'service': {},
            'base': {}
        }
        for option in apptype.option_ids:
            options[option.type][option.name] = {'id': option.id, 'name': option.name, 'type': option.type, 'default': option.default}

        vals.update({
            'apptype_name': apptype.name,
            'apptype_system_user': apptype.system_user,
            'apptype_localpath': apptype.localpath,
            'apptype_localpath_services': apptype.localpath_services,
            'apptype_options': options,
            'apptype_symlink': apptype.symlink,
            'apptype_multiple_databases': apptype.multiple_databases,
        })

        return vals

class saas_application_type_option(osv.osv):
    _name = 'saas.application.type.option'

    _columns = {
        'apptype_id': fields.many2one('saas.application.type', 'Application Type', ondelete="cascade", required=True),
        'name': fields.char('Name', size=64, required=True),
        'type': fields.selection([('application','Application'),('container','Container'),('service','Service'),('base','Base')], 'Type', required=True),
        'default': fields.text('Default value'),
    }

    _sql_constraints = [
        ('name_uniq', 'unique(apptype_id,name)', 'Options name must be unique per apptype!'),
    ]



class saas_application(osv.osv):
    _name = 'saas.application'

    _columns = {
        'name': fields.char('Name', size=64, required=True),
        'code': fields.char('Code', size=10, required=True),
        'type_id': fields.many2one('saas.application.type', 'Type', required=True),
        'current_version': fields.char('Current version', size=64, required=True),
        'next_server_id': fields.many2one('saas.server', 'Next server'),
        'default_image_id': fields.many2one('saas.image', 'Default Image', required=True),
        'admin_name': fields.char('Admin name', size=64, required=True),
        'admin_email': fields.char('Admin email', size=64),
        'archive_id': fields.many2one('saas.container', 'Archive'),
        'option_ids': fields.one2many('saas.application.option', 'application_id', 'Options'),
        'link_ids': fields.one2many('saas.application.link', 'application_id', 'Links'),
        'version_ids': fields.one2many('saas.application.version', 'application_id', 'Versions'),
        'buildfile': fields.text('Build File'),
        'container_ids': fields.one2many('saas.container', 'application_id', 'Containers'),
        'container_backup_ids': fields.many2many('saas.container', 'saas_application_container_backup_rel', 'application_id', 'backup_id', 'Backups Containers'),
        'container_time_between_save': fields.integer('Minutes between each container save', required=True),
        'container_saverepo_change': fields.integer('Days before container saverepo change', required=True),
        'container_saverepo_expiration': fields.integer('Days before container saverepo expiration', required=True),
        'container_save_expiration': fields.integer('Days before container save expiration', required=True),
        'base_backup_ids': fields.many2many('saas.container', 'saas_application_base_backup_rel', 'application_id', 'backup_id', 'Backups Bases'),
        'base_time_between_save': fields.integer('Minutes between each base save', required=True),
        'base_saverepo_change': fields.integer('Days before base saverepo change', required=True),
        'base_saverepo_expiration': fields.integer('Days before base saverepo expiration', required=True),
        'base_save_expiration': fields.integer('Days before base save expiration', required=True),
    }

    _sql_constraints = [
        ('code_uniq', 'unique(code)', 'Code must be unique!'),
    ]

    def get_vals(self, cr, uid, id, context=None):

        vals = {}

        app = self.browse(cr, uid, id, context=context)

        vals.update(self.pool.get('saas.application.type').get_vals(cr, uid, app.type_id.id, context=context))

        now = datetime.now()
        computed_version = app.current_version + '.' + now.strftime('%Y%m%d.%H%M%S')

        options = {}
        for option in app.type_id.option_ids:
            if option.type == 'application':
                options[option.name] = {'id': option.id, 'name': option.name, 'value': option.default}
        for option in app.option_ids:
            options[option.name.name] = {'id': option.id, 'name': option.name.name, 'value': option.value}

        links = {}
        for link in app.link_ids:
            links[link.name.code] = {
                'id': link.id, 'app_id': link.name.id, 'name': link.name.name, 'code': link.name.code,
                'required': link.required, 'auto': link.auto, 'make_link': link.make_link, 'next': link.next,
                'container': link.container, 'service': link.service, 'base': link.base
            }


        vals.update({
            'app_id': app.id,
            'app_name': app.name,
            'app_code': app.code,
            'app_instances_path': app.instances_path,
            'app_full_archivepath': vals['config_archive_path'] + '/' + app.type_id.name + '-' + app.code,
            'app_full_hostpath': vals['config_services_hostpath'] + app.type_id.name + '-' + app.code,
            'app_full_localpath': vals['apptype_localpath'] and vals['apptype_localpath'] + '/' + app.type_id.name + '-' + app.code or '',
            'app_build_directory': app.build_directory,
            'app_poweruser_name': app.poweruser_name,
            'app_poweruser_password': app.poweruser_password,
            'app_poweruser_email': app.poweruser_email,
            'app_current_version': app.current_version,
            'app_computed_version': computed_version,
            'app_buildfile': app.buildfile,
            'app_options': options,
            'app_links': links
        })

        return vals


    def get_current_version(self, cr, uid, vals, context=None):
        return False

    def build(self, cr, uid, ids, context=None):
        version_obj = self.pool.get('saas.application.version')

        for app in self.browse(cr, uid, ids, context={}):
            if not app.archive_id:
                raise osv.except_osv(_('Date error!'),_("You need to specify the archive where the version must be stored."))
            vals = self.get_vals(cr, uid, app.id, context=context)
            current_version = self.get_current_version(cr, uid, vals, context)
            if current_version:
                self.write(cr, uid, [app.id], {'current_version': current_version}, context=context)
            current_version = current_version or app.current_version
            now = datetime.now()
            version = current_version + '.' + now.strftime('%Y%m%d.%H%M')
            version_obj.create(cr, uid, {'application_id': app.id, 'name': version, 'archive_id': app.archive_id and app.archive_id.id}, context=context)


class saas_application_option(osv.osv):
    _name = 'saas.application.option'

    _columns = {
        'application_id': fields.many2one('saas.application', 'Application', ondelete="cascade", required=True),
        'name': fields.many2one('saas.application.type.option', 'Option', required=True),
        'value': fields.text('Value'),
    }

    _sql_constraints = [
        ('name_uniq', 'unique(application_id,name)', 'Option name must be unique per application!'),
    ]

class saas_application_version(osv.osv):
    _name = 'saas.application.version'
    _inherit = ['saas.model']

    _columns = {
        'name': fields.char('Name', size=64, required=True),
        'application_id': fields.many2one('saas.application', 'Application', required=True),
        'archive_id': fields.many2one('saas.container', 'Archive', required=True),
        'service_ids': fields.one2many('saas.service','application_version_id', 'Services'),
    }

    _sql_constraints = [
        ('name_app_uniq', 'unique (name,application_id)', 'The name of the version must be unique per application !')
    ]

    _order = 'create_date desc'

    def get_vals(self, cr, uid, id, context=None):

        vals = {}

        app_version = self.browse(cr, uid, id, context=context)

        vals.update(self.pool.get('saas.application').get_vals(cr, uid, app_version.application_id.id, context=context))


        archive_vals = self.pool.get('saas.container').get_vals(cr, uid, app_version.archive_id.id, context=context)
        vals.update({
            'archive_id': archive_vals['container_id'],
            'archive_fullname': archive_vals['container_fullname'],
            'archive_server_id': archive_vals['server_id'],
            'archive_server_ssh_port': archive_vals['server_ssh_port'],
            'archive_server_domain': archive_vals['server_domain'],
            'archive_server_ip': archive_vals['server_ip'],
        })

        vals.update({
            'app_version_id': app_version.id,
            'app_version_name': app_version.name,
            'app_version_fullname': vals['app_code'] + '_' + app_version.name,
            'app_version_full_archivepath': vals['app_full_archivepath'] + '/' + app_version.name,
            'app_version_full_archivepath_targz': vals['app_full_archivepath'] + '/' + app_version.name + '.tar.gz',
            'app_version_full_hostpath': vals['app_full_hostpath'] + '/' + app_version.name,
            'app_version_full_localpath': vals['app_full_localpath'] + '/' + app_version.name,
        })

        return vals


    def unlink(self, cr, uid, ids, context=None):
        for app in self.browse(cr, uid, ids, context=context):
            if app.service_ids:
                raise osv.except_osv(_('Inherit error!'),_("A service is linked to this application version, you can't delete it!"))
        return super(saas_application_version, self).unlink(cr, uid, ids, context=context)


    def build_application(self, cr, uid, vals, context):
        return

    def deploy(self, cr, uid, vals, context):
        context.update({'saas-self': self, 'saas-cr': cr, 'saas-uid': uid})
        ssh, sftp = execute.connect(vals['archive_fullname'], context=context)
        execute.execute(ssh, ['mkdir', vals['app_full_archivepath']], context)
        execute.execute(ssh, ['rm', '-rf', vals['app_version_full_archivepath']], context)
        execute.execute(ssh, ['mkdir', vals['app_version_full_archivepath']], context)
        self.build_application(cr, uid, vals, context)
        execute.execute(ssh, ['echo "' + vals['app_version_name'] + '" >> ' +  vals['app_version_full_archivepath'] + '/VERSION.txt'], context)
        execute.execute(ssh, ['tar', 'czf', vals['app_version_full_archivepath_targz'], '-C', vals['app_full_archivepath'] + '/' + vals['app_version_name'], '.'], context)
        ssh.close()
        sftp.close()

    def purge(self, cr, uid, vals, context={}):
        context.update({'saas-self': self, 'saas-cr': cr, 'saas-uid': uid})
        ssh, sftp = execute.connect(vals['archive_fullname'], context=context)
        execute.execute(ssh, ['rm', '-rf', vals['app_version_full_archivepath']], context)
        execute.execute(ssh, ['rm', vals['app_version_full_archivepath_targz']], context)
        ssh.close()
        sftp.close()

class saas_application_link(osv.osv):
    _name = 'saas.application.link'

    _columns = {
        'application_id': fields.many2one('saas.application', 'Application', ondelete="cascade", required=True),
        'name': fields.many2one('saas.application', 'Application', required=True),
        'required': fields.boolean('Required?'),
        'auto': fields.boolean('Auto?'),
        'make_link': fields.boolean('Make docker link?'),
        'container': fields.boolean('Container?'),
        'service': fields.boolean('Service?'),
        'base': fields.boolean('Base?'),
        'next': fields.many2one('saas.container', 'Next')
    }

    _sql_constraints = [
        ('name_uniq', 'unique(application_id,name)', 'Links must be unique per application!'),
    ]