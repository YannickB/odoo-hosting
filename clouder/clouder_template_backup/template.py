# -*- coding: utf-8 -*-
# Copyright 2015 Clouder SASU
# License LGPL-3.0 or later (http://gnu.org/licenses/lgpl.html).

try:
    from odoo import models, api
except ImportError:
    from openerp import models, api


class ClouderService(models.Model):
    """
    Add a property.
    """

    _inherit = 'clouder.service'

    @property
    def backup_method(self):
        """
        Property returning the backup method of the backup service.
        """
        backup_method = False
        if self.application_id.code == 'backup-sim':
            backup_method = 'simple'
        if self.application_id.code == 'backup-bup':
            backup_method = 'bup'

        return backup_method


class ClouderServiceLink(models.Model):
    """
    Add the method to manage transfers to the distant services.
    """
    _inherit = 'clouder.service.link'

    @api.multi
    def deploy_link(self):
        """
        Upload the whole backups to a distant service.
        """
        if self.target \
                and self.target.application_id.type_id.name ==\
                'backup-upload' \
                and self.service_id.application_id.type_id.name == 'backup':
            filegz = self.service_id.fullname + '.tar.gz'
            file_destination = '/opt/upload/' + filegz
            tmp_file = '/tmp/backup-upload/' + filegz

            service = self.service_id
            service.execute(['mkdir', '-p', '/tmp/backup-upload'])
            service.execute(['tar', 'czf', tmp_file, '-C /opt/backup', '.'])

            service.send(
                self.home_directory + '/.ssh/config',
                '/home/backup/.ssh/config', username='backup')
            service.send(
                self.home_directory + '/.ssh/keys/' +
                self.target.node_id.fulldomain + '.pub',
                '/home/backup/.ssh/keys/' +
                self.target.node_id.fulldomain + '.pub',
                username='backup')
            service.send(
                self.home_directory + '/.ssh/keys/' +
                self.target.node_id.fulldomain,
                '/home/backup/.ssh/keys/' +
                self.target.node_id.fulldomain, username='backup')
            service.execute([
                'chmod', '-R', '700', '/home/backup/.ssh'], username='backup')

            self.target.node_id.execute([
                'mkdir', '-p', '/tmp/backup-upload'])
            service.execute([
                'rsync', "-e 'ssh -o StrictHostKeyChecking=no'", '-ra',
                tmp_file, self.target.node_id.fulldomain + ':' + tmp_file],
                username='backup')
            service.execute(['rm', tmp_file])
            self.target.node_id.execute([
                'docker', 'cp',
                tmp_file, self.target.name + ':' + file_destination])
            self.target.node_id.execute(['rm', tmp_file])

#            service.self.execute(['rm', '/home/backup/.ssh/keys/*'],
#                                   username='backup')

            if self.target.options['protocol']['value'] == 'ftp':
                self.target.execute([
                    'lftp',
                    'ftp://' + self.target.options['login']['value'] +
                    ':' + self.target.options['password']['value'] + '@' +
                    self.target.options['host']['value'],
                    '-e', '"rm ' + filegz + '; quit"'])
                self.target.execute([
                    'lftp',
                    'ftp://' + self.target.options['login']['value'] +
                    ':' + self.target.options['password']['value'] + '@' +
                    self.target.options['host']['value'],
                    '-e', '"put ' + file_destination + '; quit"'])

        return super(ClouderServiceLink, self).deploy_link()

    @api.multi
    def purge_link(self):
        """
        Remove the backups on the distant service.
        """
        if self.target \
                and self.target.application_id.type_id.name ==\
                'backup-upload' \
                and self.service_id.application_id.type_id.name == 'backup':
            directory = '/opt/upload/' + self.service_id.name
            self.target.execute(['rm', '-rf', directory])
        return super(ClouderServiceLink, self).purge_link()
