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


from openerp import models, fields, api, _
from openerp.exceptions import except_orm

from datetime import datetime
import execute
from os.path import expanduser

import logging
_logger = logging.getLogger(__name__)

class ClouderConfigBackupMethod(models.Model):
    _name = 'clouder.config.backup.method'
    _description = 'Backup Method'

    name = fields.Char('Name', size=64, required=True)


class ClouderConfigSettings(models.Model):
    _name = 'clouder.config.settings'
    _description = 'Clouder configuration'

    email_sysadmin = fields.Char('Email SysAdmin', size=128)
    end_reset_keys = fields.Datetime('Last Reset Keys ended at')
    end_save_all = fields.Datetime('Last Save All ended at')
    end_reset_bases  = fields.Datetime('Last Reset Bases ended at')

    @api.multi
    def get_vals(self):
        config = self.env.ref('clouder.clouder_settings')

        vals = {}

        if not config.email_sysadmin:
            raise except_orm(_('Data error!'),
                _("You need to specify the sysadmin email in configuration"))


        now = datetime.now()
        vals.update({
            'config_email_sysadmin': config.email_sysadmin,
            'config_archive_path': '/opt/archives',
            'config_services_hostpath': '/opt/services',
            'config_home_directory': expanduser("~"),
            'now_date': now.strftime("%Y-%m-%d"),
            'now_hour': now.strftime("%H-%M"),
            'now_hour_regular': now.strftime("%H:%M:%S"),
            'now_bup': now.strftime("%Y-%m-%d-%H%M%S"),
        })
        return vals


    def reset_keys(self, cr, uid, ids, context={}):
        container_obj = self.pool.get('clouder.container')
        container_ids = container_obj.search(cr, uid, [], context=context)
        container_obj.reset_key(cr, uid, container_ids, context=context)
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        config = self.pool.get('ir.model.data').get_object(cr, uid, 'clouder', 'clouder_settings')
        self.write(cr, uid, [config.id], {'end_reset_keys': now}, context=context)
        cr.commit()


    def save_all(self, cr, uid, ids, context={}):
        container_obj = self.pool.get('clouder.container')
        container_link_obj = self.pool.get('clouder.container.link')
        base_obj = self.pool.get('clouder.base')
        context.update({'clouder-self': self, 'clouder-cr': cr, 'clouder-uid': uid})

        backup_ids = container_obj.search(cr, uid, [('application_id.type_id.name','=','backup')], context=context)
        for backup in container_obj.browse(cr, uid, backup_ids, context=context):
            vals = container_obj.get_vals(cr, uid, backup.id, context=context)
            ssh, sftp = execute.connect(vals['container_fullname'], username='backup', context=context)
            execute.execute(ssh, ['export BUP_DIR=/opt/backup/bup;', 'bup', 'fsck', '-r'], context)
            #http://stackoverflow.com/questions/1904860/how-to-remove-unreferenced-blobs-from-my-git-repo
            #https://github.com/zoranzaric/bup/tree/tmp/gc/Documentation
            #https://groups.google.com/forum/#!topic/bup-list/uvPifF_tUVs
            execute.execute(ssh, ['git', 'gc', '--prune=now'], context, path='/opt/backup/bup')
            execute.execute(ssh, ['export BUP_DIR=/opt/backup/bup;', 'bup', 'fsck', '-g'], context)
            ssh.close()
            sftp.close()

        context['save_comment'] = 'Save before upload_save'
        container_ids = container_obj.search(cr, uid, [('nosave','=',False)], context=context)
        container_obj.save(cr, uid, container_ids, context=context)
        base_ids = base_obj.search(cr, uid, [('nosave','=',False)], context=context)
        base_obj.save(cr, uid, base_ids, context=context)

        link_ids = container_link_obj.search(cr, uid, [('container_id.application_id.type_id.name','=','backup'),('name.code','=','backup-upl')], context=context)
        for link in container_link_obj.browse(cr, uid, link_ids, context=context):
            vals = container_link_obj.get_vals(cr, uid, link.id, context=context)
            container_link_obj.deploy(cr, uid, vals, context=context)

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        config = self.pool.get('ir.model.data').get_object(cr, uid, 'clouder', 'clouder_settings')
        self.write(cr, uid, [config.id], {'end_save_all': now}, context=context)
        cr.commit()

    def purge_expired_saves(self, cr, uid, ids, context={}):
        repo_obj = self.pool.get('clouder.save.repository')
        save_obj = self.pool.get('clouder.save.save')
        vals = self.get_vals(cr, uid, context=context)
        expired_saverepo_ids = repo_obj.search(cr, uid, [('date_expiration','!=',False),('date_expiration','<',vals['now_date'])], context=context)
        repo_obj.unlink(cr, uid, expired_saverepo_ids, context=context)
        expired_save_ids = save_obj.search(cr, uid, [('date_expiration','!=',False),('date_expiration','<',vals['now_date'])], context=context)
        save_obj.unlink(cr, uid, expired_save_ids, context=context)

    def purge_expired_logs(self, cr, uid, ids, context={}):
        log_obj = self.pool.get('clouder.log')
        vals = self.get_vals(cr, uid, context=context)
        expired_log_ids = log_obj.search(cr, uid, [('expiration_date','!=',False),('expiration_date','<',vals['now_date'])], context=context)
        log_obj.unlink(cr, uid, expired_log_ids, context=context)

    def launch_next_saves(self, cr, uid, ids, context={}):
        context['save_comment'] = 'Auto save'
        container_obj = self.pool.get('clouder.container')
        vals = self.get_vals(cr, uid, context=context)
        container_ids = container_obj.search(cr, uid, [('date_next_save','!=',False),('date_next_save','<',vals['now_date'] + ' ' + vals['now_hour_regular'])], context=context)
        container_obj.save(cr, uid, container_ids, context=context)
        base_obj = self.pool.get('clouder.base')
        vals = self.get_vals(cr, uid, context=context)
        base_ids = base_obj.search(cr, uid, [('date_next_save','!=',False),('date_next_save','<',vals['now_date'] + ' ' + vals['now_hour_regular'])], context=context)
        base_obj.save(cr, uid, base_ids, context=context)


    def reset_bases(self, cr, uid, ids, context={}):
        base_obj = self.pool.get('clouder.base')
        base_ids = base_obj.search(cr, uid, [('reset_each_day','=',True)], context=context)
        for base in base_obj.browse(cr, uid, base_ids, context=context):
            if base.parent_id:
                base_obj.reset_base(cr, uid, [base.id], context=context)
            else:
                base_obj.reinstall(cr, uid, [base.id], context=context)

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        config = self.pool.get('ir.model.data').get_object(cr, uid, 'clouder', 'clouder_settings')
        self.write(cr, uid, [config.id], {'end_reset_bases': now}, context=context)
        cr.commit()

    def cron_daily(self, cr, uid, ids, context={}):
        self.reset_keys(cr, uid, [], context=context)
        self.purge_expired_saves(cr, uid, [], context=context)
        self.purge_expired_logs(cr, uid, [], context=context)
        self.save_all(cr, uid, [], context=context)
        self.reset_bases(cr, uid, [], context=context)
        return True

