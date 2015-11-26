# -*- coding: utf-8 -*-
##############################################################################
#
# Author: Yannick Buron
# Copyright 2015, TODAY Clouder SASU
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License with Attribution
# clause as published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License with
# Attribution clause along with this program. If not, see
# <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp import models, fields, api, _
from openerp.exceptions import except_orm
import re

from datetime import datetime


class ClouderConfigBackupMethod(models.Model):
    """
    Define the config.backup.method object, which represent all backup method
    available for save.
    """

    _name = 'clouder.config.backup.method'
    _description = 'Backup Method'

    name = fields.Char('Name', required=True)


class ClouderConfigSettings(models.Model):
    """
    Define the config.settings object, which is used to store
    the clouder configuration.
    """

    _name = 'clouder.config.settings'
    _description = 'Clouder configuration'

    name = fields.Char('Name')
    email_sysadmin = fields.Char('Email SysAdmin')
    end_reset_keys = fields.Datetime('Last Reset Keys ended at')
    end_save_all = fields.Datetime('Last Save All ended at')
    end_reset_bases = fields.Datetime('Last Reset Bases ended at')

    @property
    def now_date(self):
        """
        Property returning the now_date property of clouder.model.
        """
        return self.env['clouder.model'].now_date

    @property
    def now_hour_regular(self):
        """
        Property returning the now_hour_regular property of clouder.model.
        """
        return self.env['clouder.model'].now_hour_regular

    @api.one
    @api.constrains('email_sysadmin')
    def _validate_data(self):
        """
        Check that the sysadmin email does not contain any forbidden
        characters.
        """
        if self.email_sysadmin \
                and not re.match("^[\w\d_.@-]*$", self.email_sysadmin):
            raise except_orm(_('Data error!'), _(
                "Sysadmin email can only contains letters, "
                "digits, underscore, - and @"))

    @api.multi
    def reset_keys(self):
        """
        Reset all keys for all containers managed by the clouder.
        """
        containers = self.env['clouder.container'].search([])
        for container in containers:
            container.deploy_key()

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.env.ref('clouder.clouder_settings').end_reset_keys = now
        self.env.cr.commit()

    @api.multi
    def save_all(self):
        """
        Execute some maintenance on backup containers, and force a save
        on all containers and bases.
        """
        self = self.with_context(save_comment='Save before upload_save')

        backups = self.env['clouder.container'].search(
            [('application_id.type_id.name', '=', 'backup')])
        for backup in backups:
            ssh = backup.connect(backup.fullname,
                                 username='backup')
            backup.execute(ssh,
                           ['export BUP_DIR=/opt/backup/bup;', 'bup', 'fsck',
                            '-r'])
            # http://stackoverflow.com/questions/1904860/
            #     how-to-remove-unreferenced-blobs-from-my-git-repo
            # https://github.com/zoranzaric/bup/tree/tmp/gc/Documentation
            # https://groups.google.com/forum/#!topic/bup-list/uvPifF_tUVs
            backup.execute(ssh, ['git', 'gc', '--prune=now'],
                           path='/opt/backup/bup')
            backup.execute(ssh,
                           ['export BUP_DIR=/opt/backup/bup;', 'bup', 'fsck',
                            '-g'])
            ssh.close()

        containers = self.env['clouder.container'].search(
            [('nosave', '=', False)])
        for container in containers:
            container.save()

        bases = self.env['clouder.base'].search([('nosave', '=', False)])
        for base in bases:
            base.save()

        links = self.env['clouder.container.link'].search(
            [('container_id.application_id.type_id.name', '=', 'backup'),
             ('name.name.code', '=', 'backup-upl')])
        for link in links:
            link.deploy_()

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.env.ref('clouder.clouder_settings').end_save_all = now
        self.env.cr.commit()

    @api.multi
    def purge_expired_saves(self):
        """
        Purge all expired saves.
        """
        self.env['clouder.save.repository'].search(
            [('date_expiration', '!=', False),
             ('date_expiration', '<', self.now_date)]).unlink()
        self.env['clouder.save'].search([
            ('date_expiration', '!=', False),
            ('date_expiration', '<', self.now_date)]).unlink()

    @api.multi
    def purge_expired_logs(self):
        """
        Purge all expired logs.
        """
        self.env['clouder.log'].search([('expiration_date', '!=', False), (
            'expiration_date', '<', self.now_date)]).unlink()

    @api.multi
    def launch_next_saves(self):
        """
        Save all containers and bases which passed their next save date.
        """
        self = self.with_context(save_comment='Auto save')
        containers = self.env['clouder.container'].search([
            ('date_next_save', '!=', False),
            ('date_next_save', '<',
             self.now_date + ' ' + self.now_hour_regular)])
        for container in containers:
            container.save()
        bases = self.env['clouder.base'].search([
            ('date_next_save', '!=', False),
            ('date_next_save', '<',
             self.now_date + ' ' + self.now_hour_regular)])
        for base in bases:
            base.save()

    @api.multi
    def reset_bases(self):
        """
        Reset all bases marked for reset.
        """
        bases = self.env['clouder.base'].search(
            [('reset_each_day', '=', True)])
        for base in bases:
            if base.parent_id:
                base.reset_base()
            else:
                bases.reinstall()

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.env.ref('clouder.clouder_settings').end_reset_bases = now
        self.env.cr.commit()

    @api.multi
    def cron_daily(self):
        """
        Call all actions which shall be executed daily.
        """
        self.reset_keys()
        self.purge_expired_saves()
        self.purge_expired_logs()
        self.save_all()
        self.reset_bases()
        return True

    @api.multi
    def reset_all_jobs(self):
        self.env.cr.execute(
            "update queue_job set state='done' "
            "where state in ('started', 'enqueued')")