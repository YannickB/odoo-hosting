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
import erppeek

import logging
_logger = logging.getLogger(__name__)


# class saas_container(osv.osv):
#     _inherit = 'saas.container'
#     def add_links(self, cr, uid, vals, context={}):
#         res = super(saas_container, self).add_links(cr, uid, vals, context=context)
#         if 'application_id' in vals and 'server_id' in vals:
#             application = self.pool.get('saas.application').browse(cr, uid, vals['application_id'], context=context)
#             if application.type_id.name == 'odoo':
#                 if not 'linked_container_ids' in vals:
#                     vals['linked_container_ids'] = []
#                 container_ids = self.search(cr, uid, [('application_id.type_id.name','=','postgres'),('server_id','=',vals['server_id'])], context=context)
#                 for container in self.browse(cr, uid, container_ids, context=context):
#                     vals['linked_container_ids'].append((4,container.id))
#         return vals

class saas_service(osv.osv):
    _inherit = 'saas.service'



    def deploy_post_service(self, cr, uid, vals, context):
        super(saas_service, self).deploy_post_service(cr, uid, vals, context)
        context.update({'saas-self': self, 'saas-cr': cr, 'saas-uid': uid})
        if vals['apptype_name'] == 'drupal':
            ssh, sftp = execute.connect(vals['container_fullname'], username=vals['apptype_system_user'], context=context)
            execute.execute(ssh, ['cp', '-R', vals['service_full_localpath_files'] + '/sites-template', vals['service_full_localpath'] + '/sites'], context)
            ssh.close()
            sftp.close()

        return


class saas_base(osv.osv):
    _inherit = 'saas.base'

    def deploy_build(self, cr, uid, vals, context=None):
        res = super(saas_base, self).deploy_build(cr, uid, vals, context)
        context.update({'saas-self': self, 'saas-cr': cr, 'saas-uid': uid})
        if vals['apptype_name'] == 'drupal':

            ssh, sftp = execute.connect(vals['container_fullname'], context=context)
            config_file = '/etc/nginx/sites-available/' + vals['base_fullname']
            sftp.put(vals['config_conductor_path'] + '/saas/saas_drupal/res/nginx.config', config_file)
            execute.execute(ssh, ['sed', '-i', '"s/BASE/' + vals['base_name'] + '/g"', config_file], context)
            execute.execute(ssh, ['sed', '-i', '"s/DOMAIN/' + vals['domain_name'] + '/g"', config_file], context)
            execute.execute(ssh, ['sed', '-i', '"s/PATH/' + vals['service_full_localpath_files'].replace('/','\/') + '/g"', config_file], context)
            execute.execute(ssh, ['ln', '-s',  '/etc/nginx/sites-available/' + vals['base_fullname'],  '/etc/nginx/sites-enabled/' + vals['base_fullname']], context)
            execute.execute(ssh, ['/etc/init.d/nginx','reload'], context)
            ssh.close()
            sftp.close()
            #
            ssh, sftp = execute.connect(vals['container_fullname'], username=vals['apptype_system_user'], context=context)
            execute.execute(ssh, ['drush', '-y', 'si',
                                  '--db-url=' + vals['database_type'] + '://' + vals['service_db_user'] + ':' + vals['service_db_password'] + '@' + vals['database_server'] + '/' + vals['base_unique_name_'],
                                  '--account-mail=' + vals['apptype_admin_email'],
                                  '--account-name=' + vals['apptype_admin_name'],
                                  '--account-pass=' + vals['base_admin_passwd'],
                                  '--sites-subdir=' + vals['base_fulldomain'],
                                  'minimal'], context, path=vals['service_full_localpath_files'])

            if vals['app_options']['install_modules']['value']:
                modules = vals['app_options']['install_modules']['value'].split(',')
                for module in modules:
                    execute.execute(ssh, ['drush', '-y', 'en', module], context, path=vals['service_full_localpath_files'] + '/sites/' + vals['base_fulldomain'])
            if vals['app_options']['theme']['value']:
                theme = vals['app_options']['theme']['value']
                execute.execute(ssh, ['drush', '-y', 'pm-enable', theme],context, path=vals['service_full_localpath_files'] + '/sites/' + vals['base_fulldomain'])
                execute.execute(ssh, ['drush', 'vset', '--yes', '--exact', 'theme_default', theme],context, path=vals['service_full_localpath_files'] + '/sites/' + vals['base_fulldomain'])
            ssh.close()
            sftp.close()


  # drush vset --yes --exact bakery_master $bakery_master_site
  # drush vset --yes --exact bakery_key '$bakery_private_key'
  # drush vset --yes --exact bakery_domain $bakery_cookie_domain

        return res

# post restore
#     ssh $system_user@$server << EOF
#       mkdir $instances_path/$instance/sites/$saas.$domain
#       cp -r $instances_path/$instance/$db_type/sites/* $instances_path/$instance/sites/$saas.$domain/
#       cd $instances_path/$instance/sites/$saas.$domain
#       sed -i "s/'database' => '[#a-z0-9_!]*'/'database' => '$unique_name_underscore'/g" $instances_path/$instance/sites/$saas.$domain/settings.php
#       sed -i "s/'username' => '[#a-z0-9_!]*'/'username' => '$db_user'/g" $instances_path/$instance/sites/$saas.$domain/settings.php
#       sed -i "s/'password' => '[#a-z0-9_!]*'/'password' => '$database_passwpord'/g" $instances_path/$instance/sites/$saas.$domain/settings.php
#       sed -i "s/'host' => '[0-9.]*'/'host' => '$database_server'/g" $instances_path/$instance/sites/$saas.$domain/settings.php
#       pwd
#       echo Title $title
#       drush vset --yes --exact site_name $title
#       drush user-password $admin_user --password=$admin_password
# EOF
#


    def deploy_post(self, cr, uid, vals, context=None):
        res = super(saas_base, self).deploy_post(cr, uid, vals, context)
        context.update({'saas-self': self, 'saas-cr': cr, 'saas-uid': uid})
        if vals['apptype_name'] == 'drupal':
            ssh, sftp = execute.connect(vals['container_fullname'], username=vals['apptype_system_user'], context=context)
            execute.execute(ssh, ['drush', 'vset', '--yes', '--exact', 'site_name', vals['base_title']], context, path=vals['service_full_localpath_files'] + '/sites/' + vals['base_fulldomain'])
            ssh.close()
            sftp.close()

    def deploy_create_poweruser(self, cr, uid, vals, context=None):
        res = super(saas_base, self).deploy_create_poweruser(cr, uid, vals, context)
        context.update({'saas-self': self, 'saas-cr': cr, 'saas-uid': uid})
        if vals['apptype_name'] == 'drupal':

            ssh, sftp = execute.connect(vals['container_fullname'], username=vals['apptype_system_user'], context=context)
            execute.execute(ssh, ['drush', 'user-create',  vals['base_poweruser_name'],  '--password=' + vals['base_poweruser_password'], '--mail=' + vals['base_poweruser_email']], context, path=vals['service_full_localpath_files'] + '/sites/' + vals['base_fulldomain'])
            if vals['app_options']['poweruser_group']['value']:
                execute.execute(ssh, ['drush', 'user-add-role', vals['app_options']['poweruser_group']['value'], vals['base_poweruser_name']], context, path=vals['service_full_localpath_files'] + '/sites/' + vals['base_fulldomain'])
            ssh.close()
            sftp.close()

        return res


    def deploy_test(self, cr, uid, vals, context=None):
        res = super(saas_base, self).deploy_test(cr, uid, vals, context)
        context.update({'saas-self': self, 'saas-cr': cr, 'saas-uid': uid})
        if vals['apptype_name'] == 'drupal':
            ssh, sftp = execute.connect(vals['container_fullname'], username=vals['apptype_system_user'], context=context)
            execute.execute(ssh, ['drush', 'vset', '--yes', '--exact', 'wikicompare_test_platform', '1'],context, path=vals['service_full_localpath_files'] + '/sites/' + vals['base_fulldomain'])
            if vals['app_options']['test_install_modules']['value']:
                modules = vals['app_options']['test_install_modules']['value'].split(',')
                for module in modules:
                    execute.execute(ssh, ['drush', '-y', 'en', module], context, path=vals['service_full_localpath_files'] + '/sites/' + vals['base_fulldomain'])
                    execute.execute(ssh, ['drush', '-y', 'en', module],context, path=vals['service_full_localpath_files'] + '/sites/' + vals['base_fulldomain'])
                    if vals['base_poweruser_name'] and vals['base_poweruser_email']:
                        execute.execute(ssh, ['drush', vals['service_full_localpath_files'] + '/wikicompare.script', '--user=' + vals['base_poweruser_name'], 'deploy_demo'],context, path=vals['service_full_localpath_files'] + '/sites/' + vals['base_fulldomain'])
            ssh.close()
            sftp.close()
        return


    # def deploy_prepare_apache(self, cr, uid, vals, context=None):
    #     res = super(saas_base, self).deploy_prepare_apache(cr, uid, vals, context)
    #     context.update({'saas-self': self, 'saas-cr': cr, 'saas-uid': uid})
    #     if vals['apptype_name'] == 'odoo':
    #         ssh, sftp = execute.connect(vals['proxy_fullname'], context=context)
    #         execute.execute(ssh, ['sed', '-i', '"s/BASE/' + vals['base_name'] + '/g"', vals['base_apache_configfile']], context)
    #         execute.execute(ssh, ['sed', '-i', '"s/DOMAIN/' + vals['domain_name'] + '/g"', vals['base_apache_configfile']], context)
    #         execute.execute(ssh, ['sed', '-i', '"s/SERVER/' + vals['server_domain'] + '/g"', vals['base_apache_configfile']], context)
    #         execute.execute(ssh, ['sed', '-i', '"s/PORT/' + vals['service_options']['port']['hostport'] + '/g"', vals['base_apache_configfile']], context)
    #         ssh.close()
    #         sftp.close()
    #     return
    #


    def post_reset(self, cr, uid, vals, context=None):
        res = super(saas_base, self).post_reset(cr, uid, vals, context)
        context.update({'saas-self': self, 'saas-cr': cr, 'saas-uid': uid})
        if vals['apptype_name'] == 'drupal':

            ssh, sftp = execute.connect(vals['container_fullname'], username=vals['apptype_system_user'], context=context)
            execute.execute(ssh, ['cp', '-R', vals['service_parent_full_localpath'] + '/sites/' + vals['base_parent_fulldomain'], vals['service_full_localpath_files'] + '/sites/' + vals['base_fulldomain']], context)
            ssh.close()
            sftp.close()

        return res


    def update_base(self, cr, uid, vals, context=None):
        res = super(saas_base, self).update_base(cr, uid, vals, context)
        context.update({'saas-self': self, 'saas-cr': cr, 'saas-uid': uid})
        if vals['apptype_name'] == 'drupal':
            ssh, sftp = execute.connect(vals['container_fullname'], username=vals['apptype_system_user'], context=context)
            execute.execute(ssh, ['drush', 'updatedb'], context, path=vals['service_full_localpath_files'] + '/sites/' + vals['base_fulldomain'])
            ssh.close()
            sftp.close()

        return res

class saas_save_save(osv.osv):
    _inherit = 'saas.save.save'


    def deploy_base(self, cr, uid, vals, context=None):
        res = super(saas_save_save, self).deploy_base(cr, uid, vals, context)
        context.update({'saas-self': self, 'saas-cr': cr, 'saas-uid': uid})
        if vals['apptype_name'] == 'drupal':
            ssh, sftp = execute.connect(vals['container_fullname'], username=vals['apptype_system_user'], context=context)
#            execute.execute(ssh, ['drush', 'archive-dump', vals['base_unique_name_'], '--destination=/base-backup/' + vals['saverepo_name'] + 'tar.gz'], context)
            execute.execute(ssh, ['cp', '-R', vals['service_full_localpath_files'] + '/sites/' + vals['base_fulldomain'], '/base-backup/' + vals['saverepo_name'] + '/site'], context)
            ssh.close()
            sftp.close()
        return


    def restore_base(self, cr, uid, vals, context=None):
        res = super(saas_save_save, self).restore_base(cr, uid, vals, context)
        context.update({'saas-self': self, 'saas-cr': cr, 'saas-uid': uid})
        if vals['apptype_name'] == 'drupal':
            ssh, sftp = execute.connect(vals['container_fullname'], username=vals['apptype_system_user'], context=context)
            execute.execute(ssh, ['rm', '-rf', vals['service_full_localpath_files'] + '/sites/' + vals['base_fulldomain']], context)
            execute.execute(ssh, ['cp', '-R', '/base-backup/' + vals['saverepo_name'] + '/site', vals['service_full_localpath_files'] + '/sites/' + vals['base_fulldomain']], context)
            ssh.close()
            sftp.close()
        return