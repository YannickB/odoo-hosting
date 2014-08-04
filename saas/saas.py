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
            if record and 'name' in record and record.name:
                res[log.id] = record.name
        return res

    _columns = {
        'model': fields.char('Related Document Model', size=128, select=1),
        'res_id': fields.integer('Related Document ID', select=1),
        'name': fields.function(_get_name, type="char", size=128, string='Name'),
        'action': fields.char('Action', size=64),
        'log': fields.text('log'),
        'state': fields.selection([('unfinished','Not finished'),('ok','Ok'),('ko','Ko')], 'State', required=True),
        'create_date': fields.datetime('Date'),
    }

    _defaults = {
        'state': 'unfinished'
    }

    _order = 'create_date desc'

    def unlink(self, cr, uid, ids, context=None):
        log_obj = self.pool.get('saas.log')
        log_ids = log_obj.search(cr, uid, [('model','=',self._name),('res_id','in',ids)],context=context)
        log_obj.unlink(cr, uid, log_ids, context=context)
        return super(saas_log, self).unlink(cr, uid, ids, context=context)

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
        log_id = log_obj.create(cr, uid, {'model': self._name, 'res_id': id, 'action': action}, context=context)
        if context == None:
            context = {}
        context['log_model'] = self._name
        context['log_res_id'] = id
        context['log_id'] = log_id
        context['log_log'] = ''
        return context

    def end_log(self, cr, uid, id, context=None):
        log_obj = self.pool.get('saas.log')
        if 'log_id' in  context:
            log = log_obj.browse(cr, uid, context['log_id'], context=context)
            if log.state == 'unfinished' and context['log_model'] == self._name and context['log_res_id'] == id:
                log_obj.write(cr, uid, [context['log_id']], {'state': 'ok'}, context=context)

class saas_image(osv.osv):
    _name = 'saas.image'

    _columns = {
        'name': fields.char('Image name', size=64, required=True),
        'application_id': fields.many2one('saas.application', 'Application', required=True),
        'current_version': fields.char('Current version', size=64, required=True),
        'dockerfile': fields.text('DockerFile'),
        'volume_ids': fields.one2many('saas.image.volume', 'image_id', 'Volumes'),
        'port_ids': fields.one2many('saas.image.port', 'image_id', 'Ports'),
        'version_ids': fields.one2many('saas.image.version','image_id', 'Versions'),
    }

    def get_vals(self, cr, uid, id, context=None):

        vals = {}

        image = self.browse(cr, uid, id, context=context)


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
    }


class saas_image_port(osv.osv):
    _name = 'saas.image.port'

    _columns = {
        'image_id': fields.many2one('saas.image', 'Image', ondelete="cascade", required=True),
        'name': fields.char('Name', size=64, required=True),
        'localport': fields.char('Local port', size=12, required=True),
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

    _columns = {
        'name': fields.char('Domain name', size=64, required=True)
    }


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
    }

    def get_vals(self, cr, uid, id, context=None):

        vals = {}

        apptype = self.browse(cr, uid, id, context=context)

        config = self.pool.get('ir.model.data').get_object(cr, uid, 'saas', 'saas_settings') 
        vals.update(self.pool.get('saas.config.settings').get_vals(cr, uid, context=context))

        vals.update({
            'apptype_name': apptype.name,
            'apptype_system_user': apptype.system_user,
            'apptype_admin_name': apptype.admin_name,
            'apptype_admin_email': apptype.admin_email,
            'apptype_mysql': apptype.mysql,
            'apptype_init_test': apptype.init_test
        })

        return vals


class saas_application(osv.osv):
    _name = 'saas.application'

    _columns = {
        'name': fields.char('Name', size=64, required=True),
        'code': fields.char('Code', size=4, required=True),
        'type_id': fields.many2one('saas.application.type', 'Type', required=True),
        'current_version': fields.char('Current version', size=64, required=True),
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
        'version_ids': fields.one2many('saas.application.version', 'application_id', 'Versions'),
        'buildfile': fields.text('Build File'),
    }

    def get_vals(self, cr, uid, id, context=None):

        vals = {}

        app = self.browse(cr, uid, id, context=context)

        vals.update(self.pool.get('saas.application.type').get_vals(cr, uid, app.type_id.id, context=context))

        now = datetime.now()
        computed_version = app.current_version + '.' + now.strftime('%Y%m%d.%H%M')

        vals.update({
            'app_name': app.name,
            'app_code': app.code,
            'app_instances_path': app.instances_path,
            'app_full_archivepath': vals['config_archive_path'] + '/' + app.type_id.name + '-' + app.code,
            'app_build_directory': app.build_directory,
            'app_poweruser_name': app.poweruser_name,
            'app_poweruser_password': app.poweruser_password,
            'app_poweruser_email': app.poweruser_email,
            'app_current_version': app.current_version,
            'app_computed_version': computed_version,
            'app_buildfile': app.buildfile
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
            'app_version_name': app_version.name,
            'app_version_full_archivepath': vals['app_full_archivepath'] + '/' + app_version.name,
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

class saas_server(osv.osv):
    _name = 'saas.server'

    _columns = {
        'name': fields.char('Domain name', size=64, required=True),
        'ip': fields.char('IP', size=64, required=True),
        'ssh_port': fields.char('SSH port', size=12, required=True),
        'mysql_passwd': fields.char('MySQL Passwd', size=64),
    }

    def get_vals(self, cr, uid, id, type='', context=None):

        server = self.browse(cr, uid, id, context=context)

        return {
            type + 'server_id': server.id,
            type + 'server_domain': server.name,
            type + 'server_ip': server.ip,
            type + 'server_ssh_port': int(server.ssh_port),
            type + 'server_mysql_passwd': server.mysql_passwd,
        }

class saas_container(osv.osv):
    _name = 'saas.container'
    _inherit = ['saas.log.model']

    _columns = {
        'name': fields.char('Name', size=64, required=True),
        'application_id': fields.many2one('saas.application', 'Application', required=True),
        'image_id': fields.many2one('saas.image', 'Image', required=True),
        'server_id': fields.many2one('saas.server', 'Server', required=True),
        'image_version_id': fields.many2one('saas.image.version', 'Image version', required=True),
        'port_ids': fields.one2many('saas.container.port', 'container_id', 'Ports')
    }

#########TODO add contraint, image_version doit appartenir à image_id qui doit correspondre à application_id

    def get_vals(self, cr, uid, id, context=None):

        vals = {}

        container = self.browse(cr, uid, id, context=context)

        vals.update(self.pool.get('saas.image.version').get_vals(cr, uid, container.image_version_id.id, context=context))
        vals.update(self.pool.get('saas.server').get_vals(cr, uid, container.server_id.id, context=context))

        ports = {}
        for port in container.port_ids:
            ports[port.name] = {'id': port.id, 'name': port.name, 'localport': port.localport, 'hostport': port.hostport}

        vals.update({
            'container_id': container.id,
            'container_name': container.name,
            'container_ports': ports
        })

        return vals


    def create(self, cr, uid, vals, context={}):
        if ('port_ids' not in vals or not vals['port_ids']) and 'image_version_id' in vals:
            vals['port_ids'] = []
            for port in self.pool.get('saas.image.version').browse(cr, uid, vals['image_version_id'], context=context).image_id.port_ids:
                vals['port_ids'].append((0,0,{'name':port.name,'localport':port.localport}))
        res = super(saas_container, self).create(cr, uid, vals, context=context)
        context = self.create_log(cr, uid, res, 'create', context)
        vals = self.get_vals(cr, uid, res, context=context)
        self.deploy(cr, uid, res, vals, context=context)
        self.end_log(cr, uid, res, context=context)
        return res

    def unlink(self, cr, uid, ids, context={}):
        for container in self.browse(cr, uid, ids, context=context):
            vals = self.get_vals(cr, uid, container.id, context=context)
            self.purge(cr, uid, container.id, vals, context=context)
        return super(saas_container, self).unlink(cr, uid, ids, context=context)


class saas_container_port(osv.osv):
    _name = 'saas.container.port'

    _columns = {
        'container_id': fields.many2one('saas.container', 'Container', ondelete="cascade", required=True),
        'name': fields.char('Name', size=64, required=True),
        'localport': fields.char('Local port', size=12, required=True),
        'hostport': fields.char('Host port', size=12),
    }

class saas_service(osv.osv):
    _name = 'saas.service'

    _columns = {
        'name': fields.char('Name', size=64, required=True),
        'application_id': fields.many2one('saas.application', 'Application', required=True),
        'application_version_id': fields.many2one('saas.application.version', 'Version', required=True),
        'bdd': fields.selection([('pgsql','PostgreSQL'),('mysql','MySQL')], 'BDD', required=True),
        'database_server_id': fields.many2one('saas.server', 'Database server', required=True),
        'database_password': fields.char('Database password', size=64, required=True),
        'container_id': fields.many2one('saas.container', 'Server', required=True),
        'port': fields.integer('Port'),
        'prod': fields.boolean('Prod?', readonly=True),
        'skip_analytics': fields.boolean('Skip Analytics?'),
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

        vals.update(self.pool.get('saas.application').get_vals(cr, uid, service.application_id.id, context=context))

        vals.update(self.pool.get('saas.server').get_vals(cr, uid, service.server_id.id, context=context))
        vals.update(self.pool.get('saas.server').get_vals(cr, uid, service.database_server_id.id, type='bdd_', context=context))

        vals.update({
            'service_name': service.name,
            'service_bdd': service.bdd,
            'service_db_user': service.name.replace('-','_'),
            'service_db_password': service.database_password,
            'service_port': service.port,
            'service_skip_analytics': service.skip_analytics,
            'service_version': service.version_many2one.name,
            'service_fullpath': vals['app_instances_path'] + '_' + service.name
        })

        return vals

    def create(self, cr, uid, vals, context={}):
        res = super(saas_instance, self).create(cr, uid, vals, context=context)

        config = self.pool.get('ir.model.data').get_object(cr, uid, 'saas', 'saas_settings')

        for instance in self.browse(cr, uid, [res], context=context):

            _logger.info('Deploying instance %s', instance.name)

            if 'build_name' in context:
                archive = instance.application_id.code + '-' + context['build_name']
            else:
                archive = 'versions/' + instance.version_many2one.name

            args = [
                config.openerp_path + '/saas/saas/shell/deploy.sh',
                'instance',
                instance.application_id.type_id.name,
                instance.application_id.code,
                instance.name,
                instance.application_id.instances_path,
                instance.bdd,
                instance.application_id.type_id.system_user,
                instance.server_id.name,
                instance.database_server_id.name,
                instance.database_password,
                archive,
                instance.application_id.archive_path,
                config.openerp_path,
                str(instance.port),
                instance.database_server_id.mysql_passwd
            ]

            _logger.info('command %s', " ".join(args))
            proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

            outfile = open(config.log_path + '/instance_' + instance.name + '.log', "w")
            for line in proc.stdout:
                _logger.info(line)
                outfile.write(line)

            _logger.info('If prod, dont forget to update the workers in conf')
        return res

    def write(self, cr, uid, ids, vals, context={}):

        for instance in self.browse(cr, uid, ids, context=context):

            if instance.prod and 'version_many2one' in vals and vals['version_many2one'] != instance.version_many2one:
                self.upgrade(cr, uid, [instance.id], vals['version_many2one'], context=context)

        return super(saas_instance, self).write(cr, uid, ids, vals, context=context)

    def unlink(self, cr, uid, ids, context=None):

        config = self.pool.get('ir.model.data').get_object(cr, uid, 'saas', 'saas_settings')

        for instance in self.browse(cr, uid, ids, context=context):

            _logger.info('Removing instance %s', instance.name)

            _logger.info('command : %s', config.openerp_path + '/saas/saas/shell/purge.sh ' + 'instance' + ' ' + instance.application_id.type_id.name  +  ' ' + instance.name + ' ' + instance.application_id.instances_path + ' ' + instance.bdd + ' ' + instance.application_id.type_id.system_user + ' ' + instance.server_id.name + ' ' + instance.database_server_id.name + ' ' + config.openerp_path)

            proc = subprocess.Popen([config.openerp_path + '/saas/saas/shell/purge.sh', 'instance', instance.application_id.type_id.name, instance.name, instance.application_id.instances_path, instance.bdd, instance.application_id.type_id.system_user, instance.server_id.name, instance.database_server_id.name, config.openerp_path, instance.database_server_id.mysql_passwd], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

            outfile = open(config.log_path + '/instance_' + instance.name + '.log', "w")
            for line in proc.stdout:
                _logger.info(line)
                outfile.write(line)

        return super(saas_instance, self).unlink(cr, uid, ids, context=context)
        
        
    def upgrade(self, cr, uid, ids, version_id, context=None):
    
        saas_obj = self.pool.get('saas.saas')

        config = self.pool.get('ir.model.data').get_object(cr, uid, 'saas', 'saas_settings')
        
        self.save(cr, uid, ids, type='preupgrade', context=context)

        version = self.pool.get('saas.version').browse(cr, uid, version_id, context=context).name

        for instance in self.browse(cr, uid, ids, context=context):

            _logger.info('Upgrading instance %s', instance.name)

            archive = instance.application_id.code + '-prod'
            if 'build_name' in context:
                archive = instance.application_id.code + '-' + context['build_name']

            args = [
                config.openerp_path + '/saas/saas/shell/upgrade.sh',
                instance.application_id.type_id.name,
                instance.application_id.code,
                instance.name,
                instance.application_id.type_id.system_user,
                instance.server_id.name,
                version,
                instance.application_id.instances_path,
                config.openerp_path,
                instance.application_id.archive_path,
            ]

            _logger.info('command %s', " ".join(args))
            proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

            outfile = open(config.log_path + '/instance_' + instance.name + '.log', "w")
            for line in proc.stdout:
                _logger.info(line)
                outfile.write(line)

            saas_ids = saas_obj.search(cr, uid, [('instance_id', '=', instance.id)], context=context)
            for saas in saas_obj.browse(cr, uid, saas_ids, context=context):
                args = [
                    config.openerp_path + '/saas/saas/apps/' + instance.application_id.type_id.name + '/upgrade.sh',
                    'upgrade_saas',
                    instance.application_id.code,
                    saas.name,
                    saas.domain_id.name,
                    instance.name,
                    instance.application_id.type_id.system_user,
                    instance.server_id.name,
                    str(instance.port),
                    instance.application_id.type_id.admin_name,
                    saas.admin_passwd,
                    instance.application_id.instances_path,
                ]

                _logger.info('command %s', " ".join(args))
                proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

                outfile = open(config.log_path + '/instance_' + instance.name + '.log', "w")
                for line in proc.stdout:
                    _logger.info(line)
                    outfile.write(line)

        return True

    def save(self, cr, uid, ids, saas_id=False, type='manual', context=None):

        saas_obj = self.pool.get('saas.saas')
        save_obj = self.pool.get('saas.save')
        config = self.pool.get('ir.model.data').get_object(cr, uid, 'saas', 'saas_settings')

        for instance in self.browse(cr, uid, ids, context=context):

            _logger.info('Saving instance %s', instance.name)



            saas_names = ''
            if saas_id:
                type_save = 'saas'
                saas_ids = [saas_id]
                for saas in saas_obj.browse(cr, uid, [saas_id], context=context):
                    saas_names = saas.name + '.' + saas.domain_id.name
            else:
                type_save = 'instance'
                saas_ids = saas_obj.search(cr, uid, [('instance_id', '=', instance.id)], context=context)
                for saas in saas_obj.browse(cr, uid, saas_ids, context=context):
                    if saas_names:
                        saas_names += ','
                    saas_names += saas.name + '.' + saas.domain_id.name


            filename = time.strftime("%Y-%m-%d")
            if type != 'auto':
                filename += time.strftime("-%H-%M")
            filename += '-' + instance.server_id.name.replace(".","-") + '-' + instance.name + '-' + type

            args = [
                config.openerp_path + '/saas/saas/shell/save.sh',
                'save_dump',
                instance.application_id.type_id.name,
                instance.application_id.code,
                saas_names,
                filename,
                instance.server_id.name,
                instance.database_server_id.name,
                instance.name,
                instance.application_id.type_id.system_user,
                config.backup_directory,
                instance.application_id.instances_path,
                config.openerp_path,
                config.ftpuser,
                config.ftppass,
                config.ftpserver
            ]
            _logger.info('command %s', " ".join(args))
            proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            outfile = open(config.log_path + '/save.log', "w")
            for line in proc.stdout:
               _logger.info(line)
               outfile.write(line)

            version = instance.prod and instance.version_many2one.name or False
            save_obj.create(cr, uid, {'name': filename, 'instance_id': instance.id, 'saas_ids': [(6, 0, saas_ids)], 'version': version}, context=context)

    def button_save(self, cr, uid, ids, context={}):
        self.save(cr, uid, ids, context=context)
        return True


class saas_base(osv.osv):
    _name = 'saas.base'

    _columns = {
        'name': fields.char('Name', size=64, required=True),
        'title': fields.char('Name', size=64, required=True),
        'domain_id': fields.many2one('saas.domain', 'Domain name', required=True),
        'service_ids': fields.many2many('saas.service', 'saas_base_service_rel', 'base_id', 'service_id', 'Services'),
        'admin_passwd': fields.char('Admin password', size=64),
        'poweruser_name': fields.char('PowerUser name', size=64),
        'poweruser_passwd': fields.char('PowerUser password', size=64),
        'poweruser_email': fields.char('PowerUser email', size=64),
        'build': fields.selection([
                 ('none','No action'),
                 ('build','Build'),
                 ('restore','Restore')],'Build?'),
        'test': fields.boolean('Test?'),
        'state': fields.selection([
                ('installing','Installing'),
                ('enabled','Enabled'),
                ('blocked','Blocked'),
                ('removing','Removing')],'State',readonly=True)
    }

    _defaults = {
      'build': 'restore',
      'admin_passwd': '#g00gle!',
      'poweruser_passwd': '#g00gle!'
    }

    _sql_constraints = [
        ('name_domain_uniq', 'unique (name,domain_id)', 'The name of the saas must be unique per domain !')
    ]

#########TODO La liaison entre base et service est un many2many à cause du loadbalancing. Si le many2many est vide, un service est créé automatiquement
#########Contrainte : L'application entre base et service doit être la même, de plus la bdd/host/db_user/db_password doit être la même entre tous les services d'une même base

    def get_vals(self, cr, uid, id, context=None):

        vals = {}

        base = self.browse(cr, uid, id, context=context)

        vals.update(self.pool.get('saas.service').get_vals(cr, uid, base.service_id.id, context=context))

        vals.update({
            'base_name': base.name,
            'base_title': base.title,
            'base_domain': base.domain_id.name,
            'base_admin_passwd': base.admin_passwd,
            'base_poweruser_name': base.poweruser_name,
            'base_poweruser_passwd': base.poweruser_passwd,
            'base_poweruser_email': base.poweruser_email,
            'base_build': base.build,
            'base_test': base.test,
        })

        return vals

    def create(self, cr, uid, vals, context=None):
        res = super(saas_saas, self).create(cr, uid, vals, context=context)

        config = self.pool.get('ir.model.data').get_object(cr, uid, 'saas', 'saas_settings')

        for saas in self.browse(cr, uid, [res], context=context):

            _logger.info('Deploying saas %s', saas.name)


            args = [
                config.openerp_path + '/saas/saas/shell/deploy.sh',
                'saas',
                saas.instance_id.application_id.type_id.name,
                saas.instance_id.application_id.code,
                saas.domain_id.name,
                saas.name,
                saas.title,
                saas.instance_id.application_id.type_id.system_user,
                saas.instance_id.server_id.name,
                saas.instance_id.database_server_id.name,
                saas.instance_id.bdd,
                saas.instance_id.database_password,
                saas.instance_id.name,
                str(saas.instance_id.port),
                saas.instance_id.application_id.type_id.admin_name,
                saas.admin_passwd,
                saas.instance_id.application_id.type_id.admin_email,
                saas.poweruser_name,
                saas.poweruser_passwd,
                saas.poweruser_email,
                saas.build,
                str(saas.test),
                str(saas.instance_id.skip_analytics),
                config.piwik_server,
                config.piwik_password,
                saas.instance_id.application_id.piwik_demo_id,
                saas.instance_id.application_id.instances_path,
                config.openerp_path,
                config.dns_server,
                config.shinken_server,
                config.backup_directory,
                saas.instance_id.database_server_id.mysql_passwd
            ]

            
            _logger.info('command %s', args)
            _logger.info('command %s', " ".join(args))

            proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

            outfile = open(config.log_path + '/saas_' + saas.domain_id.name + '_' + saas.name + '.log', "w")
            for line in proc.stdout:
               _logger.info(line)
               outfile.write(line)



        return res




    def unlink(self, cr, uid, ids, context=None):

        config = self.pool.get('ir.model.data').get_object(cr, uid, 'saas', 'saas_settings')

        for saas in self.browse(cr, uid, ids, context=context):

            _logger.info('Removing saas %s', saas.name)

            args = [
                config.openerp_path + '/saas/saas/shell/purge.sh',
                'saas',
                saas.instance_id.application_id.type_id.name,
                saas.instance_id.application_id.code,
                saas.domain_id.name,
                saas.name,
                saas.instance_id.application_id.type_id.system_user,
                saas.instance_id.server_id.name,
                saas.instance_id.database_server_id.name,
                saas.instance_id.bdd,
                config.piwik_server,
                config.piwik_password,
                saas.instance_id.application_id.instances_path,
                config.openerp_path,
                config.dns_server,
                config.shinken_server,
                saas.instance_id.database_server_id.mysql_passwd
            ]

            _logger.info('command %s', " ".join(args))

            proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

            outfile = open(config.log_path + '/saas_' + saas.domain_id.name + '_' + saas.name + '.log', "w")
            for line in proc.stdout:
               _logger.info(line)
               outfile.write(line)


        return super(saas_saas, self).unlink(cr, uid, ids, context=context)

    def button_save(self, cr, uid, ids, context={}):
        instance_obj = self.pool.get('saas.service')
        for saas in self.browse(cr, uid, ids, context=context):
            instance_obj.save(cr, uid, [saas.instance_id.id], saas_id=saas.id, context=context)
        return True

    def send_preprod(self, cr, uid, ids, context={}):

        config = self.pool.get('ir.model.data').get_object(cr, uid, 'saas', 'saas_settings')
        saas_obj = self.pool.get('saas.saas')

        for saas in self.browse(cr, uid, ids, context=context):

            new_saas = 'preprod' + saas.name

            saas_ids = saas_obj.search(cr, uid, [('name', '=', new_saas),('domain_id','=',saas.domain_id.id)], context=context)
            saas_obj.unlink(cr, uid, saas_ids, context=context)

            self.create(cr, uid, {
                'name': new_saas,
                'title': saas.title,
                'domain_id': saas.domain_id.id,
                'instance_id': saas.instance_id.application_id.preprod_instance_id.id,
                'poweruser_name': saas.poweruser_name,
                'poweruser_passwd': saas.poweruser_passwd,
                'poweruser_email': saas.poweruser_email,
                'build': 'none',
                'test': saas.test,
              }, context=context)

            _logger.info('moving saas %s', saas.name)

            args = [
                config.openerp_path + '/saas/saas/shell/move.sh',
                'move_saas',
                saas.instance_id.application_id.type_id.name,
                saas.instance_id.application_id.code,
                saas.name,
                saas.domain_id.name,
                saas.instance_id.name,
                saas.instance_id.server_id.name,
                saas.instance_id.application_id.type_id.system_user,
                saas.instance_id.database_server_id.name,
                new_saas,
                saas.domain_id.name,
                saas.instance_id.application_id.preprod_instance_id.name,
                saas.instance_id.application_id.preprod_instance_id.server_id.name,
                saas.instance_id.application_id.type_id.system_user,
                saas.instance_id.application_id.preprod_instance_id.database_server_id.name,
                saas.instance_id.application_id.instances_path,
                config.backup_directory,
                config.openerp_path,

            ]

            _logger.info('command %s', " ".join(args))

            proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

            outfile = open(config.log_path + '/send_preprod.log', "w")
            for line in proc.stdout:
               _logger.info(line)
               outfile.write(line)

            instance = saas.instance_id.application_id.preprod_instance_id
            args = [
                config.openerp_path + '/saas/saas/apps/' + instance.application_id.type_id.name + '/upgrade.sh',
                'upgrade_saas',
                instance.application_id.code,
                new_saas,
                saas.domain_id.name,
                instance.name,
                instance.application_id.type_id.system_user,
                instance.server_id.name,
                str(instance.port),
                instance.application_id.type_id.admin_name,
                saas.admin_passwd,
                instance.application_id.instances_path,
            ]

            _logger.info('command %s', " ".join(args))
            proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

            outfile = open(config.log_path + '/instance_' + instance.name + '.log', "w")
            for line in proc.stdout:
                _logger.info(line)
                outfile.write(line)



        return True

class saas_save(osv.osv):
    _name = 'saas.save'

    _columns = {
        'name': fields.char('Name', size=64, required=True),
        'saas_ids': fields.many2many('saas.saas', 'saas_saas_save_rel', 'save_id', 'saas_id', 'SaaS', readonly=True),
        'instance_id': fields.many2one('saas.service', 'Instance'),
        'application_id': fields.related('instance_id','application_id', type='many2one', relation='saas.application', string='Application'),
        'create_date': fields.datetime('Create Date'),
        'version': fields.char('Version', size=64),
        'restore_instance_id': fields.many2one('saas.service', 'Target instance for restore'),
        'restore_saas_ids': fields.many2many('saas.saas', 'saas_saas_save_restore_rel', 'save_id', 'saas_id', 'SaaS to restore'),
        'restore_prefix': fields.char('Restore prefix (optional)', size=64),
    }

    _order = 'create_date desc'


    def unlink(self, cr, uid, ids, context=None):

        config = self.pool.get('ir.model.data').get_object(cr, uid, 'saas', 'saas_settings')

        for save in self.browse(cr, uid, ids, context=context):

            _logger.info('Removing save %s', save.name)

            args = [
                config.openerp_path + '/saas/saas/shell/save.sh',
                'save_remove',
                save.name,
                config.backup_directory,
                config.shinken_server,
                config.ftpuser,
                config.ftppass,
                config.ftpserver
            ]

            _logger.info('command %s', " ".join(args))

            proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

            outfile = open(config.log_path + '/save_remove.log', "w")
            for line in proc.stdout:
               _logger.info(line)
               outfile.write(line)

        return super(saas_save, self).unlink(cr, uid, ids, context=context)

    def restore(self, cr, uid, ids, context={}):

        config = self.pool.get('ir.model.data').get_object(cr, uid, 'saas', 'saas_settings')

        saas_obj = self.pool.get('saas.saas')
        instance_obj = self.pool.get('saas.service')

        for save in self.browse(cr, uid, ids, context=context):
            if not save.restore_instance_id:
                raise osv.except_osv(_('Error!'),_("You need to specify a the target instance!"))

            for saas in save.restore_saas_ids:

                instance_obj.save(cr, uid, [saas.instance_id.id], saas_id=saas.id, type='prerestore', context=context)

                from_saas_name = saas.name
                to_saas_name = save.restore_prefix and save.restore_prefix + from_saas_name or from_saas_name
                domain = saas.domain_id.name
                instance = save.restore_instance_id

                vals = {
                  'name': to_saas_name,
                  'title': saas.title,
                  'domain_id': saas.domain_id.id,
                  'instance_id': instance.id,
                  'poweruser_name': saas.poweruser_name,
                  'poweruser_passwd': saas.poweruser_passwd,
                  'poweruser_email': saas.poweruser_email,
                  'build': 'none',
                  'test': saas.test,
                }

                save_ids = []
                if not save.restore_prefix:
                    save_ids = self.search(cr, uid, [('saas_ids','in',saas.id)], context=context)
                    saas_obj.unlink(cr, uid, [saas.id], context=context)

                saas_id = saas_obj.create(cr, uid, vals, context=context)

                if save_ids:
                    self.write(cr, uid, save_ids, {'saas_ids': [(4, saas_id)]}, context=context)
                    self.write(cr, uid, [save.id], {'restore_saas_ids': [(4, saas_id)]}, context=context)

                args = [
                    config.openerp_path + '/saas/saas/shell/restore.sh',
                    'restore_saas',
                    instance.application_id.type_id.name,
                    instance.application_id.code,
                    from_saas_name,
                    to_saas_name,
                    domain,
                    instance.name,
                    instance.server_id.name,
                    instance.application_id.type_id.system_user,
                    instance.database_server_id.name,
                    save.name, 
                    instance.application_id.instances_path,
                    config.backup_directory,
                    config.shinken_server,
                    config.openerp_path,
                    config.ftpuser,
                    config.ftppass,
                    config.ftpserver
                ]

                _logger.info('command %s', " ".join(args))

                proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

                outfile = open(config.log_path + '/restore.log', "w")
                for line in proc.stdout:
                   _logger.info(line)
                   outfile.write(line)

                version = instance.prod and instance.version_many2one.name or False
                if save.version != version:
                    args = [
                        config.openerp_path + '/saas/saas/apps/' + instance.application_id.type_id.name + '/upgrade.sh',
                        'upgrade_saas',
                        instance.application_id.code,
                        to_saas.name,
                        domain,
                        instance.name,
                        instance.application_id.type_id.system_user,
                        instance.server_id.name,
                        instance.port,
                        instance.application_id.type_id.admin_name,
                        to_saas.admin_password,
                        instance.application_id.instances_path,
                    ]

                    _logger.info('command %s', " ".join(args))
                    proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

                    outfile = open(config.log_path + '/instance_' + instance.name + '.log', "w")
                    for line in proc.stdout:
                        _logger.info(line)
                        outfile.write(line)


        return True


class saas_config_settings(osv.osv):
    _name = 'saas.config.settings'
    _description = 'SaaS configuration'

    _columns = {
        'openerp_path': fields.char('OpenERP Path', size=128),
        'log_path': fields.char('SaaS Log Path', size=128),
        'archive_path': fields.char('Archive path', size=128),
        'backup_directory': fields.char('Backup directory', size=128),
        'piwik_server': fields.char('Piwik server', size=128),
        'piwik_password': fields.char('Piwik Password', size=128),
        'dns_server': fields.char('DNS Server', size=128),
        'shinken_server': fields.char('Shinken Server', size=128),
        'ftpuser': fields.char('FTP User', size=64),
        'ftppass': fields.char('FTP Pass', size=64),
        'ftpserver': fields.char('FTP Server', size=64),
    }

    def get_vals(self, cr, uid, context=None):
        config = self.pool.get('ir.model.data').get_object(cr, uid, 'saas', 'saas_settings')
        return {
            'config_openerp_path': config.openerp_path,
            'config_log_path': config.log_path,
            'config_archive_path': config.archive_path,
            'config_backup_directory': config.backup_directory,
            'config_piwik_server': config.piwik_server,
            'config_piwik_password': config.piwik_password,
            'config_dns_server': config.dns_server,
            'config_shinken_server': config.shinken_server,
            'config_ftpuser': config.ftpuser,
            'config_ftppass': config.ftppass,
            'config_ftpserver': config.ftpserver,
        }


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
##########TODO : purge all log > X days