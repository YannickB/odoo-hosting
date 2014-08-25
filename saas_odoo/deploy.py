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

    def get_vals(self, cr, uid, id, context=None):

        vals = super(saas_service, self).get_vals(cr, uid, id, context=context)

        service = self.browse(cr, uid, id, context=context)

        if 'port' in vals['service_options'] and vals['service_options']['port']['value'] in vals['container_ports']:
            port = vals['container_ports'][vals['service_options']['port']['value']]
            vals['service_options']['port']['localport'] = port['localport']
            vals['service_options']['port']['hostport'] = port['hostport']
            
        return vals

    def deploy_post_service(self, cr, uid, vals, context):
        super(saas_service, self).deploy_post_service(cr, uid, vals, context)
        context.update({'saas-self': self, 'saas-cr': cr, 'saas-uid': uid})
        if vals['apptype_name'] == 'odoo':
            ssh, sftp = execute.connect(vals['container_fullname'], username=vals['apptype_system_user'], context=context)
            # execute.execute(ssh, ['ln', '-s', vals['app_version_full_localpath'], '/opt/odoo/services/' + vals['service_name']], context)
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
            execute.execute(ssh, ['sed', '-i', 's/PORT/' + vals['service_options']['port']['localport'] + '/g', config_file], context)

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
            ssh, sftp = execute.connect(vals['container_fullname'], username=vals['apptype_system_user'], context=context)
            execute.execute(ssh, ['mkdir', '-p', '/opt/odoo/filestore/' + vals['base_unique_name_']], context)
            ssh.close()
            sftp.close()
            if vals['base_build'] == 'build':

#I had to go in /usr/local/lib/python2.7/dist-packages/erppeek.py and replace def create_database line 610. More specifically, db.create and db.get_progress used here aren't working anymore, see why in odoo/services/db.py, check dispatch function.
#    def create_database(self, passwd, database, demo=False, lang='en_US',
#                        user_password='admin'):
#        thread_id = self.db.create_database(passwd, database, demo, lang, user_password)
#        self.login('admin', user_password,
#                       database=database)

                execute.log("client = erppeek.Client('http://" + vals['server_domain'] + ":" + vals['service_options']['port']['hostport'] + "')", context)
                client = erppeek.Client('http://' + vals['server_domain'] + ':' + vals['service_options']['port']['hostport'])
                execute.log("client.create_database('" + vals['service_db_password'] + "','" + vals['base_unique_name_'] + "'," + "demo=" + str(vals['base_test']) + "," + "lang='" + vals['base_lang'] + "'," + "user_password='" + vals['base_admin_passwd'] + "')", context)
                client.create_database(vals['service_db_password'], vals['base_unique_name_'], demo=vals['base_test'], lang=vals['base_lang'], user_password=vals['base_admin_passwd'])
#                cmd = ['/usr/local/bin/erppeek', '--server', 'http://' + vals['server_domain'] + ':' + vals['service_options']['port']['hostport']]
#                stdin = ["client.create_database('" + vals['service_db_password'] + "', '" + vals['base_unique_name_'] + "', demo=" + str(vals['base_test']) + ", lang='fr_FR', user_password='" + vals['base_admin_passwd'] + "')"]
#                execute.execute_local(cmd, context, stdin_arg=stdin)
                return True
        return res

    def deploy_build(self, cr, uid, vals, context=None):
        res = super(saas_base, self).deploy_build(cr, uid, vals, context)
        context.update({'saas-self': self, 'saas-cr': cr, 'saas-uid': uid})
        if vals['apptype_name'] == 'odoo':
            execute.log("client = erppeek.Client('http://" + vals['server_domain'] + ":" + vals['service_options']['port']['hostport'] + "," + "db=" + vals['base_unique_name_'] + "," + "user='admin', password=" + vals['base_admin_passwd'] + ")", context)
            client = erppeek.Client('http://' + vals['server_domain'] + ':' + vals['service_options']['port']['hostport'], db=vals['base_unique_name_'], user='admin', password=vals['base_admin_passwd'])

            execute.log("admin_id = client.model('ir.model.data').get_object_reference('base', 'user_root')[1]", context)
            admin_id = client.model('ir.model.data').get_object_reference('base', 'user_root')[1]
            execute.log("client.model('res.users').write([" + str(admin_id) + "], {'login': " + vals['apptype_admin_name'] + "})", context)
            client.model('res.users').write([admin_id], {'login': vals['apptype_admin_name']})

            execute.log("extended_group_id = client.model('ir.model.data').get_object_reference('base', 'group_no_one')[1]", context)
            extended_group_id = client.model('ir.model.data').get_object_reference('base', 'group_no_one')[1]
            execute.log("client.model('res.groups').write([" + str(extended_group_id) + "], {'users': [(4, 1)]})", context)
            client.model('res.groups').write([extended_group_id], {'users': [(4, 1)]})

            if vals['app_options']['default_account_chart']['value'] or vals['base_options']['account_chart']['value']:
                account_chart = vals['base_options']['account_chart']['value'] or vals['app_options']['default_account_chart']['value']
                execute.log("client.install('account_accountant', 'account_chart_install', '" + account_chart + "')", context)
                client.install('account_accountant', 'account_chart_install', account_chart)
                execute.log("client.execute('account.chart.template', 'install_chart', '" + account_chart + "', '" +  account_chart + "_pcg_chart_template', 1, 1)", context)
                client.execute('account.chart.template', 'install_chart', account_chart, account_chart + '_pcg_chart_template', 1, 1)

            if vals['app_options']['install_modules']['value']:
                modules = vals['app_options']['install_modules']['value'].split(',')
                for module in modules:
                    execute.log("client.install(" + module + ")", context)
                    client.install(module)

        return res

    def deploy_post(self, cr, uid, vals, context=None):
        res = super(saas_base, self).deploy_post(cr, uid, vals, context)
        context.update({'saas-self': self, 'saas-cr': cr, 'saas-uid': uid})
        if vals['apptype_name'] == 'odoo':
            execute.log("client = erppeek.Client('http://" + vals['server_domain'] + ":" + vals['service_options']['port']['hostport'] + "," + "db=" + vals['base_unique_name_'] + "," + "user='admin', password=" + vals['base_admin_passwd'] + ")", context)
            client = erppeek.Client('http://' + vals['server_domain'] + ':' + vals['service_options']['port']['hostport'], db=vals['base_unique_name_'], user='admin', password=vals['base_admin_passwd'])


            execute.log("company_id = client.model('ir.model.data').get_object_reference('base', 'main_company')[1]", context)
            company_id = client.model('ir.model.data').get_object_reference('base', 'main_company')[1]
            execute.log("client.model('res.company').write([" + str(company_id) + "], {'name':" + vals['base_title'] + "})", context)
            client.model('res.company').write([company_id], {'name': vals['base_title']})

            execute.log("config_ids = client.model('ir.config_parameter').search([('key','=','web.base.url')])", context)
            config_ids = client.model('ir.config_parameter').search([('key','=','web.base.url')])
            if config_ids:
                execute.log("client.model('ir.config_parameter').write(" + str(config_ids) + ", {'value': 'http://" + vals['base_fulldomain'] + "})", context)
                client.model('ir.config_parameter').write(config_ids, {'value': 'http://' + vals['base_fulldomain']})
            else:
                execute.log("client.model('ir.config_parameter').create({'key': 'web.base.url', 'value': 'http://" + vals['base_fulldomain'] + "})", context)
                client.model('ir.config_parameter').create({'key': 'web.base.url', 'value': 'http://' + vals['base_fulldomain']})

            execute.log("config_ids = client.model('ir.config_parameter').search([('key','=','ir_attachment.location')])", context)
            config_ids = client.model('ir.config_parameter').search([('key','=','ir_attachment.location')])
            if config_ids:
                execute.log("client.model('ir.config_parameter').write(" + str(config_ids) + ", {'value': 'file:///filestore'})", context)
                client.model('ir.config_parameter').write(config_ids, {'value': 'file:///filestore'})
            else:
                execute.log("client.model('ir.config_parameter').create({'key': 'ir_attachment.location', 'value': 'file:///filestore'})", context)
                client.model('ir.config_parameter').create({'key': 'ir_attachment.location', 'value': 'file:///filestore'})


    def deploy_create_poweruser(self, cr, uid, vals, context=None):
        res = super(saas_base, self).deploy_create_poweruser(cr, uid, vals, context)
        context.update({'saas-self': self, 'saas-cr': cr, 'saas-uid': uid})
        if vals['apptype_name'] == 'odoo':
            if vals['base_poweruser_name'] and vals['base_poweruser_email'] and vals['apptype_admin_name'] != vals['base_poweruser_name']:
                execute.log("client = erppeek.Client('http://" + vals['server_domain'] + ":" + vals['service_options']['port']['hostport'] + "," + "db=" + vals['base_unique_name_'] + "," + "user='admin', password=" + vals['base_admin_passwd'] + ")", context)
                client = erppeek.Client('http://' + vals['server_domain'] + ':' + vals['service_options']['port']['hostport'], db=vals['base_unique_name_'], user='admin', password=vals['base_admin_passwd'])

                if vals['base_test']:
                    execute.log("demo_id = client.model('ir.model.data').get_object_reference('base', 'user_demo')[1]", context)
                    demo_id = client.model('ir.model.data').get_object_reference('base', 'user_demo')[1]
                    execute.log("client.model('res.users').write([" + str(demo_id) + "], {'login': 'demo_odoo', 'password': 'demo_odoo'})", context)
                    client.model('res.users').write([demo_id], {'login': 'demo_odoo', 'password': 'demo_odoo'})

                execute.log("user_id = client.model('res.users').create({'login':'" + vals['base_poweruser_email'] + "', 'name':'" +  vals['base_poweruser_name'] + "', 'email':'" + vals['base_poweruser_email'] + "', 'password':'" + vals['base_poweruser_password'] + "'})", context)
                user = client.model('res.users').create({'login': vals['base_poweruser_email'], 'name': vals['base_poweruser_name'], 'email': vals['base_poweruser_email'], 'password': vals['base_poweruser_password']})

                if vals['app_options']['poweruser_group']['value']:
                    group = vals['app_options']['poweruser_group']['value'].split('.')
                    execute.log("group_id = client.model('ir.model.data').get_object_reference('" + group[0] + "','" + group[1] + "')[1]", context)
                    group_id = client.model('ir.model.data').get_object_reference(group[0], group[1])[1]
                    execute.log("client.model('res.groups').write([" + str(group_id) + "], {'users': [(4, " + str(user.id) + ")]})", context)
                    client.model('res.groups').write([group_id], {'users': [(4, user.id)]})
        return res


    def deploy_test(self, cr, uid, vals, context=None):
        res = super(saas_base, self).deploy_test(cr, uid, vals, context)
        context.update({'saas-self': self, 'saas-cr': cr, 'saas-uid': uid})
        if vals['apptype_name'] == 'odoo':
            execute.log("client = erppeek.Client('http://" + vals['server_domain'] + ":" + vals['service_options']['port']['hostport'] + "," + "db=" + vals['base_unique_name_'] + "," + "user='admin', password=" + vals['base_admin_passwd'] + ")", context)
            client = erppeek.Client('http://' + vals['server_domain'] + ':' + vals['service_options']['port']['hostport'], db=vals['base_unique_name_'], user='admin', password=vals['base_admin_passwd'])

            execute.log("demo_id = client.model('ir.model.data').get_object_reference('base', 'user_demo')[1]", context)
            demo_id = client.model('ir.model.data').get_object_reference('base', 'user_demo')[1]
            execute.log("client.model('res.users').write([" + str(demo_id) + "], {'login': 'demo_odoo', 'password': 'demo_odoo'})", context)
            client.model('res.users').write([demo_id], {'login': 'demo_odoo', 'password': 'demo_odoo'})

            if vals['app_options']['test_install_modules']['value']:
                modules = vals['app_options']['test_install_modules']['value'].split(',')
                for module in modules:
                    execute.log("client.install(" + module + ")", context)
                    client.install(module)

        return

    #
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


    def deploy_bind(self, cr, uid, vals, context={}):
        res = super(saas_base, self).deploy_bind(cr, uid, vals, context)
        context.update({'saas-self': self, 'saas-cr': cr, 'saas-uid': uid})
        if vals['apptype_name'] == 'odoo':
            if not 'dns_server_domain' in vals:
                execute.log('The dns isnt configured in conf, skipping purge container bind', context)
                return
            ssh, sftp = execute.connect(vals['dns_fullname'], context=context)
            execute.execute(ssh, ['echo "IN MX 1 ' + vals['mail_server_domain'] + '. ;' + vals['base_name'] + ' IN CNAME" >> ' + vals['domain_configfile']], context)
            execute.execute(ssh, ['/etc/init.d/bind9', 'reload'], context)
            ssh.close()
            sftp.close()
        return res

    def deploy_mail(self, cr, uid, vals, context={}):
        res = super(saas_base, self).deploy_mail(cr, uid, vals, context)
        context.update({'saas-self': self, 'saas-cr': cr, 'saas-uid': uid})
        if vals['apptype_name'] == 'odoo':
            execute.log("client = erppeek.Client('http://" + vals['server_domain'] + ":" + vals['service_options']['port']['hostport'] + "," + "db=" + vals['base_unique_name_'] + "," + "user='admin', password=" + vals['base_admin_passwd'] + ")", context)
            client = erppeek.Client('http://' + vals['server_domain'] + ':' + vals['service_options']['port']['hostport'], db=vals['base_unique_name_'], user='admin', password=vals['base_admin_passwd'])
            execute.log("server_id = client.model('ir.model.data').get_object_reference('base', 'ir_mail_server_localhost0')[1]", context)
            server_id = client.model('ir.model.data').get_object_reference('base', 'ir_mail_server_localhost0')[1]
            execute.log("client.model('ir.mail_server').write([" + str(server_id) + "], {'name': 'postfix', 'smtp_host': 'postfix'})", context)
            client.model('ir.mail_server').write([server_id], {'name': 'postfix', 'smtp_host': 'postfix'})

            ssh, sftp = execute.connect(vals['mail_fullname'], context=context)
            execute.execute(ssh, ['sed', '-i', '"/^mydestination =/ s/$/, ' + vals['base_fulldomain'] + '/"', '/etc/postfix/main.cf'], context)
            execute.execute(ssh, ['echo "@' + vals['base_fulldomain'] + ' ' + vals['base_unique_name_'] + '@localhost" >> /etc/postfix/virtual_aliases'], context)
            execute.execute(ssh, ['postmap', '/etc/postfix/virtual_aliases'], context)
            execute.execute(ssh, ["echo '" + vals['base_unique_name_'] + ": \"|openerp_mailgate.py --host=" + vals['server_domain'] + " --port=" + vals['service_options']['port']['hostport'] + " -u 1 -p " + vals['base_admin_passwd'] + " -d " + vals['base_unique_name_'] + "\"' >> /etc/aliases"], context)
            execute.execute(ssh, ['newaliases'], context)
            execute.execute(ssh, ['/etc/init.d/postfix', 'reload'], context)
            ssh.close()
            sftp.close()
        return res


    def purge_mail(self, cr, uid, vals, context={}):
        res = super(saas_base, self).purge_mail(cr, uid, vals, context)
        context.update({'saas-self': self, 'saas-cr': cr, 'saas-uid': uid})
        if vals['apptype_name'] == 'odoo':
            ssh, sftp = execute.connect(vals['mail_fullname'], context=context)
            execute.execute(ssh, ['sed', '-i', '"/^mydestination =/ s/, ' + vals['base_fulldomain'] + '//"', '/etc/postfix/main.cf'], context)
            execute.execute(ssh, ['sed', '-i', '"/@' + vals['base_fulldomain'] + '/d"', '/etc/postfix/virtual_aliases'], context)
            execute.execute(ssh, ['postmap' , '/etc/postfix/virtual_aliases'], context)
            execute.execute(ssh, ['sed', '-i', '"/d\s' + vals['base_unique_name_'] + '/d"', '/etc/aliases'], context)
            execute.execute(ssh, ['newaliases'], context)
            execute.execute(ssh, ['/etc/init.d/postfix', 'reload'], context)
            ssh.close()
            sftp.close()
        return res

    def post_reset(self, cr, uid, vals, context=None):
        res = super(saas_base, self).deploy_mail(cr, uid, vals, context)
        context.update({'saas-self': self, 'saas-cr': cr, 'saas-uid': uid})
        if vals['apptype_name'] == 'odoo':
            execute.log("client = erppeek.Client('http://" + vals['server_domain'] + ":" + vals['service_options']['port']['hostport'] + "," + "db=" + vals['base_unique_name_'] + "," + "user='admin', password=" + vals['base_admin_passwd'] + ")", context)
            client = erppeek.Client('http://' + vals['server_domain'] + ':' + vals['service_options']['port']['hostport'], db=vals['base_unique_name_'], user='admin', password=vals['base_admin_passwd'])
            execute.log("server_id = client.model('ir.model.data').get_object_reference('base', 'ir_mail_server_localhost0')[1]", context)
            server_id = client.model('ir.model.data').get_object_reference('base', 'ir_mail_server_localhost0')[1]
            execute.log("client.model('ir.mail_server').write([" + str(server_id) + "], {'smtp_host': 'mail.disabled.lol'})", context)
            client.model('ir.mail_server').write([server_id], {'smtp_host': 'mail.disabled.lol'})

            execute.log("cron_ids = client.model('ir.cron').search(['|',('active','=',True),('active','=',False)])", context)
            cron_ids = client.model('ir.cron').search(['|',('active','=',True),('active','=',False)])
            execute.log("client.model('ir.cron').write(" + str(cron_ids) +", {'active': False})", context)
            client.model('ir.cron').write(cron_ids, {'active': False})

            ssh, sftp = execute.connect(vals['container_fullname'], username=vals['apptype_system_user'], context=context)
            execute.execute(ssh, ['cp', '-R', '/opt/odoo/filestore/' + vals['base_parent_unique_name_'], '/opt/odoo/filestore/' + vals['base_unique_name_']], context)
            ssh.close()
            sftp.close()

        return res


    def update_base(self, cr, uid, vals, context=None):
        res = super(saas_base, self).update_base(cr, uid, vals, context)
        context.update({'saas-self': self, 'saas-cr': cr, 'saas-uid': uid})
        if vals['apptype_name'] == 'odoo':
            execute.log("client = erppeek.Client('http://" + vals['server_domain'] + ":" + vals['service_options']['port']['hostport'] + "," + "db=" + vals['base_unique_name_'] + "," + "user='admin', password=" + vals['base_admin_passwd'] + ")", context)
            client = erppeek.Client('http://' + vals['server_domain'] + ':' + vals['service_options']['port']['hostport'], db=vals['base_unique_name_'], user='admin', password=vals['base_admin_passwd'])
            execute.log("module_ids = client.model('ir.module.module').search([('state','in',['installed','to upgrade'])])", context)
            module_ids = client.model('ir.module.module').search([('state','in',['installed','to upgrade'])])
            execute.log("client.model('ir.module.module').button_upgrade(" + str(module_ids) + ")", context)
            client.model('ir.module.module').button_upgrade(module_ids)
        return res

class saas_save_save(osv.osv):
    _inherit = 'saas.save.save'


    def deploy_base(self, cr, uid, vals, context=None):
        res = super(saas_save_save, self).deploy_base(cr, uid, vals, context)
        context.update({'saas-self': self, 'saas-cr': cr, 'saas-uid': uid})
        if vals['apptype_name'] == 'odoo':
            ssh, sftp = execute.connect(vals['container_fullname'], username=vals['apptype_system_user'], context=context)
#            execute.execute(ssh, ['mkdir', '-p', '/base-backup/' + vals['saverepo_name'] + '/filestore'], context)
            execute.execute(ssh, ['cp', '-R', '/opt/odoo/filestore/' + vals['base_unique_name_'], '/base-backup/' + vals['saverepo_name'] + '/filestore'], context)
            ssh.close()
            sftp.close()
        return


    def restore_base(self, cr, uid, vals, context=None):
        res = super(saas_save_save, self).restore_base(cr, uid, vals, context)
        context.update({'saas-self': self, 'saas-cr': cr, 'saas-uid': uid})
        if vals['apptype_name'] == 'odoo':
            ssh, sftp = execute.connect(vals['container_fullname'], username=vals['apptype_system_user'], context=context)
            execute.execute(ssh, ['rm', '-rf', '/opt/odoo/filestore/' + vals['base_unique_name_']], context)
            execute.execute(ssh, ['cp', '-R', '/base-backup/' + vals['saverepo_name'] + '/filestore', '/opt/odoo/filestore/' + vals['base_unique_name_']], context)
            ssh.close()
            sftp.close()
        return