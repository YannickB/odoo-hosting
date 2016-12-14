# -*- coding: utf-8 -*-
# Copyright 2015 Clouder SASU
# License LGPL-3.0 or later (http://gnu.org/licenses/lgpl.html).

import os.path
import re

from odoo import models, fields, api


class ClouderConfigSettings(models.Model):
    """
    Define the config.settings object, which is used to store
    the clouder configuration.
    """

    _name = 'clouder.config.settings'
    _description = 'Clouder configuration'
    _inherit = ['clouder.model']

    name = fields.Char('Name')
    email_sysadmin = fields.Char('Email SysAdmin')
    master_id = fields.Many2one(
        'clouder.node', 'Master')
    salt_master_id = fields.Many2one(
        'clouder.service', 'Salt Master', readonly=True)
    runner = fields.Selection(
        lambda s: s._get_runners(),
        required=True, default='swarm')
    runner_id = fields.Many2one('clouder.service', 'Runner')
    executor = fields.Selection(
        lambda s: s._get_executors(),
        required=True, default='ssh')
    compose = fields.Boolean('Compose? (Experimental)', default=False)
    end_reset_keys = fields.Datetime('Last Reset Keys ended at')
    end_backup_all = fields.Datetime('Last Backup All ended at')
    end_update_services = fields.Datetime('Last Update Services ended at')
    end_reset_bases = fields.Datetime('Last Reset Bases ended at')
    end_certs_renewal = fields.Datetime('Last Certs Renewal ended at')
    provider_ids = fields.One2many(
        'clouder.provider', 'config_id', 'Providers')

    @api.multi
    def _get_runners(self):
        return [
            ('engine', 'Docker Engine'), ('swarm', 'Docker Swarm'),
            ('custom', 'Custom Runner')]

    @api.multi
    def _get_executors(self):
        return [('ssh', 'SSH'), ('salt', 'Salt (Experimental)')]

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

    @property
    def settings_id(self):
        """ It provides the Clouder settings record """
        return self.env.ref('clouder.clouder_settings')

    @api.multi
    @api.constrains('email_sysadmin')
    def _check_email_sysadmin(self):
        """
        Check that the sysadmin email does not contain any forbidden
        characters.
        """
        if self.email_sysadmin \
                and not re.match(r"^[\w\d_.@-]*$", self.email_sysadmin):
            self.raise_error(
                "Sysadmin email can only contains letters, "
                "digits, underscore, - and @",
            )

    @api.multi
    def backup_all(self):
        self.do('backup_all', 'backup_all_exec')

    @api.multi
    def backup_all_exec(self):
        """
        Execute some maintenance on backup services, and force a backup
        on all services and bases.
        """

        context = {
            'backup_comment': 'Backup before upload_backup',
        }

        with self.with_context(**context).private_env() as self:

            backup_dir = os.path.join(self.BACKUP_DIR, 'bup')
            ClouderService = self.env['clouder.service']
            ServiceLink = self.env['clouder.service.link']
            ClouderBase = self.env['clouder.base'].with_context(**context)

            backups = ClouderService.search([
                ('application_id.type_id.name', '=', 'backup'),
            ])
            for backup in backups:
                backup.execute([
                    'export BUP_DIR="%s";' % backup_dir,
                    'bup', 'fsck', '-r',
                ],
                    username="backup",
                )
                # http://stackoverflow.com/questions/1904860/
                #     how-to-remove-unreferenced-blobs-from-my-git-repo
                # https://github.com/zoranzaric/bup/tree/tmp/gc/Documentation
                # https://groups.google.com/forum/#!topic/bup-list/uvPifF_tUVs
                backup.execute(
                    ['git', 'gc', '--prune=now'],
                    backup_dir,
                    username="backup",
                )
                backup.execute([
                    'export BUP_DIR="%s";' % backup_dir, 'bup', 'fsck', '-g',
                ],
                    username="backup",
                )

            domain = [('auto_backup', '=', True)]

            services = ClouderService.search(domain)
            for service in services:
                service.backup_exec()

            bases = ClouderBase.search(domain)
            for base in bases:
                base.backup_exec()

            links = ServiceLink.search([
                ('service_id.application_id.type_id.name', '=', 'backup'),
                ('name.code', '=', 'backup-upload'),
            ])
            for link in links:
                link.deploy_exec()

            now = fields.Datetime.now()

            for rec_id in self:
                rec_id.settings_id.end_backup_all = now

    @api.multi
    def purge_expired_backups(self):
        self.do('purge_expired_backups', 'purge_expired_backups_exec')

    @api.multi
    def purge_expired_backups_exec(self):
        """
        Purge all expired backups.
        """
        self.env['clouder.backup'].search([
            ('date_expiration', '!=', False),
            ('date_expiration', '<', self.now_date)]).unlink()

    @api.multi
    def launch_next_backups(self):
        self = self.with_context(no_enqueue=True)
        self.do('launch_next_backups', 'launch_next_backups_exec')

    @api.multi
    def launch_next_backups_exec(self):
        """
        Backup all services and bases which passed their next backup date.
        """
        self = self.with_context(no_enqueue=True, backup_comment='Auto backup')
        services = self.env['clouder.service'].search([
            ('auto_backup', '=', True),
            ('date_next_backup', '!=', False),
            ('date_next_backup', '<',
             self.now_date + ' ' + self.now_hour_regular)])
        for service in services:
            service.backup_exec()
        bases = self.env['clouder.base'].search([
            ('auto_backup', '=', True),
            ('date_next_backup', '!=', False),
            ('date_next_backup', '<',
             self.now_date + ' ' + self.now_hour_regular)])
        for base in bases:
            base.backup_exec()

    @api.multi
    def update_services(self):
        self.do('update_services', 'update_services_exec')

    @api.multi
    def update_services_exec(self):
        """
        """

        with self._private_env() as self:

            services = self.env['clouder.service'].search([
                ('application_id.update_strategy', '=', 'auto'),
            ])
            services.update_exec()

            now = fields.Datetime.now()

            for rec_id in self:
                rec_id.settings_id.end_update_services = now

    @api.multi
    def reset_bases(self):
        self.do('reset_bases', 'reset_bases_exec')

    @api.multi
    def reset_bases_exec(self):
        """
        Reset all bases marked for reset.
        """

        with self._private_env() as self:

            bases = self.env['clouder.base'].search([
                ('reset_each_day', '=', True),
            ])

            for base in bases:
                if base.parent_id:
                    base.reset_base()
                else:
                    bases.reinstall()

            now = fields.Datetime.now()

            for rec_id in self:
                rec_id.settings_id.end_reset_bases = now

    @api.multi
    def certs_renewal(self):
        self.do('certs_renewal', 'certs_renewal_exec')

    @api.multi
    def certs_renewal_exec(self):
        """
        Reset all bases marked for reset.
        """

        with self._private_env() as self:

            bases = self.env['clouder.base'].search([
                ('cert_renewal_date', '!=', False),
                ('cert_renewal_date', '<=', self.now_date),
            ])
            for base in bases:
                base.renew_cert()

            now = fields.Datetime.now()

            for rec_id in self:
                rec_id.settings_id.end_certs_renewal = now

    @api.multi
    def cron_daily(self):
        self = self.with_context(no_enqueue=True)
        self.do('cron_daily', 'cron_daily_exec')

    @api.multi
    def cron_daily_exec(self):
        """
        Call all actions which shall be executed daily.
        """
        self = self.with_context(no_enqueue=True)
        self.purge_expired_backups_exec()
        self.backup_all_exec()
        self.reset_bases_exec()
        self.certs_renewal_exec()
        return True

    @api.multi
    def reset_all_jobs(self):
        job_obj = self.env['queue.job']
        jobs = job_obj.search([
            ('state', 'in', ['pending', 'started', 'enqueued', 'failed'])])
        jobs.write({'state': 'done'})
        clouder_job_obj = self.env['clouder.job']
        clouder_jobs = clouder_job_obj.search([
            ('job_id', 'in', [j.id for j in jobs])])
        clouder_jobs.write({'state': 'failed'})
