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


class saas_base(osv.osv):
    _name = 'saas.base'
    _inherit = ['saas.log.model']

    _columns = {
        'name': fields.char('Name', size=64, required=True),
        'title': fields.char('Title', size=64, required=True),
        'domain_id': fields.many2one('saas.domain', 'Domain name', required=True),
        'service_id': fields.many2one('saas.service', 'Service', required=True),
        'service_ids': fields.many2many('saas.service', 'saas_base_service_rel', 'base_id', 'service_id', 'Alternative Services'),
        'proxy_id': fields.many2one('saas.container', 'Proxy', required=True),
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
    }

    _defaults = {
      'build': 'restore',
      'admin_passwd': execute.generate_random_password(20),
      'poweruser_passwd': execute.generate_random_password(12),
      'lang': 'en_US'
    }

    _sql_constraints = [
        ('name_domain_uniq', 'unique (name,domain_id)', 'The name of the saas must be unique per domain !')
    ]

#########TODO La liaison entre base et service est un many2many à cause du loadbalancing. Si le many2many est vide, un service est créé automatiquement. Finalement il y aura un many2one pour le principal, et un many2many pour gérer le loadbalancing
#########Contrainte : L'application entre base et service doit être la même, de plus la bdd/host/db_user/db_password doit être la même entre tous les services d'une même base

    def get_vals(self, cr, uid, id, context=None):

        vals = {}

        base = self.browse(cr, uid, id, context=context)

        vals.update(self.pool.get('saas.domain').get_vals(cr, uid, base.domain_id.id, context=context))
        vals.update(self.pool.get('saas.service').get_vals(cr, uid, base.service_id.id, context=context))

        unique_name = vals['app_code'] + '-' + base.name + '-' + base.domain_id.name
        unique_name = unique_name.replace('.','-')

        proxy_vals = self.pool.get('saas.container').get_vals(cr, uid, base.proxy_id.id, context=context)
        vals.update({
            'proxy_id': proxy_vals['container_id'],
            'proxy_ssh_port': proxy_vals['container_ssh_port'],
            'proxy_server_id': proxy_vals['server_id'],
            'proxy_server_domain': proxy_vals['server_domain'],
        })

        options = {}
        for option in base.service_id.container_id.application_id.type_id.option_ids:
            if option.type == 'base':
                options[option.name] = {'id': option.id, 'name': option.name, 'value': option.default}
        for option in base.option_ids:
            options[option.name.name] = {'id': option.id, 'name': option.name.name, 'value': option.value}


        vals.update({
            'base_name': base.name,
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
            'base_options': options,
            'base_apache_configfile': '/etc/apache2/sites-available/' + unique_name,
            'base_shinken_configfile': '/usr/local/shinken/etc/services/' + unique_name + '.cfg'
        })

        return vals



    def create(self, cr, uid, vals, context={}):
        res = super(saas_base, self).create(cr, uid, vals, context=context)
        context = self.create_log(cr, uid, res, 'create', context)
        vals = self.get_vals(cr, uid, res, context=context)
        try:
            self.deploy(cr, uid, vals, context)
        except:
            self.unlink(cr, uid, [res], context=context)
            raise
        self.end_log(cr, uid, res, context=context)
        return res


    def unlink(self, cr, uid, ids, context={}):
        for base in self.browse(cr, uid, ids, context=context):
            vals = self.get_vals(cr, uid, base.id, context=context)
            self.purge(cr, uid, vals, context=context)
        return super(saas_base, self).unlink(cr, uid, ids, context=context)

    # def create(self, cr, uid, vals, context=None):
        # res = super(saas_saas, self).create(cr, uid, vals, context=context)

        # config = self.pool.get('ir.model.data').get_object(cr, uid, 'saas', 'saas_settings')

        # for saas in self.browse(cr, uid, [res], context=context):

            # _logger.info('Deploying saas %s', saas.name)


            # args = [
                # config.openerp_path + '/saas/saas/shell/deploy.sh',
                # 'saas',
                # saas.instance_id.application_id.type_id.name,
                # saas.instance_id.application_id.code,
                # saas.domain_id.name,
                # saas.name,
                # saas.title,
                # saas.instance_id.application_id.type_id.system_user,
                # saas.instance_id.server_id.name,
                # saas.instance_id.database_server_id.name,
                # saas.instance_id.bdd,
                # saas.instance_id.database_password,
                # saas.instance_id.name,
                # str(saas.instance_id.port),
                # saas.instance_id.application_id.type_id.admin_name,
                # saas.admin_passwd,
                # saas.instance_id.application_id.type_id.admin_email,
                # saas.poweruser_name,
                # saas.poweruser_passwd,
                # saas.poweruser_email,
                # saas.build,
                # str(saas.test),
                # str(saas.instance_id.skip_analytics),
                # config.piwik_server,
                # config.piwik_password,
                # saas.instance_id.application_id.piwik_demo_id,
                # saas.instance_id.application_id.instances_path,
                # config.openerp_path,
                # config.dns_server,
                # config.shinken_server,
                # config.backup_directory,
                # saas.instance_id.database_server_id.mysql_passwd
            # ]

            
            # _logger.info('command %s', args)
            # _logger.info('command %s', " ".join(args))

            # proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

            # outfile = open(config.log_path + '/saas_' + saas.domain_id.name + '_' + saas.name + '.log', "w")
            # for line in proc.stdout:
               # _logger.info(line)
               # outfile.write(line)



        # return res




    # def unlink(self, cr, uid, ids, context=None):

        # config = self.pool.get('ir.model.data').get_object(cr, uid, 'saas', 'saas_settings')

        # for saas in self.browse(cr, uid, ids, context=context):

            # _logger.info('Removing saas %s', saas.name)

            # args = [
                # config.openerp_path + '/saas/saas/shell/purge.sh',
                # 'saas',
                # saas.instance_id.application_id.type_id.name,
                # saas.instance_id.application_id.code,
                # saas.domain_id.name,
                # saas.name,
                # saas.instance_id.application_id.type_id.system_user,
                # saas.instance_id.server_id.name,
                # saas.instance_id.database_server_id.name,
                # saas.instance_id.bdd,
                # config.piwik_server,
                # config.piwik_password,
                # saas.instance_id.application_id.instances_path,
                # config.openerp_path,
                # config.dns_server,
                # config.shinken_server,
                # saas.instance_id.database_server_id.mysql_passwd
            # ]

            # _logger.info('command %s', " ".join(args))

            # proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

            # outfile = open(config.log_path + '/saas_' + saas.domain_id.name + '_' + saas.name + '.log', "w")
            # for line in proc.stdout:
               # _logger.info(line)
               # outfile.write(line)


        # return super(saas_saas, self).unlink(cr, uid, ids, context=context)

    # def button_save(self, cr, uid, ids, context={}):
        # instance_obj = self.pool.get('saas.service')
        # for saas in self.browse(cr, uid, ids, context=context):
            # instance_obj.save(cr, uid, [saas.instance_id.id], saas_id=saas.id, context=context)
        # return True

    # def send_preprod(self, cr, uid, ids, context={}):

        # config = self.pool.get('ir.model.data').get_object(cr, uid, 'saas', 'saas_settings')
        # saas_obj = self.pool.get('saas.saas')

        # for saas in self.browse(cr, uid, ids, context=context):

            # new_saas = 'preprod' + saas.name

            # saas_ids = saas_obj.search(cr, uid, [('name', '=', new_saas),('domain_id','=',saas.domain_id.id)], context=context)
            # saas_obj.unlink(cr, uid, saas_ids, context=context)

            # self.create(cr, uid, {
                # 'name': new_saas,
                # 'title': saas.title,
                # 'domain_id': saas.domain_id.id,
                # 'instance_id': saas.instance_id.application_id.preprod_instance_id.id,
                # 'poweruser_name': saas.poweruser_name,
                # 'poweruser_passwd': saas.poweruser_passwd,
                # 'poweruser_email': saas.poweruser_email,
                # 'build': 'none',
                # 'test': saas.test,
              # }, context=context)

            # _logger.info('moving saas %s', saas.name)

            # args = [
                # config.openerp_path + '/saas/saas/shell/move.sh',
                # 'move_saas',
                # saas.instance_id.application_id.type_id.name,
                # saas.instance_id.application_id.code,
                # saas.name,
                # saas.domain_id.name,
                # saas.instance_id.name,
                # saas.instance_id.server_id.name,
                # saas.instance_id.application_id.type_id.system_user,
                # saas.instance_id.database_server_id.name,
                # new_saas,
                # saas.domain_id.name,
                # saas.instance_id.application_id.preprod_instance_id.name,
                # saas.instance_id.application_id.preprod_instance_id.server_id.name,
                # saas.instance_id.application_id.type_id.system_user,
                # saas.instance_id.application_id.preprod_instance_id.database_server_id.name,
                # saas.instance_id.application_id.instances_path,
                # config.backup_directory,
                # config.openerp_path,

            # ]

            # _logger.info('command %s', " ".join(args))

            # proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

            # outfile = open(config.log_path + '/send_preprod.log', "w")
            # for line in proc.stdout:
               # _logger.info(line)
               # outfile.write(line)

            # instance = saas.instance_id.application_id.preprod_instance_id
            # args = [
                # config.openerp_path + '/saas/saas/apps/' + instance.application_id.type_id.name + '/upgrade.sh',
                # 'upgrade_saas',
                # instance.application_id.code,
                # new_saas,
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
        res = self.deploy_create_database(cr, uid, vals, context)
        if not res:
            if vals['app_bdd'] != 'mysql':
                ssh, sftp = execute.connect(vals['server_domain'], vals['container_ssh_port'], vals['apptype_system_user'], context)
                execute.execute(ssh, ['createdb', '-h', vals['bdd_server_domain'], '-U', vals['service_db_user'], vals['base_unique_name_']], context)
                ssh.close()
                sftp.close()
            # else:
  # ssh www-data@$database_server << EOF
    # mysql -u root -p'$mysql_password' -se "create database $unique_name_underscore;"
    # mysql -u root -p'$mysql_password' -se "grant all on $unique_name_underscore.* to '${db_user}';"
# EOF
  # fi

        execute.log('Database created', context)
        if vals['base_build'] == 'build':
            self.deploy_build(cr, uid, vals, context)

        elif vals['base_build'] == 'restore':
            if vals['app_bdd'] != 'mysql':
                ssh, sftp = execute.connect(vals['server_domain'], vals['container_ssh_port'], vals['apptype_system_user'], context)
                execute.execute(ssh, ['pg_restore', '-h', vals['bdd_server_domain'], '-U', vals['service_db_user'], '--no-owner', '-Fc', '-d', vals['base_unique_name_'], vals['app_version_full_localpath'] + '/' + vals['app_bdd'] + '/build.sql'], context)
                ssh.close()
                sftp.close()
            else:
                ssh, sftp = execute.connect(vals['server_domain'], vals['container_ssh_port'], vals['apptype_system_user'], context)
                execute.execute(ssh, ['mysql', '-h', vals['bdd_server_domain'], '-u', vals['service_db_user'], '-p' + vals['bdd_server_mysql_passwd'], vals['base_unique_name_'], '<', vals['app_version_full_localpath'] + '/' + vals['app_bdd'] + '/build.sql'], context)
                ssh.close()
                sftp.close()

            self.deploy_post_restore(cr, uid, vals, context)

        if vals['base_build'] != 'none':
            self.deploy_create_poweruser(cr, uid, vals, context)

            if vals['base_test']:
                self.deploy_test(cr, uid, vals, context)

        self.deploy_post(cr, uid, vals, context)


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

        ssh, sftp = execute.connect(vals['proxy_server_domain'], vals['proxy_ssh_port'], 'root', context)
        sftp.put(vals['config_conductor_path'] + '/saas/saas_' + vals['apptype_name'] + '/res/apache.config', vals['base_apache_configfile'])
        self.deploy_prepare_apache(cr, uid, vals, context)
        execute.execute(ssh, ['a2ensite', vals['base_unique_name']], context)
        execute.execute(ssh, ['/etc/init.d/apache2', 'reload'], context)
        ssh.close()
        sftp.close()


        ssh, sftp = execute.connect(vals['dns_server_domain'], vals['dns_ssh_port'], 'root', context)
        execute.execute(ssh, ['sed', '-i', '"/' + vals['base_name'] + '\sIN\sCNAME/d"', vals['domain_configfile']], context)
        execute.execute(ssh, ['echo "' + vals['base_name'] + ' IN CNAME ' + vals['proxy_server_domain'] + '" >> ' + vals['domain_configfile']], context)
        execute.execute(ssh, ['/etc/init.d/bind9', 'reload'], context)
        ssh.close()
        sftp.close()

        ssh, sftp = execute.connect(vals['shinken_server_domain'], vals['shinken_ssh_port'], 'root', context)
        sftp.put(vals['config_conductor_path'] + '/saas/saas_shinken/res/base-shinken.config', vals['base_shinken_configfile'])
        execute.execute(ssh, ['sed', '-i', '"s/UNIQUE_NAME/' + vals['base_unique_name'] + '/g"', vals['base_shinken_configfile']], context)
        execute.execute(ssh, ['sed', '-i', '"s/BASE/' + vals['base_name'] + '/g"', vals['base_shinken_configfile']], context)
        execute.execute(ssh, ['sed', '-i', '"s/APPLICATION/' + vals['app_name'] + '/g"', vals['base_shinken_configfile']], context)
        execute.execute(ssh, ['sed', '-i', '"s/SERVER/' + vals['server_domain'] + '/g"', vals['base_shinken_configfile']], context)
        execute.execute(ssh, ['sed', '-i', '"s/SERVICE/' + vals['service_name'] + '/g"', vals['base_shinken_configfile']], context)
        execute.execute(ssh, ['sed', '-i', '"s/DOMAIN/' + vals['domain_name'] + '/g"', vals['base_shinken_configfile']], context)
        execute.execute(ssh, ['/etc/init.d/shinken', 'reload'], context)
        ssh.close()
        sftp.close()


# directory=$backup_directory/control_backups/`date +%Y-%m-%d`-${server}-${instance}-auto
# directory=${directory//./-}

# if ssh $shinken_server stat $directory \> /dev/null 2\>\&1
# then
  # echo Shinken save already set
# else
# ssh $shinken_server << EOF
  # mkdir $directory
  # mkdir $directory/$instance
  # echo 'lorem ipsum' > $directory/$instance/lorem.txt
# EOF
# fi

# ssh $shinken_server << EOF
# echo 'lorem ipsum' > $directory/$unique_name_underscore.sql
# EOF



    def purge_post(self, cr, uid, vals, context=None):
        return

    def purge(self, cr, uid, vals, context={}):
        context.update({'saas-self': self, 'saas-cr': cr, 'saas-uid': uid})

        ssh, sftp = execute.connect(vals['shinken_server_domain'], vals['shinken_ssh_port'], 'root', context)
        execute.execute(ssh, ['rm', vals['base_shinken_configfile']], context)
        execute.execute(ssh, ['/etc/init.d/shinken', 'reload'], context)
        ssh.close()
        sftp.close()


        ssh, sftp = execute.connect(vals['dns_server_domain'], vals['dns_ssh_port'], 'root', context)
        execute.execute(ssh, ['sed', '-i', '"/' + vals['base_name'] + '\sIN\sCNAME/d"', vals['domain_configfile']], context)
        execute.execute(ssh, ['/etc/init.d/bind9', 'reload'], context)
        ssh.close()
        sftp.close()

        ssh, sftp = execute.connect(vals['proxy_server_domain'], vals['proxy_ssh_port'], 'root', context)
        execute.execute(ssh, ['a2dissite', vals['base_unique_name']], context)
        execute.execute(ssh, ['rm', vals['base_apache_configfile']], context)
        execute.execute(ssh, ['/etc/init.d/apache2', 'reload'], context)
        ssh.close()
        sftp.close()

        if vals['app_bdd'] != 'mysql':
            ssh, sftp = execute.connect(vals['database_server_domain'], vals['database_ssh_port'], 'postgres', context)
            execute.execute(ssh, ['psql', '-c', '"update pg_database set datallowconn = \'false\' where datname = \'' + vals['base_unique_name_'] + '\'; SELECT pg_terminate_backend(procpid) FROM pg_stat_activity WHERE datname = \'' + vals['base_unique_name_'] + '\';"'], context)
            execute.execute(ssh, ['dropdb', vals['base_unique_name_']], context)

            ssh.close()
            sftp.close()

        else:
            ssh, sftp = execute.connect(vals['bdd_server_domain'], vals['bdd_server_ssh_port'], vals['apptype_system_user'], context)
            execute.execute(ssh, ["mysql -u root -p'" + vals['bdd_server_mysql_password'] + "' -se 'drop database '" + vals['base_unique_name_'] + ";'"], context)
            ssh.close()
            sftp.close()

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



class saas_base_option(osv.osv):
    _name = 'saas.base.option'

    _columns = {
        'base_id': fields.many2one('saas.base', 'Base', ondelete="cascade", required=True),
        'name': fields.many2one('saas.application.type.option', 'Option', required=True),
        'value': fields.text('Value'),
    }

