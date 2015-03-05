# -*- coding: utf-8 -*-
# #############################################################################
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
import re

from datetime import datetime

import logging

_logger = logging.getLogger(__name__)


class ClouderConfigBackupMethod(models.Model):
    _name = 'clouder.config.backup.method'
    _description = 'Backup Method'

    name = fields.Char('Name', size=64, required=True)


class ClouderConfigSettings(models.Model):
    _name = 'clouder.config.settings'
    _description = 'Clouder configuration'

    name = fields.Char('Name', size=64)
    email_sysadmin = fields.Char('Email SysAdmin', size=128)
    end_reset_keys = fields.Datetime('Last Reset Keys ended at')
    end_save_all = fields.Datetime('Last Save All ended at')
    end_reset_bases = fields.Datetime('Last Reset Bases ended at')

    @property
    def now_date(self):
        return self.env['clouder.model'].now_date

    @property
    def now_hour_regular(self):
        return self.env['clouder.model'].now_hour_regular

    # @api.multi
    # def get_vals(self):
    #     config = self.env.ref('clouder.clouder_settings')
    #
    #     vals = {}
    #
    #     if not config.email_sysadmin:
    #         raise except_orm(_('Data error!'),
    #             _("You need to specify the sysadmin email in configuration"))
    #
    #
    #     now = datetime.now()
    #     vals.update({
    #         'config_email_sysadmin': config.email_sysadmin,
    #         'config_archive_path': '/opt/archives',
    #         'config_services_hostpath': '/opt/services',
    #         'config_home_directory': expanduser("~"),
    #         'now_date': now.strftime("%Y-%m-%d"),
    #         'now_hour': now.strftime("%H-%M"),
    #         'now_hour_regular': now.strftime("%H:%M:%S"),
    #         'now_bup': now.strftime("%Y-%m-%d-%H%M%S"),
    #     })
    #     return vals

    @api.one
    @api.constrains('email_sysadmin')
    def _validate_data(self):
        if self.email_sysadmin \
                and not re.match("^[\w\d_.@-]*$", self.email_sysadmin):
            raise except_orm(_('Data error!'), _(
                "Sysadmin email can only contains letters, "
                "digits, underscore, - and @"))

    @api.multi
    def reset_keys(self):

        containers = self.env['clouder.container'].search([])
        if containers:
            containers.deploy_key()

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.env.ref('clouder.clouder_settings').end_reset_keys = now
        self.env.cr.commit()

    @api.multi
    def save_all(self):
        self = self.with_context(save_comment='Save before upload_save')

        backups = self.env['clouder.container'].search(
            [('application_id.type_id.name', '=', 'backup')])
        for backup in backups:
            vals = backup.get_vals()
            ssh = backup.connect(vals['container_fullname'],
                                       username='backup')
            backup.execute(ssh,
                           ['export BUP_DIR=/opt/backup/bup;', 'bup', 'fsck',
                            '-r'])
            #http://stackoverflow.com/questions/1904860/how-to-remove-unreferenced-blobs-from-my-git-repo
            #https://github.com/zoranzaric/bup/tree/tmp/gc/Documentation
            #https://groups.google.com/forum/#!topic/bup-list/uvPifF_tUVs
            backup.execute(ssh, ['git', 'gc', '--prune=now'],
                           path='/opt/backup/bup')
            backup.execute(ssh,
                           ['export BUP_DIR=/opt/backup/bup;', 'bup', 'fsck',
                            '-g'])
            ssh.close()

        containers = self.env['clouder.container'].search(
            [('nosave', '=', False)])
        if containers:
            containers.save()

        bases = self.env['clouder.base'].search([('nosave', '=', False)])
        if bases:
            bases.save()

        links = self.env['clouder.container.link'].search(
            [('container_id.application_id.type_id.name', '=', 'backup'),
             ('name.application_id.code', '=', 'backup-upl')])
        for link in links:
            link.deploy()

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.env.ref('clouder.clouder_settings').end_save_all = now
        self.env.cr.commit()

    @api.multi
    def purge_expired_saves(self):
        self.env['clouder.save.repository'].search(
            [('date_expiration', '!=', False),
             ('date_expiration', '<', self.now_date)]).unlink()
        self.env['clouder.save.save'].search([('date_expiration', '!=', False),
                                              ('date_expiration', '<',
                                               self.now_date)]).unlink()

    @api.multi
    def purge_expired_logs(self):
        self.env['clouder.log'].search([('expiration_date', '!=', False), (
            'expiration_date', '<', self.now_date)]).unlink()

    @api.multi
    def launch_next_saves(self):
        self = self.with_context(save_comment='Auto save')
        containers = self.env['clouder.container'].search([
            ('date_next_save', '!=', False),
            ('date_next_save', '<',
             self.now_date + ' ' + self.now_hour_regular)])
        if containers:
            containers.save()
        bases = self.env['clouder.base'].search([
            ('date_next_save', '!=', False),
            ('date_next_save', '<',
             self.now_date + ' ' + self.now_hour_regular)])
        if bases:
            bases.save()

    @api.multi
    def reset_bases(self):
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
        self.reset_keys()
        self.purge_expired_saves()
        self.purge_expired_logs()
        self.save_all()
        self.reset_bases()
        return True

