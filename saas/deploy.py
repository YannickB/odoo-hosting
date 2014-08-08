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

STARTPORT = 48000
ENDPORT = 50000

class saas_container(osv.osv):
    _inherit = 'saas.container'

    def deploy_post(self, cr, uid, vals, context=None):
        return

    def deploy(self, cr, uid, id, vals, context={}):
        context.update({'saas-self': self, 'saas-cr': cr, 'saas-uid': uid})
        container = self.browse(cr, uid, id, context=context)
        ssh, sftp = execute.connect(vals['server_domain'], vals['server_ssh_port'], 'root', context)

        cmd = ['sudo','docker', 'run', '-d']
        nextport = STARTPORT
        for key, port in vals['container_ports'].iteritems():
            if not port['hostport']:
                while not port['hostport'] and nextport != ENDPORT:
                    port_ids = self.pool.get('saas.container.port').search(cr, uid, [('hostport','=',nextport),('container_id.server_id','=',vals['server_id'])], context=context)
                    if not port_ids and not execute.execute(ssh, ['netstat', '-an', '|', 'grep', str(nextport)], context):
                        self.pool.get('saas.container.port').write(cr, uid, [port['id']], {'hostport': nextport}, context=context)
                        port['hostport'] = nextport
                        if port['name'] == 'ssh':
                            vals['container_ssh_port'] = nextport
                    nextport += 1
                    _logger.info('nextport %s', nextport)
            _logger.info('server_id %s, hostport %s, localport %s', vals['server_ip'], port['hostport'], port['localport'])
            cmd.extend(['-p', vals['server_ip'] + ':' + str(port['hostport']) + ':' + port['localport']])
        for key, volume in vals['container_volumes'].iteritems():
            if volume['hostpath']:
                arg =  volume['hostpath'] + ':' + volume['name']
                if volume['readonly']:
                    arg += ':ro'
                cmd.extend(['-v', arg])
        for key, link in vals['container_links'].iteritems():
            cmd.extend(['--link', link['name'] + ':' + link['name']])
        cmd.extend(['-v', '/opt/keys/conductor_key.pub:/opt/authorized_keys', '--name', vals['container_name'], vals['image_version_fullname']])
        execute.execute(ssh, cmd, context)

        time.sleep(5)

        self.deploy_post(cr, uid, vals, context)

        execute.execute(ssh, ['sudo', 'docker', 'restart', vals['container_name']], context)
        ssh.close()
        sftp.close()
        return

class saas_service(osv.osv):
    _inherit = 'saas.service'

    def deploy_post_service(self, cr, uid, vals, context=None):
        return


    def deploy(self, cr, uid, vals, context=None):
        context.update({'saas-self': self, 'saas-cr': cr, 'saas-uid': uid})
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
            ssh, sftp = execute.connect(vals['database_server_domain'], vals['database_ssh_port'], 'postgres', context)
            execute.execute(ssh, ['psql', '-c', '"CREATE USER ' + vals['service_db_user'] + ' WITH PASSWORD \'' + vals['service_db_password'] + '\' CREATEDB;"'], context)
            ssh.close()
            sftp.close()

            ssh, sftp = execute.connect(vals['server_domain'], vals['container_ssh_port'], vals['apptype_system_user'], context)
            execute.execute(ssh, ['sed', '-i', '"/:*:' + vals['service_db_user'] + ':/d" ~/.pgpass'], context)
            execute.execute(ssh, ['echo "' + vals['database_server_domain'] + ':5432:*:' + vals['service_db_user'] + ':' + vals['service_db_password'] + '" >> ~/.pgpass'], context)
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

class saas_base(osv.osv):
    _inherit = 'saas.base'

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


# scp $openerp_path/saas/saas/apps/$application_type/apache.config www-data@$server:/etc/apache2/sites-available/$unique_name

##escape='\$1'
# $openerp_path/saas/saas/apps/$application_type/deploy.sh prepare_apache $application $saas $instance $domain $server $port $unique_name $instances_path

# ssh www-data@$server << EOF
  # sudo a2ensite $unique_name
  # sudo /etc/init.d/apache2 reload
# EOF


# ssh $dns_server << EOF
  # sed -i "/$saas\sIN\sCNAME/d" /etc/bind/db.$domain
  # echo "$saas IN CNAME $server." >> /etc/bind/db.$domain
  # sudo /etc/init.d/bind9 reload
# EOF


# scp $openerp_path/saas/saas/shell/shinken.config $shinken_server:/usr/local/shinken/etc/services/${unique_name}.cfg

# directory=$backup_directory/control_backups/`date +%Y-%m-%d`-${server}-${instance}-auto
# directory=${directory//./-}

# ssh $shinken_server << EOF
  # sed -i 's/UNIQUE_NAME/${unique_name}/g' /usr/local/shinken/etc/services/${unique_name}.cfg
  # sed -i 's/APPLICATION/${application}/g' /usr/local/shinken/etc/services/${unique_name}.cfg
  # sed -i 's/SERVER/${server}/g' /usr/local/shinken/etc/services/${unique_name}.cfg
  # sed -i 's/INSTANCE/${instance}/g' /usr/local/shinken/etc/services/${unique_name}.cfg
  # sed -i 's/SAAS/${saas}/g' /usr/local/shinken/etc/services/${unique_name}.cfg
  # sed -i 's/DOMAIN/${domain}/g' /usr/local/shinken/etc/services/${unique_name}.cfg
  # /etc/init.d/shinken reload
# EOF


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
