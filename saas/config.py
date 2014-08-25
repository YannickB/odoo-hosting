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




class saas_config_settings(osv.osv):
    _name = 'saas.config.settings'
    _description = 'SaaS configuration'

    _columns = {
        'conductor_path': fields.char('Conductor Path', size=128),
        'email_sysadmin': fields.char('Email SysAdmin', size=128),
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
        'mailchimp_username': fields.char('MailChimp Username', size=64),
        'mailchimp_apikey': fields.char('MailChimp API Key', size=64),
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
            'config_email_sysadmin': config.email_sysadmin,
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
            'config_mailchimp_username': config.mailchimp_username,
            'config_mailchimp_apikey': config.mailchimp_apikey,
            'now_date': now.strftime("%Y-%m-%d"),
            'now_hour': now.strftime("%H-%M"),
            'now_hour_regular': now.strftime("%H:%M:%S"),
            'now_bup': now.strftime("%Y-%m-%d-%H%M%S"),
        })
        return vals


    def reset_keys(self, cr, uid, ids, context={}):
        container_obj = self.pool.get('saas.container')
        container_ids = container_obj.search(cr, uid, [], context=context)
        container_obj.reset_key(cr, uid, container_ids, context=context)


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

    def save_all(self, cr, uid, ids, context={}):
        container_obj = self.pool.get('saas.container')
        base_obj = self.pool.get('saas.base')
        context.update({'saas-self': self, 'saas-cr': cr, 'saas-uid': uid})

        vals = self.get_vals(cr, uid, context=context)


        context['save_comment'] = 'Save before upload_save'
        container_ids = container_obj.search(cr, uid, [], context=context)
        container_obj.save(cr, uid, container_ids, context=context)
        base_ids = base_obj.search(cr, uid, [], context=context)
        base_obj.save(cr, uid, base_ids, context=context)

    def save_fsck(self, cr, uid, ids, context={}):
        context.update({'saas-self': self, 'saas-cr': cr, 'saas-uid': uid})
        vals = self.get_vals(cr, uid, context=context)
        ssh, sftp = execute.connect(vals['bup_fullname'], username='bup', context=context)
        execute.execute(ssh, ['bup', 'fsck', '-r'], context)
        execute.execute(ssh, ['bup', 'fsck', '-g'], context)
        ssh.close()
        sftp.close()

    def save_upload(self, cr, uid, ids, context={}):
        context.update({'saas-self': self, 'saas-cr': cr, 'saas-uid': uid})
        vals = self.get_vals(cr, uid, context=context)
        ssh, sftp = execute.connect(vals['bup_fullname'], username='bup', context=context)
        execute.execute(ssh, ['tar', 'czf', '/home/bup/bup.tar.gz', '-C', '/home/bup/.bup', '.'], context)
        execute.execute(ssh, ['/opt/upload', vals['config_ftpuser'], vals['config_ftppass'], vals['config_ftpserver']], context)
        execute.execute(ssh, ['rm', '/home/bup/bup.tar.gz'], context)
        ssh.close()
        sftp.close()


    def save_control(self, cr, uid, ids, context={}):
        container_obj = self.pool.get('saas.container')
        base_obj = self.pool.get('saas.base')
        context.update({'saas-self': self, 'saas-cr': cr, 'saas-uid': uid})
        vals = self.get_vals(cr, uid, context=context)
        ssh, sftp = execute.connect(vals['shinken_fullname'], context=context)
        execute.execute(ssh, ['rm', '-rf', '/opt/control-bup'], context)
        execute.execute(ssh, ['mkdir', '-p', '/opt/control-bup/bup'], context)
        execute.execute(ssh, ['ncftpget', '-u', vals['config_ftpuser'], '-p' + vals['config_ftppass'], vals['config_ftpserver'], '/opt/control-bup', '/bup.tar.gz'], context)
        execute.execute(ssh, ['tar', '-xf', '/opt/control-bup/bup.tar.gz', '-C', '/opt/control-bup/bup'], context)

        container_ids = container_obj.search(cr, uid, [], context=context)
        base_ids = base_obj.search(cr, uid, [], context=context)
        for container in container_obj.browse(cr, uid, container_ids, context=context):
            container_vals = container_obj.get_vals(cr, uid, container.id, context=context)
            if container_vals['container_no_save']:
                continue
            execute.execute(ssh, ['export BUP_DIR=/opt/control-bup/bup; bup restore -C /opt/control-bup/restore/' + container_vals['container_fullname'] + ' ' + container_vals['saverepo_name'] + '/latest'], context)
        for base in base_obj.browse(cr, uid, base_ids, context=context):
            base_vals = base_obj.get_vals(cr, uid, base.id, context=context)
            if base_vals['base_nosave']:
                continue
            execute.execute(ssh, ['export BUP_DIR=/opt/control-bup/bup; bup restore -C /opt/control-bup/restore/' + base_vals['base_unique_name_'] + ' ' + base_vals['saverepo_name'] + '/latest'], context)
        execute.execute(ssh, ['chown', '-R', 'shinken:shinken', '/opt/control-bup'], context)
        ssh.close()
        sftp.close()

    def purge_expired_saverepo(self, cr, uid, ids, context={}):
        repo_obj = self.pool.get('saas.save.repository')
        vals = self.get_vals(cr, uid, context=context)
        expired_saverepo_ids = repo_obj.search(cr, uid, [('date_expiration','!=',False),('date_expiration','<',vals['now_date'])], context=context)
        repo_obj.unlink(cr, uid, expired_saverepo_ids, context=context)

    def purge_expired_logs(self, cr, uid, ids, context={}):
        log_obj = self.pool.get('saas.log')
        vals = self.get_vals(cr, uid, context=context)
        expired_log_ids = log_obj.search(cr, uid, [('expiration_date','!=',False),('expiration_date','<',vals['now_date'])], context=context)
        log_obj.unlink(cr, uid, expired_log_ids, context=context)

    def launch_next_saves(self, cr, uid, ids, context={}):
        context['save_comment'] = 'Auto save'
        container_obj = self.pool.get('saas.container')
        vals = self.get_vals(cr, uid, context=context)
        container_ids = container_obj.search(cr, uid, [('date_next_save','!=',False),('date_next_save','<',vals['now_date'] + ' ' + vals['now_hour_regular'])], context=context)
        container_obj.save(cr, uid, container_ids, context=context)
        base_obj = self.pool.get('saas.base')
        vals = self.get_vals(cr, uid, context=context)
        base_ids = base_obj.search(cr, uid, [('date_next_save','!=',False),('date_next_save','<',vals['now_date'] + ' ' + vals['now_hour_regular'])], context=context)
        base_obj.save(cr, uid, base_ids, context=context)


    def reset_bases(self, cr, uid, ids, context={}):
        base_obj = self.pool.get('saas.base')
        base_ids = base_obj.search(cr, uid, [('reset_each_day','=',True)], context=context)
        base_obj.reinstall(cr, uid, base_ids, context=context)

    def cron_daily(self, cr, uid, ids, context={}):
        self.reset_keys(cr, uid, [], context=context)
        self.save_fsck(cr, uid, [], context=context)
        self.save_all(cr, uid, [], context=context)
        self.save_upload(cr, uid, [], context=context)
        self.save_control(cr, uid, [], context=context)
        self.purge_expired_saverepo(cr, uid, [], context=context)
        self.purge_expired_logs(cr, uid, [], context=context)
        self.launch_next_saves(cr, uid, [], context=context)
        self.reset_bases(cr, uid, [], context=context)
        return True
