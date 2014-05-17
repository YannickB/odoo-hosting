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
    }

class saas_application(osv.osv):
    _name = 'saas.application'

    _columns = {
        'name': fields.char('Name', size=64, required=True),
        'code': fields.char('Code', size=4, required=True),
        'type_id': fields.many2one('saas.application.type', 'Type', required=True),
        'next_instance_id': fields.many2one('saas.instance', 'Next instance'),
        'demo_saas_id': fields.many2one('saas.saas', 'Demo SaaS'),
        'preprod_domain_id': fields.many2one('saas.domain', 'Preprod Domain'),
        'preprod_server_id': fields.many2one('saas.server', 'Preprod server'),
        'preprod_bdd_server_id': fields.many2one('saas.server', 'Preprod database server'),
        'preprod_port': fields.integer('Port preprod'),
        'preprod_instance_id': fields.many2one('saas.instance', 'Instance preprod'),
        'preprod_mysql_instance_id': fields.many2one('saas.instance', 'Instance preprod mysql'),
        'test_port': fields.integer('Port test'),
        'test_instance_id': fields.many2one('saas.instance', 'Instance test'),
        'test_mysql_instance_id': fields.many2one('saas.instance', 'Instance test mysql'),
        'dev_port': fields.integer('Port dev'),
        'dev_instance_id': fields.many2one('saas.instance', 'Instance dev'),
        'dev_mysql_instance_id': fields.many2one('saas.instance', 'Instance dev mysql'),
        'instances_path': fields.char('Instances path', size=128),
        'archive_path': fields.char('Archive path', size=128),
        'build_directory': fields.char('Build directory', size=128),
        'poweruser_name': fields.char('PowerUser Name', size=64),
        'poweruser_password': fields.char('PowerUser Password', size=64),
        'poweruser_email': fields.char('PowerUser Email', size=64),
        'piwik_demo_id': fields.char('Piwik Demo ID', size=64),
        'version_prod': fields.char('Version Prod', size=64),
        'version_preprod': fields.char('Version Preprod', size=64),
        'version_test': fields.char('Version Test', size=64),
        'version_dev': fields.char('Version Dev', size=64),
    }

    def build(self, cr, uid, ids, context={}):

        saas_obj = self.pool.get('saas.saas')
        instance_obj = self.pool.get('saas.instance')

        config = self.pool.get('ir.model.data').get_object(cr, uid, 'saas', 'saas_settings')
        name = context['build_name']

        for app in self.browse(cr, uid, ids, context=context):

            _logger.info('Rebuilding %s', name)

            if context['build']:
                args = [
                    config.openerp_path + '/saas/saas/shell/build.sh',
                    'build_archive',
                    app.type_id.name,
                    app.code,
                    name,
                    app.type_id.system_user,
                    app.archive_path,
                    config.openerp_path,
                    app.build_directory
                ]
                _logger.info('command %s', " ".join(args))
                proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                outfile = open(config.log_path + '/build_' + name + '.log', "w")
                for line in proc.stdout:
                   _logger.info(line)
                   outfile.write(line)
            else:
                args = [
                    config.openerp_path + '/saas/saas/shell/build.sh',
                    'build_copy',
                    app.type_id.name,
                    app.code,
                    name,
                    context['build_source'],
                    config.openerp_path,
                    app.archive_path,
                ]
                _logger.info('command %s', " ".join(args))
                proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                outfile = open(config.log_path + '/build_' + name + '.log', "w")
                for line in proc.stdout:
                   _logger.info(line)
                   outfile.write(line)


            instance_ids = instance_obj.search(cr, uid, [('name','in',[app.code + '-' + name, app.code + '-' + name + '-my']), ('application_id', '=', app.id)], context=context)
            saas_ids = saas_obj.search(cr, uid, [('instance_id', 'in', instance_ids)], context=context)
            saas_obj.unlink(cr, uid, saas_ids, context=context)
            instance_obj.unlink(cr, uid, instance_ids, context=context)

            instance_id = instance_obj.create(cr, uid, {
                'name': app.code + '-' + name,
                'application_id': app.id,
                'bdd': 'pgsql',
                'server_id': app.preprod_server_id.id,
                'database_server_id': app.preprod_bdd_server_id.id,
                'port': getattr(app, name + '_port'),
                'skip_analytics': True
              }, context=context)
            self.write(cr, uid, [app.id], {name + '_instance_id': instance_id}, context=context)
            saas_obj.create(cr, uid, {
                'name': name,
                'title': 'Test',
                'domain_id': app.preprod_domain_id.id,
                'instance_id': instance_id,
                'poweruser_name': app.type_id.admin_name,
                'poweruser_passwd': app.poweruser_password,
                'poweruser_email': app.poweruser_email,
                'build': True,
                'test': app.type_id.init_test,
              }, context=context)

            if context['build']:
                args = [
                    config.openerp_path + '/saas/saas/shell/build.sh',
                    'build_dump',
                    app.type_id.name,
                    app.code,
                    name,
                    app.preprod_domain_id.name,
                    app.code + '-' + name,
                    app.type_id.system_user,
                    app.preprod_server_id.name,
                    app.preprod_bdd_server_id.name,
                    'pgsql',
                    config.openerp_path,
                    app.archive_path,
                    app.instances_path,
                    app.preprod_bdd_server_id.mysql_passwd
                ]
                _logger.info('command %s', " ".join(args))
                proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                outfile = open(config.log_path + '/build_' + name + '.log', "w")
                for line in proc.stdout:
                   _logger.info(line)
                   outfile.write(line)

            if app.type_id.mysql:
              instance_id = instance_obj.create(cr, uid, {
                  'name': app.code + '-' + name + '-my',
                  'application_id': app.id,
                  'bdd': 'mysql',
                  'server_id': app.preprod_server_id.id,
                  'database_server_id': app.preprod_bdd_server_id.id,
                  'port': getattr(app, name + '_port'),
                  'skip_analytics': True
                }, context=context)
              self.write(cr, uid, [app.id], {name + '_mysql_instance_id': instance_id}, context=context)
              saas_obj.create(cr, uid, {
                  'name': name + '-my',
                  'title': 'Test',
                  'domain_id': app.preprod_domain_id.id,
                  'instance_id': instance_id,
                  'poweruser_name': app.type_id.admin_name,
                  'poweruser_passwd': app.poweruser_password,
                  'poweruser_email': app.poweruser_email,
                  'build': True,
                  'test': app.type_id.init_test,
                }, context=context)

              _logger.info('system_user %s', app.type_id.system_user)
              _logger.info('bdd_server %s', app.preprod_bdd_server_id.name)
              if context['build']:
                  args = [
                      config.openerp_path + '/saas/saas/shell/build.sh',
                      'build_dump',
                      app.type_id.name,
                      app.code,
                      name + '-my',
                      app.preprod_domain_id.name,
                      app.code + '-' + name + '-my',
                      app.type_id.system_user,
                      app.preprod_server_id.name,
                      app.preprod_bdd_server_id.name,
                      'mysql',
                      config.openerp_path,
                      app.archive_path,
                      app.instances_path,
                      app.preprod_bdd_server_id.mysql_passwd
                  ]
                  _logger.info('command %s', " ".join(args))
                  proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                  outfile = open(config.log_path + '/build_' + name + '.log', "w")
                  for line in proc.stdout:
                     _logger.info(line)
                     outfile.write(line)


            #Get Version
            version = ''
            args = [
                config.openerp_path + '/saas/saas/shell/build.sh',
                'get_version',
                app.type_id.name,
                app.code,
                name,
                app.preprod_domain_id.name,
                config.openerp_path,
                app.instances_path,
                app.archive_path,
            ]
            _logger.info('command %s', " ".join(args))
            proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            outfile = open(config.log_path + '/build_' + name + '.log', "w")
            for line in proc.stdout:
               _logger.info(line)
               outfile.write(line)
            with open(app.archive_path  + '/' + app.code + '-' + name + '/VERSION.txt') as f:
                version = f.read()
                _logger.info('version : %s', version)
                self.write(cr, uid, [app.id], {'version_' + name: version}, context=context)


            if context['build']:
                #Build after
                args = [
                    config.openerp_path + '/saas/saas/shell/build.sh',
                    'build_after',
                    app.type_id.name,
                    app.code,
                    name,
                    version,
                    config.openerp_path,
                    app.archive_path,
                ]
                _logger.info('command %s', " ".join(args))
                proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                outfile = open(config.log_path + '/build_' + name + '.log', "w")
                for line in proc.stdout:
                   _logger.info(line)
                   outfile.write(line)

               
            args = [
                config.openerp_path + '/saas/saas/apps/' + app.type_id.name + '/deploy.sh',
                'create_poweruser',
                app.code,
                app.preprod_domain_id.name,
                name,
                app.type_id.system_user,
                app.preprod_server_id.name,
                app.poweruser_name,
                app.poweruser_password,
                app.poweruser_email,
                app.instances_path,
            ]
            _logger.info('command %s', " ".join(args))
            proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            outfile = open(config.log_path + '/build_' + name + '.log', "w")
            for line in proc.stdout:
               _logger.info(line)
               outfile.write(line)
               
            if not app.type_id.init_test :
                args = [
                    config.openerp_path + '/saas/saas/apps/' + app.type_id.name + '/deploy.sh',
                    'test_specific',
                    app.code,
                    app.preprod_domain_id.name,
                    name,
                    app.type_id.system_user,
                    app.preprod_server_id.name,
                    app.poweruser_name,
                    app.instances_path,
                ]
                _logger.info('command %s', " ".join(args))
                proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                outfile = open(config.log_path + '/build_' + name + '.log', "w")
                for line in proc.stdout:
                   _logger.info(line)
                   outfile.write(line)

            if app.type_id.mysql:
              args = [
                  config.openerp_path + '/saas/saas/apps/' + app.type_id.name + '/deploy.sh',
                  'create_poweruser',
                  app.code,
                  app.preprod_domain_id.name,
                  name + '-my',
                  app.type_id.system_user,
                  app.preprod_server_id.name,
                  app.poweruser_name,
                  app.poweruser_password,
                  app.poweruser_email,
                  app.instances_path,
              ]
              _logger.info('command %s', " ".join(args))
              proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
              outfile = open(config.log_path + '/build_' + name + '.log', "w")
              for line in proc.stdout:
                 _logger.info(line)
                 outfile.write(line)
                 
              if not app.type_id.init_test:
                  args = [
                      config.openerp_path + '/saas/saas/apps/' + app.type_id.name + '/deploy.sh',
                      'test_specific',
                      app.code,
                      app.preprod_domain_id.name,
                      name + '-my',
                      app.type_id.system_user,
                      app.preprod_server_id.name,
                      app.poweruser_name,
                      app.instances_path,
                  ]
                  _logger.info('command %s', " ".join(args))
                  proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                  outfile = open(config.log_path + '/build_' + name + '.log', "w")
                  for line in proc.stdout:
                     _logger.info(line)
                     outfile.write(line)
        return True
        
        
        
    def populate(self, cr, uid, ids, context={}):
    
        instance_obj = self.pool.get('saas.instance')
        
        config = self.pool.get('ir.model.data').get_object(cr, uid, 'saas', 'saas_settings')


        for app in self.browse(cr, uid, ids, context=context):
            preprod_archive = app.code + '-preprod'
            prod_archive = app.code + '-prod'
            args = [
                config.openerp_path + '/saas/saas/shell/populate.sh',
                app.code,
                preprod_archive,
                prod_archive,
                app.archive_path,
            ]
            _logger.info('command %s', " ".join(args))
            proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            outfile = open(config.log_path + '/populate.log', "w")
            for line in proc.stdout:
               _logger.info(line)
               outfile.write(line)
               
               
            with open(app.archive_path  + '/' + prod_archive + '/VERSION.txt') as f:
                version = f.read()
                _logger.info('version : %s', version)
                self.write(cr, uid, [app.id], {'version_prod': version}, context=context)
        return True
            
    def refresh_demo(self, cr, uid, ids, context={}):
    
        saas_obj = self.pool.get('saas.saas')
    
        for app in self.browse(cr, uid, ids, context=context):
            if app.demo_saas_id:
                saas_obj.unlink(cr, uid, [app.demo_saas_id.id], context=context)
            
            demo_id = saas_obj.create(cr, uid, {
              'name': 'demo',
              'title': 'Demo',
              'domain_id': app.preprod_domain_id.id,
              'instance_id': app.next_instance_id.id,
              'poweruser_name': app.poweruser_name,
              'poweruser_passwd': app.poweruser_password,
              'poweruser_email': app.poweruser_email,
              'build': True,
              'test': True,
            }, context=context)
            
            self.write(cr, uid, [app.id], {'demo_saas_id': demo_id}, context=context)
        return True

class saas_server(osv.osv):
    _name = 'saas.server'

    _columns = {
        'name': fields.char('Domain name', size=64, required=True),
        'ip': fields.char('IP', size=64, required=True),
        'mysql_passwd': fields.char('MySQL Passwd', size=64),
    }

class saas_instance(osv.osv):
    _name = 'saas.instance'

    _columns = {
        'name': fields.char('Name', size=64, required=True),
        'application_id': fields.many2one('saas.application', 'Application', required=True),
        'bdd': fields.selection([('pgsql','PostgreSQL'),('mysql','MySQL')], 'BDD', required=True),
        'server_id': fields.many2one('saas.server', 'Server', required=True),
        'database_server_id': fields.many2one('saas.server', 'Database server', required=True),
        'database_password': fields.char('Database password', size=64, required=True),
        'port': fields.integer('Port'),
        'version': fields.char('Version', size=64),
        'skip_analytics': fields.boolean('Skip Analytics?'),
    }

    _defaults = {
      'database_password': '#g00gle!'
    }

    def create(self, cr, uid, vals, context={}):
        res = super(saas_instance, self).create(cr, uid, vals, context=context)

        config = self.pool.get('ir.model.data').get_object(cr, uid, 'saas', 'saas_settings')

        for instance in self.browse(cr, uid, [res], context=context):

            _logger.info('Deploying instance %s', instance.name)

            archive = instance.application_id.code + '-prod'
            if 'build_name' in context:
                archive = instance.application_id.code + '-' + context['build_name']

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

            with open(instance.application_id.archive_path  + '/' + archive + '/VERSION.txt') as f:
                self.write(cr, uid, [instance.id], {'version': f.read()}, context=context)


        return res

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
        
        
    def upgrade(self, cr, uid, ids, context=None):
    

        config = self.pool.get('ir.model.data').get_object(cr, uid, 'saas', 'saas_settings')
        
        self.save(cr, uid, ids, type='preupgrade', context=context)

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
                archive,
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

            with open(instance.application_id.archive_path  + '/' + archive + '/VERSION.txt') as f:
                self.write(cr, uid, [instance.id], {'version': f.read()}, context=context)
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
            filename += '-' + instance.server_id.name.replace(".","-") + '-' + instance.name + '-' + type + '.tar.gz'

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

            save_obj.create(cr, uid, {'name': filename, 'type': type_save, 'instance_id': instance.id, 'saas_id': saas_id}, context=context)

    def button_save(self, cr, uid, ids, context={}):
        self.save(cr, uid, ids, context=context)
        return True


class saas_saas(osv.osv):
    _name = 'saas.saas'

    _columns = {
        'name': fields.char('Name', size=64, required=True),
        'title': fields.char('Name', size=64, required=True),
        'domain_id': fields.many2one('saas.domain', 'Domain name', required=True),
        'instance_id': fields.many2one('saas.instance', 'Instance', required=True),
        'admin_passwd': fields.char('Admin password', size=64),
        'poweruser_name': fields.char('PowerUser name', size=64),
        'poweruser_passwd': fields.char('PowerUser password', size=64),
        'poweruser_email': fields.char('PowerUser email', size=64),
        'build': fields.boolean('Build?'),
        'test': fields.boolean('Test?'),
        'state': fields.selection([
                ('installing','Installing'),
                ('enabled','Enabled'),
                ('blocked','Blocked'),
                ('removing','Removing')],'State',readonly=True)
    }

    _defaults = {
      'admin_passwd': '#g00gle!',
      'poweruser_passwd': '#g00gle!'
    }

    _sql_constraints = [
        ('name_domain_uniq', 'unique (name,domain_id)', 'The name of the saas must be unique per domain !')
    ]

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
                str(saas.build),
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
        instance_obj = self.pool.get('saas.instance')
        for saas in self.browse(cr, uid, ids, context=context):
            self.pool.get('saas.config.settings').cron_save(cr, uid, context=context)
#            instance_obj.save(cr, uid, [saas.instance_id.id], saas_id=saas.id, context=context)
        return True

class saas_save(osv.osv):
    _name = 'saas.save'

    _columns = {
        'name': fields.char('Name', size=64, required=True),
        'type': fields.selection([
                ('instance','Instance'),
                ('saas','SaaS')],'Type'),
        'saas_id': fields.many2one('saas.saas', 'SaaS'),
        'instance_id': fields.many2one('saas.instance', 'Instance'),
        'create_date': fields.datetime('Create Date'),
    }

    _order = 'create_date desc'

class saas_config_settings(osv.osv):
    _name = 'saas.config.settings'
    _description = 'SaaS configuration'

    _columns = {
        'openerp_path': fields.char('OpenERP Path', size=128),
        'log_path': fields.char('SaaS Log Path', size=128),
        'backup_directory': fields.char('Backup directory', size=128),
        'piwik_server': fields.char('Piwik server', size=128),
        'piwik_password': fields.char('Piwik Password', size=128),
        'dns_server': fields.char('DNS Server', size=128),
        'shinken_server': fields.char('Shinken Server', size=128),
        'ftpuser': fields.char('FTP User', size=64),
        'ftppass': fields.char('FTP Pass', size=64),
        'ftpserver': fields.char('FTP Server', size=64),
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

        instance_obj = self.pool.get('saas.instance')
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
