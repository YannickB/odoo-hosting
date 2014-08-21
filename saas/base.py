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
    _name = 'saas.domain'
    _inherit = ['saas.model']

    _columns = {
        'name': fields.char('Domain name', size=64, required=True)
    }

    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'Name must be unique!'),
    ]

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



    def deploy(self, cr, uid, vals, context={}):
        context.update({'saas-self': self, 'saas-cr': cr, 'saas-uid': uid})
        ssh, sftp = execute.connect(vals['dns_fullname'], username='root', context=context)
        sftp.put(vals['config_conductor_path'] + '/saas/saas/res/bind.config', vals['domain_configfile'])
        execute.execute(ssh, ['sed', '-i', '"s/DOMAIN/' + vals['domain_name'] + '/g"', vals['domain_configfile']], context)
        execute.execute(ssh, ['sed', '-i', '"s/IP/' + vals['dns_server_ip'] + '/g"', vals['domain_configfile']], context)
        execute.execute(ssh, ["echo 'zone \"" + vals['domain_name'] + "\" {' >> /etc/bind/named.conf"], context)
        execute.execute(ssh, ['echo "type master;" >> /etc/bind/named.conf'], context)
        execute.execute(ssh, ['echo "allow-transfer {213.186.33.199;};" >> /etc/bind/named.conf'], context)
        execute.execute(ssh, ["echo 'file \"/etc/bind/db." + vals['domain_name'] + "\";' >> /etc/bind/named.conf"], context)
        execute.execute(ssh, ['echo "notify yes;" >> /etc/bind/named.conf'], context)
        execute.execute(ssh, ['echo "};" >> /etc/bind/named.conf'], context)
        execute.execute(ssh, ['echo "//END ' + vals['domain_name'] + '\n" >> /etc/bind/named.conf'], context)
        execute.execute(ssh, ['/etc/init.d/bind9', 'reload'], context)
        ssh.close()
        sftp.close()

    def purge(self, cr, uid, vals, context={}):
        context.update({'saas-self': self, 'saas-cr': cr, 'saas-uid': uid})
        ssh, sftp = execute.connect(vals['dns_fullname'], username='root', context=context)
        execute.execute(ssh, ['sed', '-i', "'/zone\s\"" + vals['domain_name'] + "\"/,/END\s" + vals['domain_name'] + "/d'", '/etc/bind/named.conf'], context)
        execute.execute(ssh, ['rm', vals['domain_configfile']], context)
        execute.execute(ssh, ['/etc/init.d/bind9', 'reload'], context)
        ssh.close()
        sftp.close()

class saas_base(osv.osv):
    _name = 'saas.base'
    _inherit = ['saas.model']

    _columns = {
        'name': fields.char('Name', size=64, required=True),
        'title': fields.char('Title', size=64, required=True),
        'application_id': fields.many2one('saas.application', 'Application', required=True),
        'domain_id': fields.many2one('saas.domain', 'Domain name', required=True),
        'service_id': fields.many2one('saas.service', 'Service', required=True),
        'service_ids': fields.many2many('saas.service', 'saas_base_service_rel', 'base_id', 'service_id', 'Alternative Services'),
        'proxy_id': fields.many2one('saas.container', 'Proxy', required=True),
        'mail_id': fields.many2one('saas.container', 'Mail', required=True),
        'admin_passwd': fields.char('Admin password', size=64),
        'poweruser_name': fields.char('PowerUser name', size=64),
        'poweruser_passwd': fields.char('PowerUser password', size=64),
        'poweruser_email': fields.char('PowerUser email', size=64),
        'build': fields.selection([
                 ('none','No action'),
                 ('build','Build'),
                 ('restore','Restore')],'Build?'),
        'test': fields.boolean('Test?'),
        'lang': fields.selection([('en_US','en_US'),('fr_FR','fr_FR')], 'Language', required=True),
        'state': fields.selection([
                ('installing','Installing'),
                ('enabled','Enabled'),
                ('blocked','Blocked'),
                ('removing','Removing')],'State',readonly=True),
        'option_ids': fields.one2many('saas.base.option', 'base_id', 'Options'),
        'save_repository_id': fields.many2one('saas.save.repository', 'Save repository'),
        'time_between_save': fields.integer('Minutes between each save'),
        'saverepo_change': fields.integer('Days before saverepo change'),
        'saverepo_expiration': fields.integer('Days before saverepo expiration'),
        'date_next_save': fields.datetime('Next save planned'),
        'save_comment': fields.text('Save Comment'),
        'nosave': fields.boolean('No save?'),
    }

    _defaults = {
      'build': 'restore',
      'admin_passwd': execute.generate_random_password(20),
      'poweruser_passwd': execute.generate_random_password(12),
      'lang': 'en_US'
    }

    _sql_constraints = [
        ('name_uniq', 'unique (name,domain_id)', 'Name must be unique per domain !')
    ]

    def _check_application(self, cr, uid, ids, context=None):
        for b in self.browse(cr, uid, ids, context=context):
            if b.application_id.id != b.service_id.application_id.id:
                return False
            for s in b.service_ids:
                if b.application_id.id != s.application_id.id:
                    return False
        return True

    _constraints = [
        (_check_application, "The application of base must be the same than the application of service." , ['service_id','service_ids']),
    ]


#########TODO La liaison entre base et service est un many2many � cause du loadbalancing. Si le many2many est vide, un service est cr�� automatiquement. Finalement il y aura un many2one pour le principal, et un many2many pour g�rer le loadbalancing
#########Contrainte : L'application entre base et service doit �tre la m�me, de plus la bdd/host/db_user/db_password doit �tre la m�me entre tous les services d'une m�me base

    def get_vals(self, cr, uid, id, context=None):
        repo_obj = self.pool.get('saas.save.repository')
        vals = {}

        base = self.browse(cr, uid, id, context=context)

        now = datetime.now()
        if not base.save_repository_id:
            repo_ids = repo_obj.search(cr, uid, [('base_name','=',base.name),('base_domain','=',base.domain_id.name)], context=context)
            if repo_ids:
                self.write(cr, uid, [base.id], {'save_repository_id': repo_ids[0]}, context=context)
                base = self.browse(cr, uid, id, context=context)

        if not base.save_repository_id or datetime.strptime(base.save_repository_id.date_change, "%Y-%m-%d") < now or False:
            repo_vals ={
                'name': now.strftime("%Y-%m-%d") + '_' + base.name + '_' + base.domain_id.name,
                'type': 'base',
                'date_change': (now + timedelta(days=base.saverepo_change or base.application_id.base_saverepo_change)).strftime("%Y-%m-%d"),
                'date_expiration': (now + timedelta(days=base.saverepo_expiration or base.application_id.base_saverepo_expiration)).strftime("%Y-%m-%d"),
                'base_name': base.name,
                'base_domain': base.domain_id.name,
            }
            repo_id = repo_obj.create(cr, uid, repo_vals, context=context)
            self.write(cr, uid, [base.id], {'save_repository_id': repo_id}, context=context)
            base = self.browse(cr, uid, id, context=context)


        vals.update(self.pool.get('saas.domain').get_vals(cr, uid, base.domain_id.id, context=context))
        vals.update(self.pool.get('saas.service').get_vals(cr, uid, base.service_id.id, context=context))
        vals.update(self.pool.get('saas.save.repository').get_vals(cr, uid, base.save_repository_id.id, context=context))

        unique_name = vals['app_code'] + '-' + base.name + '-' + base.domain_id.name
        unique_name = unique_name.replace('.','-')

        proxy_vals = self.pool.get('saas.container').get_vals(cr, uid, base.proxy_id.id, context=context)
        vals.update({
            'proxy_id': proxy_vals['container_id'],
            'proxy_fullname': proxy_vals['container_fullname'],
            'proxy_ssh_port': proxy_vals['container_ssh_port'],
            'proxy_server_id': proxy_vals['server_id'],
            'proxy_server_domain': proxy_vals['server_domain'],
        })
        
        mail_vals = self.pool.get('saas.container').get_vals(cr, uid, base.mail_id.id, context=context)
        vals.update({
            'mail_id': mail_vals['container_id'],
            'mail_fullname': mail_vals['container_fullname'],
            'mail_ssh_port': mail_vals['container_ssh_port'],
            'mail_server_id': mail_vals['server_id'],
            'mail_server_domain': mail_vals['server_domain'],
        })

        options = {}
        for option in base.service_id.container_id.application_id.type_id.option_ids:
            if option.type == 'base':
                options[option.name] = {'id': option.id, 'name': option.name, 'value': option.default}
        for option in base.option_ids:
            options[option.name.name] = {'id': option.id, 'name': option.name.name, 'value': option.value}


        vals.update({
            'base_id': base.id,
            'base_name': base.name,
            'base_fullname': unique_name,
            'base_fulldomain': base.name + '.' + base.domain_id.name,
            'base_unique_name': unique_name,
            'base_unique_name_': unique_name.replace('-','_'),
            'base_title': base.title,
            'base_domain': base.domain_id.name,
            'base_admin_passwd': base.admin_passwd,
            'base_poweruser_name': base.poweruser_name,
            'base_poweruser_password': base.poweruser_passwd,
            'base_poweruser_email': base.poweruser_email,
            'base_build': base.build,
            'base_test': base.test,
            'base_lang': base.lang,
            'base_nosave': base.nosave,
            'base_options': options,
            'base_apache_configfile': '/etc/apache2/sites-available/' + unique_name,
            'base_shinken_configfile': '/usr/local/shinken/etc/services/' + unique_name + '.cfg'
        })

        return vals




    def unlink(self, cr, uid, ids, context={}):
        context['save_comment'] = 'Before unlink'
        self.save(cr, uid, ids, context=context)
        return super(saas_base, self).unlink(cr, uid, ids, context=context)

    def save(self, cr, uid, ids, context={}):
        context.update({'saas-self': self, 'saas-cr': cr, 'saas-uid': uid})
        save_obj = self.pool.get('saas.save.save')

        res = {}
        for base in self.browse(cr, uid, ids, context=context):
            if 'nosave' in context or base.nosave:
                execute.log('The bup isnt configured in conf, skipping save base', context)
                continue
            context = self.create_log(cr, uid, base.id, 'save', context)
            vals = self.get_vals(cr, uid, base.id, context=context)
            if not 'bup_server_domain' in vals:
                execute.log('The bup isnt configured in conf, skipping save base', context)
                return
            save_vals = {
                'name': vals['now_bup'] + '_' + vals['base_unique_name'],
                'repo_id': vals['saverepo_id'],
                'comment': 'save_comment' in context and context['save_comment'] or base.save_comment or 'Manual',
                'now_bup': vals['now_bup'],
                'container_id': vals['container_id'],
                'container_volumes_comma': vals['container_volumes_save'],
                'container_app': vals['app_code'],
                'container_img': vals['image_name'],
                'container_img_version': vals['image_version_name'],
                'container_ports': str(vals['container_ports']),
                'container_volumes': str(vals['container_volumes']),
                'container_options': str(vals['container_options']),
                'service_id': vals['service_id'],
                'service_name': vals['service_name'],
                'service_database_id': vals['database_id'],
                'service_options': str(vals['service_options']),
                'base_id': vals['base_id'],
                'base_title': vals['base_title'],
                'base_app_version': vals['app_version_name'],
                'base_proxy_id': vals['proxy_id'],
                'base_container_name': vals['container_name'],
                'base_container_server': vals['server_domain'],
                'base_admin_passwd': vals['base_admin_passwd'],
                'base_poweruser_name': vals['base_poweruser_name'],
                'base_poweruser_password': vals['base_poweruser_password'],
                'base_poweruser_email': vals['base_poweruser_email'],
                'base_build': vals['base_build'],
                'base_test': vals['base_test'],
                'base_lang': vals['base_lang'],
                'base_nosave': vals['base_nosave'],
                'base_options': str(vals['base_options']),
            }
            res[base.id] = save_obj.create(cr, uid, save_vals, context=context)
            next = (datetime.now() + timedelta(minutes=base.time_between_save or base.application_id.base_time_between_save)).strftime("%Y-%m-%d %H:%M:%S")
            self.write(cr, uid, [base.id], {'save_comment': False, 'date_next_save': next}, context=context)
            self.end_log(cr, uid, base.id, context=context)
        return res

    def reset_proxy(self, cr, uid, ids, context={}):
        for container in self.browse(cr, uid, ids, context=context):
            vals = self.get_vals(cr, uid, container.id, context=context)
            self.deploy_proxy(cr, uid, vals, context=context)

    def reset_bind(self, cr, uid, ids, context={}):
        for container in self.browse(cr, uid, ids, context=context):
            vals = self.get_vals(cr, uid, container.id, context=context)
            self.deploy_bind(cr, uid, vals, context=context)

    def reset_shinken(self, cr, uid, ids, context={}):
        for container in self.browse(cr, uid, ids, context=context):
            vals = self.get_vals(cr, uid, container.id, context=context)
            self.deploy_shinken(cr, uid, vals, context=context)

    def reset_mail(self, cr, uid, ids, context={}):
        for container in self.browse(cr, uid, ids, context=context):
            vals = self.get_vals(cr, uid, container.id, context=context)
            self.deploy_mail(cr, uid, vals, context=context)


    def deploy_create_database(self, cr, uid, vals, context=None):
        return False

    def deploy_build(self, cr, uid, vals, context=None):
        return

    def deploy_post_restore(self, cr, uid, vals, context=None):
        return

    def deploy_create_poweruser(self, cr, uid, vals, context=None):
        return

    def deploy_test(self, cr, uid, vals, context=None):
        return

    def deploy_post(self, cr, uid, vals, context=None):
        return

    def deploy_prepare_apache(self, cr, uid, vals, context=None):
        return

    def deploy(self, cr, uid, vals, context=None):
        context.update({'saas-self': self, 'saas-cr': cr, 'saas-uid': uid})
        self.purge(cr, uid, vals, context=context)

#        if 'base_restoration' not in context:
        res = self.deploy_create_database(cr, uid, vals, context)
        if not res:
            if vals['app_bdd'] != 'mysql':
                ssh, sftp = execute.connect(vals['container_fullname'], username=vals['apptype_system_user'], context=context)
                execute.execute(ssh, ['createdb', '-h', vals['bdd_server_domain'], '-U', vals['service_db_user'], vals['base_unique_name_']], context)
                ssh.close()
                sftp.close()
            # else:
  # ssh www-data@$database_server << EOF
    # mysql -u root -p'$mysql_password' -se "create database $unique_name_underscore;"
    # mysql -u root -p'$mysql_password' -se "grant all on $unique_name_underscore.* to '${db_user}';"
# EOF
  # fi

            # execute.log('Database created', context)
            # if vals['base_build'] == 'build':
                # self.deploy_build(cr, uid, vals, context)

            # elif vals['base_build'] == 'restore':
                # if vals['app_bdd'] != 'mysql':
                    # ssh, sftp = execute.connect(vals['container_fullname'], username=vals['apptype_system_user'], context=context)
                    # execute.execute(ssh, ['pg_restore', '-h', vals['bdd_server_domain'], '-U', vals['service_db_user'], '--no-owner', '-Fc', '-d', vals['base_unique_name_'], vals['app_version_full_localpath'] + '/' + vals['app_bdd'] + '/build.sql'], context)
                    # ssh.close()
                    # sftp.close()
                # else:
                    # ssh, sftp = execute.connect(vals['container_fullname'], username=vals['apptype_system_user'], context=context)
                    # execute.execute(ssh, ['mysql', '-h', vals['bdd_server_domain'], '-u', vals['service_db_user'], '-p' + vals['bdd_server_mysql_passwd'], vals['base_unique_name_'], '<', vals['app_version_full_localpath'] + '/' + vals['app_bdd'] + '/build.sql'], context)
                    # ssh.close()
                    # sftp.close()

                # self.deploy_post_restore(cr, uid, vals, context)

            # if vals['base_build'] != 'none':
                # self.deploy_create_poweruser(cr, uid, vals, context)

                # if vals['base_test']:
                    # self.deploy_test(cr, uid, vals, context)

            # self.deploy_post(cr, uid, vals, context)


  # if [[ $skip_analytics != True ]]
  # then

    # if [[ $saas != 'demo' ]]
    # then
    # ssh $piwik_server << EOF
      # mysql piwik -u piwik -p$piwik_password -se "INSERT INTO piwik_site (name, main_url, ts_created, timezone, currency) VALUES ('$domain_name.wikicompare.info', 'http://$domain_name.wikicompare.info', NOW(), 'Europe/Paris', 'EUR');"
# EOF

    # piwik_id=$(mysql piwik -u piwik -p$piwik_password -se "select idsite from piwik_site WHERE name = '$domain_name.wikicompare.info' LIMIT 1")
    # ssh $piwik_server << EOF
      # mysql piwik -u piwik -p$piwik_password -se "INSERT INTO piwik_access (login, idsite, access) VALUES ('anonymous', $piwik_id, 'view');"
# EOF
    # else
    # piwik_id=$piwik_demo_id
    # fi

    # $openerp_path/saas/saas/apps/$application_type/deploy.sh post_piwik $application $domain $instance $saas $system_user $server $piwik_id $piwik_server $instances_path

  # fi

# fi


        self.deploy_proxy(cr, uid, vals, context=context)
        self.deploy_bind(cr, uid, vals, context=context)
        self.deploy_shinken(cr, uid, vals, context=context)



    def purge_post(self, cr, uid, vals, context=None):
        return

    def purge_db(self, cr, uid, vals, context=None):
        context.update({'saas-self': self, 'saas-cr': cr, 'saas-uid': uid})
        if vals['app_bdd'] != 'mysql':
            ssh, sftp = execute.connect(vals['database_fullname'], username='postgres', context=context)
            execute.execute(ssh, ['psql', '-c', '"update pg_database set datallowconn = \'false\' where datname = \'' + vals['base_unique_name_'] + '\'; SELECT pg_terminate_backend(procpid) FROM pg_stat_activity WHERE datname = \'' + vals['base_unique_name_'] + '\';"'], context)
            execute.execute(ssh, ['dropdb', vals['base_unique_name_']], context)

            ssh.close()
            sftp.close()

        else:
            ssh, sftp = execute.connect(vals['bdd_server_domain'], vals['bdd_server_ssh_port'], vals['apptype_system_user'], context)
            execute.execute(ssh, ["mysql -u root -p'" + vals['bdd_server_mysql_password'] + "' -se 'drop database '" + vals['base_unique_name_'] + ";'"], context)
            ssh.close()
            sftp.close()
        return

    def purge(self, cr, uid, vals, context={}):
        context.update({'saas-self': self, 'saas-cr': cr, 'saas-uid': uid})

        self.purge_shinken(cr, uid, vals, context=context)
        self.purge_bind(cr, uid, vals, context=context)
        self.purge_proxy(cr, uid, vals, context=context)

        self.purge_db(cr, uid, vals, context=context)

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


    def deploy_proxy(self, cr, uid, vals, context={}):
        context.update({'saas-self': self, 'saas-cr': cr, 'saas-uid': uid})
        self.purge_proxy(cr, uid, vals, context=context)
        ssh, sftp = execute.connect(vals['proxy_fullname'], context=context)
        sftp.put(vals['config_conductor_path'] + '/saas/saas_' + vals['apptype_name'] + '/res/apache.config', vals['base_apache_configfile'])
        self.deploy_prepare_apache(cr, uid, vals, context)
        execute.execute(ssh, ['a2ensite', vals['base_unique_name']], context)
        execute.execute(ssh, ['/etc/init.d/apache2', 'reload'], context)
        ssh.close()
        sftp.close()


    def purge_proxy(self, cr, uid, vals, context={}):
        context.update({'saas-self': self, 'saas-cr': cr, 'saas-uid': uid})
        ssh, sftp = execute.connect(vals['proxy_fullname'], context=context)
        execute.execute(ssh, ['a2dissite', vals['base_unique_name']], context)
        execute.execute(ssh, ['rm', vals['base_apache_configfile']], context)
        execute.execute(ssh, ['/etc/init.d/apache2', 'reload'], context)
        ssh.close()
        sftp.close()

    def deploy_bind(self, cr, uid, vals, context={}):
        context.update({'saas-self': self, 'saas-cr': cr, 'saas-uid': uid})
        if not 'dns_server_domain' in vals:
            execute.log('The dns isnt configured in conf, skipping purge container bind', context)
            return
        self.purge_bind(cr, uid, vals, context=context)
        ssh, sftp = execute.connect(vals['dns_fullname'], context=context)
        execute.execute(ssh, ['echo "' + vals['base_name'] + ' IN CNAME ' + vals['proxy_server_domain'] + '." >> ' + vals['domain_configfile']], context)
        execute.execute(ssh, ['/etc/init.d/bind9', 'reload'], context)
        ssh.close()
        sftp.close()


    def purge_bind(self, cr, uid, vals, context={}):
        context.update({'saas-self': self, 'saas-cr': cr, 'saas-uid': uid})
        if not 'dns_server_domain' in vals:
            execute.log('The dns isnt configured in conf, skipping purge container bind', context)
            return
        ssh, sftp = execute.connect(vals['dns_fullname'], context=context)
        execute.execute(ssh, ['sed', '-i', '"/' + vals['base_name'] + '\sIN\sCNAME/d"', vals['domain_configfile']], context)
        execute.execute(ssh, ['/etc/init.d/bind9', 'reload'], context)
        ssh.close()
        sftp.close()


    def deploy_shinken(self, cr, uid, vals, context={}):
        context.update({'saas-self': self, 'saas-cr': cr, 'saas-uid': uid})
        if not 'shinken_server_domain' in vals:
            execute.log('The shinken isnt configured in conf, skipping deploy container shinken', context)
            return
        self.purge_shinken(cr, uid, vals, context=context)
        ssh, sftp = execute.connect(vals['shinken_fullname'], context=context)
        sftp.put(vals['config_conductor_path'] + '/saas/saas_shinken/res/base-shinken.config', vals['base_shinken_configfile'])
        execute.execute(ssh, ['sed', '-i', '"s/TYPE/base/g"', vals['base_shinken_configfile']], context)
        execute.execute(ssh, ['sed', '-i', '"s/UNIQUE_NAME/' + vals['base_unique_name_'] + '/g"', vals['base_shinken_configfile']], context)
        execute.execute(ssh, ['sed', '-i', '"s/BASE/' + vals['base_name'] + '/g"', vals['base_shinken_configfile']], context)
        execute.execute(ssh, ['sed', '-i', '"s/DOMAIN/' + vals['domain_name'] + '/g"', vals['base_shinken_configfile']], context)

        execute.execute(ssh, ['mkdir', '-p', '/opt/control-bup/restore/' + vals['base_unique_name_'] + '/latest'], context)
        execute.execute(ssh, ['echo "' + vals['now_date'] + '" >> /opt/control-bup/restore/' + vals['base_unique_name_'] + '/latest/backup-date'], context)
        execute.execute(ssh, ['echo "lorem ipsum" >> /opt/control-bup/restore/' + vals['base_unique_name_'] + '/latest/' + vals['base_unique_name_'] + '.dump'], context)
        execute.execute(ssh, ['chown', '-R', 'shinken:shinken', '/opt/control-bup'], context)


        execute.execute(ssh, ['/etc/init.d/shinken', 'reload'], context)
        ssh.close()
        sftp.close()


    def purge_shinken(self, cr, uid, vals, context={}):
        context.update({'saas-self': self, 'saas-cr': cr, 'saas-uid': uid})
        if not 'shinken_server_domain' in vals:
            execute.log('The shinken isnt configured in conf, skipping purge container shinken', context)
            return
        ssh, sftp = execute.connect(vals['shinken_fullname'], context=context)
        execute.execute(ssh, ['rm', vals['base_shinken_configfile']], context)
        execute.execute(ssh, ['/etc/init.d/shinken', 'reload'], context)
        ssh.close()
        sftp.close()
        
        
        
    def deploy_mail(self, cr, uid, vals, context={}):
        context.update({'saas-self': self, 'saas-cr': cr, 'saas-uid': uid})
        self.purge_mail(cr, uid, vals, context=context)


    def purge_mail(self, cr, uid, vals, context={}):
        context.update({'saas-self': self, 'saas-cr': cr, 'saas-uid': uid})



class saas_base_option(osv.osv):
    _name = 'saas.base.option'

    _columns = {
        'base_id': fields.many2one('saas.base', 'Base', ondelete="cascade", required=True),
        'name': fields.many2one('saas.application.type.option', 'Option', required=True),
        'value': fields.text('Value'),
    }

    _sql_constraints = [
        ('name_uniq', 'unique(base_id,name)', 'Option name must be unique per base!'),
    ]
