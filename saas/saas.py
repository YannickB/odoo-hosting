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
import execute
import ast

import logging
_logger = logging.getLogger(__name__)


class saas_log(osv.osv):
    _name = 'saas.log'

    def _get_name(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for log in self.browse(cr, uid, ids, context=context):
            model_obj = self.pool.get(log.model)
            record = model_obj.browse(cr, uid, log.res_id, context=context)
            res[log.id] = ''
            if record and hasattr(record, 'name'):
                res[log.id] = record.name
        return res

    _columns = {
        'model': fields.char('Related Document Model', size=128, select=1),
        'res_id': fields.integer('Related Document ID', select=1),
        'name': fields.function(_get_name, type="char", size=128, string='Name'),
        'action': fields.char('Action', size=64),
        'log': fields.text('log'),
        'state': fields.selection([('unfinished','Not finished'),('ok','Ok'),('ko','Ko')], 'State', required=True),
        'create_date': fields.datetime('Launch Date'),
        'finish_date': fields.datetime('Finish Date'),
        'expiration_date': fields.datetime('Expiration Date'),
    }

    _defaults = {
        'state': 'unfinished'
    }

    _order = 'create_date desc'

class saas_log_model(osv.AbstractModel):
    _name = 'saas.log.model'

    _columns = {
        'log_ids': fields.one2many('saas.log', 'res_id',
            domain=lambda self: [('model', '=', self._name)],
            auto_join=True,
            string='Logs'),
    }

    def create_log(self, cr, uid, id, action, context):
        if 'log_id' in context:
            return context
        log_obj = self.pool.get('saas.log')
        if context == None:
            context = {}
        if not 'logs' in context:
            context['logs'] = {}
        if not self._name in context['logs']:
            context['logs'][self._name] = {}
        if not id in context['logs'][self._name]:
            log_id = log_obj.create(cr, uid, {'model': self._name, 'res_id': id, 'action': action}, context=context)
            context['logs'][self._name][id] = {}
            context['logs'][self._name][id]['log_model'] = self._name
            context['logs'][self._name][id]['log_res_id'] = id
            context['logs'][self._name][id]['log_id'] = log_id
            context['logs'][self._name][id]['log_log'] = ''
        return context

    def end_log(self, cr, uid, id, context=None):
        log_obj = self.pool.get('saas.log')
        if 'logs' in  context:
            log = log_obj.browse(cr, uid, context['logs'][self._name][id]['log_id'], context=context)
            if log.state == 'unfinished':
                log_obj.write(cr, uid, [context['logs'][self._name][id]['log_id']], {'state': 'ok'}, context=context)

    def reinstall(self, cr, uid, ids, context=None):
        for record in self.browse(cr, uid, ids, context=context):
            context = self.create_log(cr, uid, record.id, 'reinstall', context)
            vals = self.get_vals(cr, uid, record.id, context=context)
            self.purge(cr, uid, vals, context=context)
            self.deploy(cr, uid, vals, context=context)
            self.end_log(cr, uid, record.id, context=context)

    def unlink(self, cr, uid, ids, context=None):
        log_obj = self.pool.get('saas.log')
        log_ids = log_obj.search(cr, uid, [('model','=',self._name),('res_id','in',ids)],context=context)
        log_obj.unlink(cr, uid, log_ids, context=context)
        return super(saas_log_model, self).unlink(cr, uid, ids, context=context)

class saas_image(osv.osv):
    _name = 'saas.image'

    _columns = {
        'name': fields.char('Image name', size=64, required=True),
        'application_id': fields.many2one('saas.application', 'Application'),
        'current_version': fields.char('Current version', size=64, required=True),
        'dockerfile': fields.text('DockerFile'),
        'volume_ids': fields.one2many('saas.image.volume', 'image_id', 'Volumes'),
        'port_ids': fields.one2many('saas.image.port', 'image_id', 'Ports'),
        'version_ids': fields.one2many('saas.image.version','image_id', 'Versions'),
    }

    def get_vals(self, cr, uid, id, context={}):

        vals = {}

        image = self.browse(cr, uid, id, context=context)

        config = self.pool.get('ir.model.data').get_object(cr, uid, 'saas', 'saas_settings') 
        vals.update(self.pool.get('saas.config.settings').get_vals(cr, uid, context=context))

        ports = {}
        for port in image.port_ids:
            ports[port.name] = {'id': port.id, 'name': port.name, 'localport': port.localport}

        volumes = {}
        for volume in image.volume_ids:
            volumes[volume.id] = {'id': volume.id, 'name': volume.name}

        vals.update({
            'image_name': image.name,
            'image_ports': ports,
            'image_volumes': volumes,
            'image_dockerfile': image.dockerfile
        })

        return vals

    def build(self, cr, uid, ids, context=None):
        version_obj = self.pool.get('saas.image.version')

        for image in self.browse(cr, uid, ids, context={}):
            if not image.dockerfile:
                continue
            now = datetime.now()
            version = image.current_version + '.' + now.strftime('%Y%m%d.%H%M')
            version_obj.create(cr, uid, {'image_id': image.id, 'name': version}, context=context)

    def unlink(self, cr, uid, ids, context=None):
        for image in self.browse(cr, uid, ids, context=context):
            vals = self.get_vals(cr, uid, image.id, context=context)
            self.remove_image(cr, uid, image.id, vals, context=context)
        return super(saas_image, self).unlink(cr, uid, ids, context=context)

class saas_image_volume(osv.osv):
    _name = 'saas.image.volume'

    _columns = {
        'image_id': fields.many2one('saas.image', 'Image', ondelete="cascade", required=True),
        'name': fields.char('Path', size=128, required=True),
        'hostpath': fields.char('Host path', size=128),
        'readonly': fields.boolean('Readonly?'),
        'nosave': fields.boolean('No save?'),
    }


class saas_image_port(osv.osv):
    _name = 'saas.image.port'

    _columns = {
        'image_id': fields.many2one('saas.image', 'Image', ondelete="cascade", required=True),
        'name': fields.char('Name', size=64, required=True),
        'localport': fields.char('Local port', size=12, required=True),
        'expose': fields.boolean('Expose?'),
    }

class saas_image_version(osv.osv):
    _name = 'saas.image.version'
    _inherit = ['saas.log.model']

    _columns = {
        'image_id': fields.many2one('saas.image','Image', ondelete='cascade', required=True),
        'name': fields.char('Version', size=64, required=True),
        'container_ids': fields.one2many('saas.container','image_version_id', 'Containers'),
    }

    _order = 'create_date desc'

    def get_vals(self, cr, uid, id, context=None):

        vals = {}

        image_version = self.browse(cr, uid, id, context=context)

        vals.update(self.pool.get('saas.image').get_vals(cr, uid, image_version.image_id.id, context=context))

        vals.update({
            'image_version_name': image_version.name,
            'image_version_fullname': image_version.image_id.name + ':' + image_version.name,
        })


        return vals

    def create(self, cr, uid, vals, context=None):
        res = super(saas_image_version, self).create(cr, uid, vals, context=context)
        context = self.create_log(cr, uid, res, 'create', context)
        vals = self.get_vals(cr, uid, res, context=context)
        self.build(cr, uid, res, vals, context=context)
        self.end_log(cr, uid, res, context=context)
        return res 


    def unlink(self, cr, uid, ids, context=None):
        container_obj = self.pool.get('saas.container')
        if container_obj.search(cr, uid, [('image_version_id','in',ids)], context=context):
            raise osv.except_osv(_('Inherit error!'),_("A container is linked to this image version, you can't delete it!"))
        for image in self.browse(cr, uid, ids, context=context):
            vals = self.get_vals(cr, uid, image.id, context=context)
            self.purge(cr, uid, image.id, vals, context=context)
        return super(saas_image_version, self).unlink(cr, uid, ids, context=context)

class saas_domain(osv.osv):
    _name = 'saas.domain'
    _inherit = ['saas.log.model']

    _columns = {
        'name': fields.char('Domain name', size=64, required=True)
    }

    def get_vals(self, cr, uid, id, context=None):

        vals = {}

        domain = self.browse(cr, uid, id, context=context)

        config = self.pool.get('ir.model.data').get_object(cr, uid, 'saas', 'saas_settings') 
        vals.update(self.pool.get('saas.config.settings').get_vals(cr, uid, context=context))

        vals.update({
            'domain_name': domain.name,
            'domain_configfile': '/etc/bind/db.' + domain.name,
        })

        return vals

    def create(self, cr, uid, vals, context=None):
        res = super(saas_domain, self).create(cr, uid, vals, context=context)
        context = self.create_log(cr, uid, res, 'create', context)
        vals = self.get_vals(cr, uid, res, context=context)
        self.deploy(cr, uid, vals, context=context)
        self.end_log(cr, uid, res, context=context)
        return res 


    def unlink(self, cr, uid, ids, context=None):
        for domain in self.browse(cr, uid, ids, context=context):
            vals = self.get_vals(cr, uid, domain.id, context=context)
            self.purge(cr, uid, vals, context=context)
        return super(saas_domain, self).unlink(cr, uid, ids, context=context)


class saas_application_type(osv.osv):
    _name = 'saas.application.type'

    _columns = {
        'name': fields.char('Name', size=64, required=True),
        'system_user': fields.char('System User', size=64, required=True),
        'admin_name': fields.char('Admin name', size=64, required=True),
        'admin_email': fields.char('Admin email', size=64, required=True),
        'mysql': fields.boolean('Can have mysql?'),
        'init_test': fields.boolean('Demo mode must be set at database creation?'),
        'standard_port': fields.char('Standard port', size=12),
        'localpath': fields.char('Localpath', size=128),
        'option_ids': fields.one2many('saas.application.type.option', 'apptype_id', 'Options'),
        'application_ids': fields.one2many('saas.application', 'type_id', 'Applications'),
    }

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
            'apptype_admin_name': apptype.admin_name,
            'apptype_admin_email': apptype.admin_email,
            'apptype_mysql': apptype.mysql,
            'apptype_init_test': apptype.init_test,
            'apptype_localpath': apptype.localpath,
            'apptype_options': options
        })

        return vals

class saas_application_type_option(osv.osv):
    _name = 'saas.application.type.option'

    _columns = {
        'apptype_id': fields.many2one('saas.application.type', 'Application Type', ondelete="cascade", required=True),
        'name': fields.char('Name', size=64, required=True),
        'type': fields.selection([('application','Application'),('container','Container'),('service','Service'),('base','Base')], 'Type', required=True),
        'default': fields.text('Default value'),
#        'inherit': fields.boolean('Inherit?'),
    }


class saas_application(osv.osv):
    _name = 'saas.application'

    _columns = {
        'name': fields.char('Name', size=64, required=True),
        'code': fields.char('Code', size=4, required=True),
        'type_id': fields.many2one('saas.application.type', 'Type', required=True),
        'current_version': fields.char('Current version', size=64, required=True),
        'bdd': fields.selection([('pgsql','PostgreSQL'),('mysql','MySQL')], 'BDD', required=True),
        # 'next_instance_id': fields.many2one('saas.service', 'Next instance'),
        # 'demo_saas_id': fields.many2one('saas.saas', 'Demo SaaS'),
        # 'preprod_domain_id': fields.many2one('saas.domain', 'Preprod Domain'),
        # 'preprod_server_id': fields.many2one('saas.server', 'Preprod server'),
        # 'preprod_bdd_server_id': fields.many2one('saas.server', 'Preprod database server'),
        # 'preprod_port': fields.integer('Port preprod'),
        # 'preprod_instance_id': fields.many2one('saas.service', 'Instance preprod'),
        # 'preprod_mysql_instance_id': fields.many2one('saas.service', 'Instance preprod mysql'),
        # 'test_port': fields.integer('Port test'),
        # 'test_instance_id': fields.many2one('saas.service', 'Instance test'),
        # 'test_mysql_instance_id': fields.many2one('saas.service', 'Instance test mysql'),
        # 'dev_port': fields.integer('Port dev'),
        # 'dev_instance_id': fields.many2one('saas.service', 'Instance dev'),
        # 'dev_mysql_instance_id': fields.many2one('saas.service', 'Instance dev mysql'),
        'instances_path': fields.char('Instances path', size=128),
        'build_directory': fields.char('Build directory', size=128),
        'poweruser_name': fields.char('PowerUser Name', size=64),
        'poweruser_password': fields.char('PowerUser Password', size=64),
        'poweruser_email': fields.char('PowerUser Email', size=64),
        'piwik_demo_id': fields.char('Piwik Demo ID', size=64),
        'version_prod': fields.char('Version Prod', size=64),
        'version_preprod': fields.char('Version Preprod', size=64),
        'version_test': fields.char('Version Test', size=64),
        'version_dev': fields.char('Version Dev', size=64),
        'option_ids': fields.one2many('saas.application.option', 'application_id', 'Options'),
        'version_ids': fields.one2many('saas.application.version', 'application_id', 'Versions'),
        'buildfile': fields.text('Build File'),
        'container_ids': fields.one2many('saas.container', 'application_id', 'Containers'),
        'container_time_between_save': fields.integer('Minutes between each container save', required=True),
        'container_saverepo_change': fields.integer('Days before container saverepo change', required=True),
        'container_saverepo_expiration': fields.integer('Days before container saverepo expiration', required=True),
        'base_time_between_save': fields.integer('Minutes between each base save', required=True),
        'base_saverepo_change': fields.integer('Days before base saverepo change', required=True),
        'base_saverepo_expiration': fields.integer('Days before base saverepo expiration', required=True),
    }

    _defaults = {
        'bdd': 'pgsql',
    }

    def get_vals(self, cr, uid, id, context=None):

        vals = {}

        app = self.browse(cr, uid, id, context=context)

        vals.update(self.pool.get('saas.application.type').get_vals(cr, uid, app.type_id.id, context=context))

        now = datetime.now()
        computed_version = app.current_version + '.' + now.strftime('%Y%m%d.%H%M')

        options = {}
        for option in app.type_id.option_ids:
            if option.type == 'application':
                options[option.name] = {'id': option.id, 'name': option.name, 'value': option.default}
        for option in app.option_ids:
            options[option.name.name] = {'id': option.id, 'name': option.name.name, 'value': option.value}


        vals.update({
            'app_name': app.name,
            'app_code': app.code,
            'app_bdd': app.bdd,
            'app_instances_path': app.instances_path,
            'app_full_archivepath': vals['config_archive_path'] + '/' + app.type_id.name + '-' + app.code,
            'app_full_hostpath': vals['config_services_hostpath'] + '/' + app.type_id.name + '-' + app.code,
            'app_full_localpath': vals['apptype_localpath'] and vals['apptype_localpath'] + '/' + app.type_id.name + '-' + app.code or '',
            'app_build_directory': app.build_directory,
            'app_poweruser_name': app.poweruser_name,
            'app_poweruser_password': app.poweruser_password,
            'app_poweruser_email': app.poweruser_email,
            'app_current_version': app.current_version,
            'app_computed_version': computed_version,
            'app_buildfile': app.buildfile,
            'app_options': options
        })

        return vals



    def build(self, cr, uid, ids, context=None):
        version_obj = self.pool.get('saas.application.version')

        for app in self.browse(cr, uid, ids, context={}):
            if not app.buildfile:
                continue
            current_version = self.get_current_version(cr, uid, app, context)
            if current_version:
                self.write(cr, uid, [app.id], {'current_version': current_version}, context=context)
            current_version = current_version or app.current_version
            now = datetime.now()
            version = current_version + '.' + now.strftime('%Y%m%d.%H%M')
            version_obj.create(cr, uid, {'application_id': app.id, 'name': version}, context=context)


class saas_application_option(osv.osv):
    _name = 'saas.application.option'

    _columns = {
        'application_id': fields.many2one('saas.application', 'Application', ondelete="cascade", required=True),
        'name': fields.many2one('saas.application.type.option', 'Option', required=True),
        'value': fields.text('Value'),
    }

class saas_application_version(osv.osv):
    _name = 'saas.application.version'
    _inherit = ['saas.log.model']

    _columns = {
        'name': fields.char('Name', size=64, required=True),
        'application_id': fields.many2one('saas.application', 'Application', required=True),
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

        vals.update({
            'app_version_id': app_version.id,
            'app_version_name': app_version.name,
            'app_version_full_archivepath': vals['app_full_archivepath'] + '/' + app_version.name,
            'app_version_full_archivepath_targz': vals['app_full_archivepath'] + '/' + app_version.name + '.tar.gz',
            'app_version_full_hostpath': vals['app_full_hostpath'] + '/' + app_version.name,
            'app_version_full_localpath': vals['app_full_localpath'] + '/' + app_version.name,
        })

        return vals

    def create(self, cr, uid, vals, context=None):
        res = super(saas_application_version, self).create(cr, uid, vals, context=context)
        context = self.create_log(cr, uid, res, 'create', context)
        vals = self.get_vals(cr, uid, res, context=context)
        self.build(cr, uid, res, vals, context)
        self.end_log(cr, uid, res, context)
        return res 


    def unlink(self, cr, uid, ids, context=None):
        for app in self.browse(cr, uid, ids, context=context):
            if app.service_ids:
                raise osv.except_osv(_('Inherit error!'),_("A service is linked to this application version, you can't delete it!"))
            vals = self.get_vals(cr, uid, app.id, context=context)
            self.purge(cr, uid, app.id, vals, context=context)
        return super(saas_application_version, self).unlink(cr, uid, ids, context=context)
###################
    # def unlink(self, cr, uid, ids, context=None):

        # config = self.pool.get('ir.model.data').get_object(cr, uid, 'saas', 'saas_settings')

        # for version in self.browse(cr, uid, ids, context=context):

            # _logger.info('Removing version %s', version.name)

            # args = [
                # config.openerp_path + '/saas/saas/shell/populate.sh',
                # 'remove_version',
                # version.application_id.code,
                # version.name,
                # version.application_id.archive_path,
            # ]
            # _logger.info('command %s', " ".join(args))
            # proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            # outfile = open(config.log_path + '/populate.log', "w")
            # for line in proc.stdout:
               # _logger.info(line)
               # outfile.write(line)


        # return super(saas_version, self).unlink(cr, uid, ids, context=context)

    # def build(self, cr, uid, ids, context={}):

        # saas_obj = self.pool.get('saas.saas')
        # instance_obj = self.pool.get('saas.service')

        # config = self.pool.get('ir.model.data').get_object(cr, uid, 'saas', 'saas_settings')
        # name = context['build_name']

        # for app in self.browse(cr, uid, ids, context=context):

            # _logger.info('Rebuilding %s', name)

            # if context['build']:
                # args = [
                    # config.openerp_path + '/saas/saas/shell/build.sh',
                    # 'build_archive',
                    # app.type_id.name,
                    # app.code,
                    # name,
                    # app.type_id.system_user,
                    # app.archive_path,
                    # config.openerp_path,
                    # app.build_directory
                # ]
                # _logger.info('command %s', " ".join(args))
                # proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                # outfile = open(config.log_path + '/build_' + name + '.log', "w")
                # for line in proc.stdout:
                   # _logger.info(line)
                   # outfile.write(line)
            # else:
                # args = [
                    # config.openerp_path + '/saas/saas/shell/build.sh',
                    # 'build_copy',
                    # app.type_id.name,
                    # app.code,
                    # name,
                    # context['build_source'],
                    # config.openerp_path,
                    # app.archive_path,
                # ]
                # _logger.info('command %s', " ".join(args))
                # proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                # outfile = open(config.log_path + '/build_' + name + '.log', "w")
                # for line in proc.stdout:
                   # _logger.info(line)
                   # outfile.write(line)


            # instance_ids = instance_obj.search(cr, uid, [('name','in',[app.code + '-' + name, app.code + '-' + name + '-my']), ('application_id', '=', app.id)], context=context)
            # saas_ids = saas_obj.search(cr, uid, [('instance_id', 'in', instance_ids)], context=context)
            # saas_obj.unlink(cr, uid, saas_ids, context=context)
            # instance_obj.unlink(cr, uid, instance_ids, context=context)

            # instance_id = instance_obj.create(cr, uid, {
                # 'name': app.code + '-' + name,
                # 'application_id': app.id,
                # 'bdd': 'pgsql',
                # 'server_id': app.preprod_server_id.id,
                # 'database_server_id': app.preprod_bdd_server_id.id,
                # 'port': getattr(app, name + '_port'),
                # 'prod': False,
                # 'skip_analytics': True
              # }, context=context)
            # self.write(cr, uid, [app.id], {name + '_instance_id': instance_id}, context=context)
            # saas_obj.create(cr, uid, {
                # 'name': name,
                # 'title': 'Test',
                # 'domain_id': app.preprod_domain_id.id,
                # 'instance_id': instance_id,
                # 'poweruser_name': app.type_id.admin_name,
                # 'poweruser_passwd': app.poweruser_password,
                # 'poweruser_email': app.poweruser_email,
                # 'build': 'build',
                # 'test': app.type_id.init_test,
              # }, context=context)

            # if context['build']:
                # args = [
                    # config.openerp_path + '/saas/saas/shell/build.sh',
                    # 'build_dump',
                    # app.type_id.name,
                    # app.code,
                    # name,
                    # app.preprod_domain_id.name,
                    # app.code + '-' + name,
                    # app.type_id.system_user,
                    # app.preprod_server_id.name,
                    # app.preprod_bdd_server_id.name,
                    # 'pgsql',
                    # config.openerp_path,
                    # app.archive_path,
                    # app.instances_path,
                    # app.preprod_bdd_server_id.mysql_passwd
                # ]
                # _logger.info('command %s', " ".join(args))
                # proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                # outfile = open(config.log_path + '/build_' + name + '.log', "w")
                # for line in proc.stdout:
                   # _logger.info(line)
                   # outfile.write(line)

            # if app.type_id.mysql:
              # instance_id = instance_obj.create(cr, uid, {
                  # 'name': app.code + '-' + name + '-my',
                  # 'application_id': app.id,
                  # 'bdd': 'mysql',
                  # 'server_id': app.preprod_server_id.id,
                  # 'database_server_id': app.preprod_bdd_server_id.id,
                  # 'port': getattr(app, name + '_port'),
                  # 'prod': False,
                  # 'skip_analytics': True
                # }, context=context)
              # self.write(cr, uid, [app.id], {name + '_mysql_instance_id': instance_id}, context=context)
              # saas_obj.create(cr, uid, {
                  # 'name': name + '-my',
                  # 'title': 'Test',
                  # 'domain_id': app.preprod_domain_id.id,
                  # 'instance_id': instance_id,
                  # 'poweruser_name': app.type_id.admin_name,
                  # 'poweruser_passwd': app.poweruser_password,
                  # 'poweruser_email': app.poweruser_email,
                  # 'build': 'build',
                  # 'test': app.type_id.init_test,
                # }, context=context)

              # _logger.info('system_user %s', app.type_id.system_user)
              # _logger.info('bdd_server %s', app.preprod_bdd_server_id.name)
              # if context['build']:
                  # args = [
                      # config.openerp_path + '/saas/saas/shell/build.sh',
                      # 'build_dump',
                      # app.type_id.name,
                      # app.code,
                      # name + '-my',
                      # app.preprod_domain_id.name,
                      # app.code + '-' + name + '-my',
                      # app.type_id.system_user,
                      # app.preprod_server_id.name,
                      # app.preprod_bdd_server_id.name,
                      # 'mysql',
                      # config.openerp_path,
                      # app.archive_path,
                      # app.instances_path,
                      # app.preprod_bdd_server_id.mysql_passwd
                  # ]
                  # _logger.info('command %s', " ".join(args))
                  # proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                  # outfile = open(config.log_path + '/build_' + name + '.log', "w")
                  # for line in proc.stdout:
                     # _logger.info(line)
                     # outfile.write(line)


            #Get Version
            # version = ''
            # args = [
                # config.openerp_path + '/saas/saas/shell/build.sh',
                # 'get_version',
                # app.type_id.name,
                # app.code,
                # name,
                # app.preprod_domain_id.name,
                # config.openerp_path,
                # app.instances_path,
                # app.archive_path,
                # app.build_directory
            # ]
            # _logger.info('command %s', " ".join(args))
            # proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            # outfile = open(config.log_path + '/build_' + name + '.log', "w")
            # for line in proc.stdout:
               # _logger.info(line)
               # outfile.write(line)
            # with open(app.archive_path  + '/' + app.code + '/' + app.code + '-' + name + '/VERSION.txt') as f:
                # version = f.read()
                # _logger.info('version : %s', version)
                # self.write(cr, uid, [app.id], {'version_' + name: version}, context=context)


            # if context['build']:
                #Build after
                # args = [
                    # config.openerp_path + '/saas/saas/shell/build.sh',
                    # 'build_after',
                    # app.type_id.name,
                    # app.code,
                    # name,
                    # version,
                    # config.openerp_path,
                    # app.archive_path,
                # ]
                # _logger.info('command %s', " ".join(args))
                # proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                # outfile = open(config.log_path + '/build_' + name + '.log', "w")
                # for line in proc.stdout:
                   # _logger.info(line)
                   # outfile.write(line)

               
            # args = [
                # config.openerp_path + '/saas/saas/apps/' + app.type_id.name + '/deploy.sh',
                # 'create_poweruser',
                # app.code,
                # app.preprod_domain_id.name,
                # name,
                # app.type_id.system_user,
                # app.preprod_server_id.name,
                # app.poweruser_name,
                # app.poweruser_password,
                # app.poweruser_email,
                # app.instances_path,
            # ]
            # _logger.info('command %s', " ".join(args))
            # proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            # outfile = open(config.log_path + '/build_' + name + '.log', "w")
            # for line in proc.stdout:
               # _logger.info(line)
               # outfile.write(line)
               
            # if not app.type_id.init_test :
                # args = [
                    # config.openerp_path + '/saas/saas/apps/' + app.type_id.name + '/deploy.sh',
                    # 'test_specific',
                    # app.code,
                    # app.preprod_domain_id.name,
                    # name,
                    # app.type_id.system_user,
                    # app.preprod_server_id.name,
                    # app.poweruser_name,
                    # app.instances_path,
                # ]
                # _logger.info('command %s', " ".join(args))
                # proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                # outfile = open(config.log_path + '/build_' + name + '.log', "w")
                # for line in proc.stdout:
                   # _logger.info(line)
                   # outfile.write(line)

            # if app.type_id.mysql:
              # args = [
                  # config.openerp_path + '/saas/saas/apps/' + app.type_id.name + '/deploy.sh',
                  # 'create_poweruser',
                  # app.code,
                  # app.preprod_domain_id.name,
                  # name + '-my',
                  # app.type_id.system_user,
                  # app.preprod_server_id.name,
                  # app.poweruser_name,
                  # app.poweruser_password,
                  # app.poweruser_email,
                  # app.instances_path,
              # ]
              # _logger.info('command %s', " ".join(args))
              # proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
              # outfile = open(config.log_path + '/build_' + name + '.log', "w")
              # for line in proc.stdout:
                 # _logger.info(line)
                 # outfile.write(line)
                 
              # if not app.type_id.init_test:
                  # args = [
                      # config.openerp_path + '/saas/saas/apps/' + app.type_id.name + '/deploy.sh',
                      # 'test_specific',
                      # app.code,
                      # app.preprod_domain_id.name,
                      # name + '-my',
                      # app.type_id.system_user,
                      # app.preprod_server_id.name,
                      # app.poweruser_name,
                      # app.instances_path,
                  # ]
                  # _logger.info('command %s', " ".join(args))
                  # proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                  # outfile = open(config.log_path + '/build_' + name + '.log', "w")
                  # for line in proc.stdout:
                     # _logger.info(line)
                     # outfile.write(line)
        # return True
        
        
        
    # def populate(self, cr, uid, ids, context={}):
    
        # instance_obj = self.pool.get('saas.service')
        # version_obj = self.pool.get('saas.version')
        
        # config = self.pool.get('ir.model.data').get_object(cr, uid, 'saas', 'saas_settings')


        # for app in self.browse(cr, uid, ids, context=context):
            # preprod_archive = app.code + '-preprod'
            # prod_archive = app.code + '-prod'

            # with open(app.archive_path  + '/' + app.code + '/' + preprod_archive + '/VERSION.txt') as f:
                # version = f.read()
                # version = version.replace('\n','')
                # _logger.info('version : %s', version)

            # args = [
                # config.openerp_path + '/saas/saas/shell/populate.sh',
                # 'populate',
                # app.code,
                # preprod_archive,
                # prod_archive,
                # app.archive_path,
            # ]
            # _logger.info('command %s', " ".join(args))
            # proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            # outfile = open(config.log_path + '/populate.log', "w")
            # for line in proc.stdout:
               # _logger.info(line)
               # outfile.write(line)
               
               
            # with open(app.archive_path  + '/' + app.code + '/' + prod_archive + '/VERSION.txt') as f:
                # version = f.read()
                # version = version.replace('\n','')
                # _logger.info('version : %s', version)
                # version_ids = version_obj.search(cr, uid, [('name','=',version),('application_id','=',app.id)], context=context)
                # if not version_ids:
                    # version_obj.create(cr, uid, {'name': version, 'application_id': app.id}, context=context)
                # self.write(cr, uid, [app.id], {'version_prod': version}, context=context)
        # return True
            
    # def refresh_demo(self, cr, uid, ids, context={}):
    
        # saas_obj = self.pool.get('saas.saas')
    
        # for app in self.browse(cr, uid, ids, context=context):
            # if app.demo_saas_id:
                # saas_obj.unlink(cr, uid, [app.demo_saas_id.id], context=context)
            
            # demo_id = saas_obj.create(cr, uid, {
              # 'name': 'demo',
              # 'title': 'Demo',
              # 'domain_id': app.preprod_domain_id.id,
              # 'instance_id': app.next_instance_id.id,
              # 'poweruser_name': app.poweruser_name,
              # 'poweruser_passwd': app.poweruser_password,
              # 'poweruser_email': app.poweruser_email,
              # 'build': 'build',
              # 'test': True,
            # }, context=context)
            
            # self.write(cr, uid, [app.id], {'demo_saas_id': demo_id}, context=context)
        ########## return True




class saas_service(osv.osv):
    _name = 'saas.service'
    _inherit = ['saas.log.model']

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



########TODO move app specific field (like port) in a one2many, with type field and value. The type will be a many2one to saas.field.type(name, application) with selection widget, and domain filtering only the field with the same application. The get_vals function will add all value in one2many, and when we create an instance, the one2many is auto filled with default value thanks to a function.
#######The saas.field.type are defined as data in submodule drupal/odoo
    def get_vals(self, cr, uid, id, context=None):

        vals = {}

        service = self.browse(cr, uid, id, context=context)

        vals.update(self.pool.get('saas.application.version').get_vals(cr, uid, service.application_version_id.id, context=context))

        vals.update(self.pool.get('saas.container').get_vals(cr, uid, service.container_id.id, context=context))


        database_vals = self.pool.get('saas.container').get_vals(cr, uid, service.database_container_id.id, context=context)
        vals.update({
            'database_id': database_vals['container_id'],
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

    def create(self, cr, uid, vals, context={}):
        res = super(saas_service, self).create(cr, uid, vals, context=context)
        context = self.create_log(cr, uid, res, 'create', context)
        vals = self.get_vals(cr, uid, res, context=context)
        self.deploy(cr, uid, vals, context=context)
        self.end_log(cr, uid, res, context=context)
        return res


    def unlink(self, cr, uid, ids, context={}):
        for service in self.browse(cr, uid, ids, context=context):
            vals = self.get_vals(cr, uid, service.id, context=context)
            try:
                self.purge(cr, uid, service.id, vals, context=context)
            except:
                pass    
        return super(saas_service, self).unlink(cr, uid, ids, context=context)


    # def create(self, cr, uid, vals, context={}):
        # res = super(saas_instance, self).create(cr, uid, vals, context=context)

        # config = self.pool.get('ir.model.data').get_object(cr, uid, 'saas', 'saas_settings')

        # for instance in self.browse(cr, uid, [res], context=context):

            # _logger.info('Deploying instance %s', instance.name)

            # if 'build_name' in context:
                # archive = instance.application_id.code + '-' + context['build_name']
            # else:
                # archive = 'versions/' + instance.version_many2one.name

            # args = [
                # config.openerp_path + '/saas/saas/shell/deploy.sh',
                # 'instance',
                # instance.application_id.type_id.name,
                # instance.application_id.code,
                # instance.name,
                # instance.application_id.instances_path,
                # instance.bdd,
                # instance.application_id.type_id.system_user,
                # instance.server_id.name,
                # instance.database_server_id.name,
                # instance.database_password,
                # archive,
                # instance.application_id.archive_path,
                # config.openerp_path,
                # str(instance.port),
                # instance.database_server_id.mysql_passwd
            # ]

            # _logger.info('command %s', " ".join(args))
            # proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

            # outfile = open(config.log_path + '/instance_' + instance.name + '.log', "w")
            # for line in proc.stdout:
                # _logger.info(line)
                # outfile.write(line)

            # _logger.info('If prod, dont forget to update the workers in conf')
        # return res

    # def write(self, cr, uid, ids, vals, context={}):

        # for instance in self.browse(cr, uid, ids, context=context):

            # if instance.prod and 'version_many2one' in vals and vals['version_many2one'] != instance.version_many2one:
                # self.upgrade(cr, uid, [instance.id], vals['version_many2one'], context=context)

        # return super(saas_instance, self).write(cr, uid, ids, vals, context=context)

    # def unlink(self, cr, uid, ids, context=None):

        # config = self.pool.get('ir.model.data').get_object(cr, uid, 'saas', 'saas_settings')

        # for instance in self.browse(cr, uid, ids, context=context):

            # _logger.info('Removing instance %s', instance.name)

            # _logger.info('command : %s', config.openerp_path + '/saas/saas/shell/purge.sh ' + 'instance' + ' ' + instance.application_id.type_id.name  +  ' ' + instance.name + ' ' + instance.application_id.instances_path + ' ' + instance.bdd + ' ' + instance.application_id.type_id.system_user + ' ' + instance.server_id.name + ' ' + instance.database_server_id.name + ' ' + config.openerp_path)

            # proc = subprocess.Popen([config.openerp_path + '/saas/saas/shell/purge.sh', 'instance', instance.application_id.type_id.name, instance.name, instance.application_id.instances_path, instance.bdd, instance.application_id.type_id.system_user, instance.server_id.name, instance.database_server_id.name, config.openerp_path, instance.database_server_id.mysql_passwd], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

            # outfile = open(config.log_path + '/instance_' + instance.name + '.log', "w")
            # for line in proc.stdout:
                # _logger.info(line)
                # outfile.write(line)

        # return super(saas_instance, self).unlink(cr, uid, ids, context=context)
        
        
    # def upgrade(self, cr, uid, ids, version_id, context=None):
    
        # saas_obj = self.pool.get('saas.saas')

        # config = self.pool.get('ir.model.data').get_object(cr, uid, 'saas', 'saas_settings')
        
        # self.save(cr, uid, ids, type='preupgrade', context=context)

        # version = self.pool.get('saas.version').browse(cr, uid, version_id, context=context).name

        # for instance in self.browse(cr, uid, ids, context=context):

            # _logger.info('Upgrading instance %s', instance.name)

            # archive = instance.application_id.code + '-prod'
            # if 'build_name' in context:
                # archive = instance.application_id.code + '-' + context['build_name']

            # args = [
                # config.openerp_path + '/saas/saas/shell/upgrade.sh',
                # instance.application_id.type_id.name,
                # instance.application_id.code,
                # instance.name,
                # instance.application_id.type_id.system_user,
                # instance.server_id.name,
                # version,
                # instance.application_id.instances_path,
                # config.openerp_path,
                # instance.application_id.archive_path,
            # ]

            # _logger.info('command %s', " ".join(args))
            # proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

            # outfile = open(config.log_path + '/instance_' + instance.name + '.log', "w")
            # for line in proc.stdout:
                # _logger.info(line)
                # outfile.write(line)

            # saas_ids = saas_obj.search(cr, uid, [('instance_id', '=', instance.id)], context=context)
            # for saas in saas_obj.browse(cr, uid, saas_ids, context=context):
                # args = [
                    # config.openerp_path + '/saas/saas/apps/' + instance.application_id.type_id.name + '/upgrade.sh',
                    # 'upgrade_saas',
                    # instance.application_id.code,
                    # saas.name,
                    # saas.domain_id.name,
                    # instance.name,
                    # instance.application_id.type_id.system_user,
                    # instance.server_id.name,
                    # str(instance.port),
                    # instance.application_id.type_id.admin_name,
                    # saas.admin_passwd,
                    # instance.application_id.instances_path,
                # ]

                # _logger.info('command %s', " ".join(args))
                # proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

                # outfile = open(config.log_path + '/instance_' + instance.name + '.log', "w")
                # for line in proc.stdout:
                    # _logger.info(line)
                    # outfile.write(line)

        # return True

    # def save(self, cr, uid, ids, saas_id=False, type='manual', context=None):

        # saas_obj = self.pool.get('saas.saas')
        # save_obj = self.pool.get('saas.save')
        # config = self.pool.get('ir.model.data').get_object(cr, uid, 'saas', 'saas_settings')

        # for instance in self.browse(cr, uid, ids, context=context):

            # _logger.info('Saving instance %s', instance.name)



            # saas_names = ''
            # if saas_id:
                # type_save = 'saas'
                # saas_ids = [saas_id]
                # for saas in saas_obj.browse(cr, uid, [saas_id], context=context):
                    # saas_names = saas.name + '.' + saas.domain_id.name
            # else:
                # type_save = 'instance'
                # saas_ids = saas_obj.search(cr, uid, [('instance_id', '=', instance.id)], context=context)
                # for saas in saas_obj.browse(cr, uid, saas_ids, context=context):
                    # if saas_names:
                        # saas_names += ','
                    # saas_names += saas.name + '.' + saas.domain_id.name


            # filename = time.strftime("%Y-%m-%d")
            # if type != 'auto':
                # filename += time.strftime("-%H-%M")
            # filename += '-' + instance.server_id.name.replace(".","-") + '-' + instance.name + '-' + type

            # args = [
                # config.openerp_path + '/saas/saas/shell/save.sh',
                # 'save_dump',
                # instance.application_id.type_id.name,
                # instance.application_id.code,
                # saas_names,
                # filename,
                # instance.server_id.name,
                # instance.database_server_id.name,
                # instance.name,
                # instance.application_id.type_id.system_user,
                # config.backup_directory,
                # instance.application_id.instances_path,
                # config.openerp_path,
                # config.ftpuser,
                # config.ftppass,
                # config.ftpserver
            # ]
            # _logger.info('command %s', " ".join(args))
            # proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            # outfile = open(config.log_path + '/save.log', "w")
            # for line in proc.stdout:
               # _logger.info(line)
               # outfile.write(line)

            # version = instance.prod and instance.version_many2one.name or False
            # save_obj.create(cr, uid, {'name': filename, 'instance_id': instance.id, 'saas_ids': [(6, 0, saas_ids)], 'version': version}, context=context)

    # def button_save(self, cr, uid, ids, context={}):
        # self.save(cr, uid, ids, context=context)
        # return True

class saas_service_option(osv.osv):
    _name = 'saas.service.option'

    _columns = {
        'service_id': fields.many2one('saas.service', 'Service', ondelete="cascade", required=True),
        'name': fields.many2one('saas.application.type.option', 'Option', required=True),
        'value': fields.text('Value'),
    }



class saas_config_settings(osv.osv):
    _name = 'saas.config.settings'
    _description = 'SaaS configuration'

    _columns = {
        'conductor_path': fields.char('Conductor Path', size=128),
        'log_path': fields.char('SaaS Log Path', size=128),
        'archive_path': fields.char('Archive path', size=128),
        'services_hostpath': fields.char('Host services path', size=128),
        'backup_directory': fields.char('Backup directory', size=128),
        'piwik_server': fields.char('Piwik server', size=128),
        'piwik_password': fields.char('Piwik Password', size=128),
        'dns_id': fields.many2one('saas.container', 'DNS Server'),
        'shinken_id': fields.many2one('saas.container', 'Shinken Server'),
        'bup_id': fields.many2one('saas.container', 'BUP Server'),
        'home_directory': fields.char('Home directory', size=128),
        'ftpuser': fields.char('FTP User', size=64),
        'ftppass': fields.char('FTP Pass', size=64),
        'ftpserver': fields.char('FTP Server', size=64),
    }

    def get_vals(self, cr, uid, context={}):
        context['from_config'] = True
        config = self.pool.get('ir.model.data').get_object(cr, uid, 'saas', 'saas_settings')

        vals = {}

        if config.dns_id:
            dns_vals = self.pool.get('saas.container').get_vals(cr, uid, config.dns_id.id, context=context)
            vals.update({
                'dns_id': dns_vals['container_id'],
                'dns_fullname': dns_vals['container_fullname'],
                'dns_ssh_port': dns_vals['container_ssh_port'],
                'dns_server_id': dns_vals['server_id'],
                'dns_server_domain': dns_vals['server_domain'],
                'dns_server_ip': dns_vals['server_ip'],
            })

        if config.shinken_id:
            shinken_vals = self.pool.get('saas.container').get_vals(cr, uid, config.shinken_id.id, context=context)
            vals.update({
                'shinken_id': shinken_vals['container_id'],
                'shinken_fullname': shinken_vals['container_fullname'],
                'shinken_ssh_port': shinken_vals['container_ssh_port'],
                'shinken_server_id': shinken_vals['server_id'],
                'shinken_server_domain': shinken_vals['server_domain'],
                'shinken_server_ip': shinken_vals['server_ip'],
            })

        if config.bup_id:
            bup_vals = self.pool.get('saas.container').get_vals(cr, uid, config.bup_id.id, context=context)
            vals.update({
                'bup_id': bup_vals['container_id'],
                'bup_fullname': bup_vals['container_fullname'],
                'bup_ssh_port': bup_vals['container_ssh_port'],
                'bup_server_id': bup_vals['server_id'],
                'bup_server_domain': bup_vals['server_domain'],
                'bup_server_ip': bup_vals['server_ip'],
            })
        del context['from_config']

        now = datetime.now()
        vals.update({
            'config_conductor_path': config.conductor_path,
            'config_log_path': config.log_path,
            'config_archive_path': config.archive_path,
            'config_services_hostpath': config.services_hostpath,
            'config_backup_directory': config.backup_directory,
            'config_piwik_server': config.piwik_server,
            'config_piwik_password': config.piwik_password,
            'config_home_directory': config.home_directory,
            'config_ftpuser': config.ftpuser,
            'config_ftppass': config.ftppass,
            'config_ftpserver': config.ftpserver,
            'now_date': now.strftime("%Y-%m-%d"),
            'now_hour': now.strftime("%H-%M"),
            'now_bup': now.strftime("%Y-%m-%d-%H%M%S"),
        })
        return vals

    def reset_keys(self, cr, uid, ids, context={}):
        container_ids = container_obj.search(cr, uid, [], context=context)
        for container in container_obj.browse(cr, uid, container_ids, context=context):
            container_obj.reset_key(cr, uid, container.id, context=context)


    def reset_bup_key(self, cr, uid, ids, context={}):
        container_obj = self.pool.get('saas.container')
        server_obj = self.pool.get('saas.server')
        context.update({'saas-self': self, 'saas-cr': cr, 'saas-uid': uid})
        vals = self.get_vals(cr, uid, context=context)

        if not 'key_already_reset' in context:
            container_obj.reset_key(cr, uid, [vals['bup_id']], context=context)

        server_ids = server_obj.search(cr, uid, [], context=context)
        for server in server_obj.browse(cr, uid, server_ids, context=context):
            server_vals = server_obj.get_vals(cr, uid, server.id, context=context)
            ssh, sftp = execute.connect(server_vals['server_domain'], server_vals['server_ssh_port'], 'root', context)
            sftp.put(vals['config_home_directory'] + '/keys/' + vals['bup_fullname'], '/opt/keys/bup/bup_key')
            sftp.put(vals['config_home_directory'] + '/keys/' + vals['bup_fullname'] + '.pub', '/opt/keys/bup/bup_key.pub')
            execute.execute(ssh, ['rm /opt/keys/bup/config'], context)
            execute.execute(ssh, ['echo "Host bup-server" >> /opt/keys/bup/config'], context)
            execute.execute(ssh, ['echo "    Hostname ' + vals['bup_server_domain'] + '" >> /opt/keys/bup/config'], context)
            execute.execute(ssh, ['echo "    Port ' + vals['bup_ssh_port'] + '" >> /opt/keys/bup/config'], context)
            execute.execute(ssh, ['echo "    User bup" >> /opt/keys/bup/config'], context)
            execute.execute(ssh, ['echo "    IdentityFile /root/.ssh/bup_key" >> /opt/keys/bup/config'], context)
            execute.execute(ssh, ['chown -R root:root /opt/keys/bup'], context)
            execute.execute(ssh, ['chmod -R 700 /opt/keys/bup'], context)

            ssh.close()
            sftp.close()

    def cron_upload_save(self, cr, uid, ids, context={}):
        container_obj = self.pool.get('saas.container')
        context.update({'saas-self': self, 'saas-cr': cr, 'saas-uid': uid})

        container_ids = container_obj.search(cr, uid, [], context=context)
        context['container_save_comment'] = 'Save before upload_save'
        container_obj.save(cr, uid, container_ids, context=context)

        vals = self.get_vals(cr, uid, context=context)

        ssh, sftp = execute.connect(vals['bup_fullname'], username='bup', context=context)
        execute.execute(ssh, ['bup', 'fsck', '-g'], context)
        execute.execute(ssh, ['bup', 'fsck', '-r'], context)
        execute.execute(ssh, ['tar', 'czf', '/home/bup/bup.tar.gz', '-C', '/home/bup/.bup', '.'], context)
        execute.execute(ssh, ['/opt/upload', vals['config_ftpuser'], vals['config_ftppass'], vals['config_ftpserver']], context)
        execute.execute(ssh, ['rm', '/home/bup/bup.tar.gz'], context)
        ssh.close()
        sftp.close()


        ssh, sftp = execute.connect(vals['shinken_fullname'], context=context)
        execute.execute(ssh, ['rm', '-rf', '/opt/control-bup'], context)
        execute.execute(ssh, ['mkdir', '-p', '/opt/control-bup/bup'], context)
        execute.execute(ssh, ['ncftpget', '-u', vals['config_ftpuser'], '-p' + vals['config_ftppass'], vals['config_ftpserver'], '/opt/control-bup', '/bup.tar.gz'], context)
        execute.execute(ssh, ['tar', '-xf', '/opt/control-bup/bup.tar.gz', '-C', '/opt/control-bup/bup'], context)

        for container in container_obj.browse(cr, uid, container_ids, context=context):
            container_vals = container_obj.get_vals(cr, uid, container.id, context=context)
            execute.execute(ssh, ['export BUP_DIR=/opt/control-bup/bup; bup restore -C /opt/control-bup/restore/' + container_vals['container_fullname'] + ' ' + container_vals['saverepo_name'] + '/latest'], context)
        execute.execute(ssh, ['chown', '-R', 'shinken:shinken', '/opt/control-bup'], context)
        ssh.close()
        sftp.close()

    def cron_save(self, cr, uid, ids, context={}):

        config = self.pool.get('ir.model.data').get_object(cr, uid, 'saas', 'saas_settings')

        args = [
            config.openerp_path + '/saas/saas/shell/save.sh',
            'save_prepare',
            config.backup_directory,
            config.shinken_server,
        ]
        _logger.info('command %s', " ".join(args))
        proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        outfile = open(config.log_path + '/save.log', "w")
        for line in proc.stdout:
           _logger.info(line)
           outfile.write(line)

        instance_obj = self.pool.get('saas.service')
        instance_ids = instance_obj.search(cr, uid, [], context=context)
        instance_obj.save(cr, uid, instance_ids, type='auto', context=context)


        args = [
            config.openerp_path + '/saas/saas/shell/save.sh',
            'save_after',
            config.backup_directory,
            config.shinken_server,
            config.ftpuser,
            config.ftppass,
            config.ftpserver,
        ]
        _logger.info('command %s', " ".join(args))
        proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        outfile = open(config.log_path + '/save.log', "w")
        for line in proc.stdout:
           _logger.info(line)
           outfile.write(line)

        save_obj = self.pool.get('saas.save')
        old_date = datetime.now()-timedelta(days=5)
        save_ids = save_obj.search(cr, uid, [('create_date','<', old_date.strftime("%Y-%m-%d"))], context=context)
        save_obj.unlink(cr, uid, save_ids, context=context)

        return True
##########TODO : purge all log date_expiration < time
##########TODO : remove all saverepo date_expiration < time