# -*- coding: utf-8 -*-
# Copyright 2015 Clouder SASU
# License LGPL-3.0 or later (http://gnu.org/licenses/lgpl.html).

try:
    from odoo import models, api
except ImportError:
    from openerp import models, api

import yaml
import time


class ClouderNode(models.Model):
    """
    """

    _inherit = 'clouder.node'

    @api.multi
    def configure_exec(self):
        """
        """

        super(ClouderNode, self).configure_exec()

        if self.executor == 'salt':

            if not self.env.ref('clouder.clouder_settings').salt_master_id:
                application = self.env.ref('clouder.application_salt_master')
                master = self.env['clouder.service'].create({
                    'environment_id': self.environment_id.id,
                    'suffix': 'salt-master',
                    'application_id': application.id,
                    'node_id': self.id,
                })
            else:
                master = self.salt_master

            application = self.env.ref('clouder.application_salt_minion')
            self.env['clouder.service'].create({
                'environment_id': self.environment_id.id,
                'suffix': 'salt-minion',
                'application_id': application.id,
                'node_id': self.id,
            })

            time.sleep(3)

            master.execute(['salt-key', '-y', '--accept=' + self.fulldomain])

            master.execute([
                'echo "  \'%s\':\n#END %s" >> /srv/pillar/top.sls' %
                (self.fulldomain, self.fulldomain)])

    @api.multi
    def purge(self):
        """
        """

        if self.executor == 'salt':

            master = self.salt_master
            if master:
                try:
                    master.execute([
                        'sed', '-i',
                        '"/  \'' + self.fulldomain + r'\'/,/END\s' +
                        self.fulldomain + '/d"',
                        '/srv/pillar/top.sls'])
                    master.execute([
                        'rm',
                        '/etc/salt/pki/master/minions/%s' % (self.fulldomain)])
                    master.execute([
                        'rm', '/etc/salt/pki/master/minions_denied/%s' %
                        (self.fulldomain)])
                except:
                    pass
            try:
                minion = self.env['clouder.service'].search(
                    [('environment_id', '=', self.environment_id.id),
                     ('node_id', '=', self.id),
                     ('suffix', '=', 'salt-minion')])
                minion.unlink()
            except:
                pass

        super(ClouderNode, self).purge()


class ClouderService(models.Model):
    """
    """

    _inherit = 'clouder.service'

    @api.multi
    def hook_deploy_special_args(self, cmd):
        cmd = super(ClouderService, self).hook_deploy_special_args(cmd)
        if self.application_id.type_id.name == 'salt-minion':
            cmd.extend(['--pid host'])
        return cmd

    @api.multi
    def deploy_salt(self):

        self.purge_salt()

        # if not self.childs_ids:
        res = self.get_service_res()
        self.image_id.build_image(
            self, self.salt_master, expose_ports=res['expose_ports'])

        data = {
            'name': self.name,
            'image': self.name,
            'from': self.image_id.parent_from,
            'secretkey': 'registry_password' in self.options and
                         self.options['registry_password']['value'],
        }
        bases = {}
        if self.application_id.update_bases:
            for base in self.env['clouder.base'].search(
                    [('service_id', '=', self.id)]):
                bases[base.fullname_] = base.fullname_
            if self.parent_id:
                for base in self.env['clouder.base'].search(
                        [('service_id', '=',
                          self.parent_id.service_id.id)]):
                    bases[base.fullname_] = base.fullname_
        data['bases'] = [base for key, base in bases.iteritems()]
        data.update(self.get_service_res())

        links = []
        for link in data['links']:
            links.append(link['name'] + ':' + link['code'])
        data['links'] = links

        data = {self.name: data}

        if 'registry' in self.links:
            registry_domain = \
                self.links['registry'].target.base_ids[0].fulldomain
            data[self.name + '-docker-registries'] = {
                'https://' + registry_domain + '/v1/': {
                    'email': 'admin@example.net',
                    'username': self.name,
                    'password': self.options['registry_password']['value']
                }
            }

        data = yaml.safe_dump(data, default_flow_style=False)
        self.salt_master.execute(
            ['echo "' + data + '" > /srv/pillar/services/' +
             self.name + '.sls'])
        self.salt_master.execute(
            ['sed', '-i', '"/' + self.node_id.fulldomain +
             '\':/a +++    - services/' + self.name + '"',
             '/srv/pillar/top.sls'])
        self.salt_master.execute(
            ['sed', '-i', '"s/+++//g"', '/srv/pillar/top.sls'])
        self.salt_master.execute(
            ['salt', self.node_id.fulldomain, 'saltutil.refresh_pillar'])

    @api.multi
    def deploy(self):
        if self.application_id.type_id.name == 'salt-master':
            if not self.env.ref('clouder.clouder_settings').salt_master_id:
                self.env.ref('clouder.clouder_settings').salt_master_id = \
                    self.id

        if self.application_id.type_id.name == 'salt-minion':
            if not self.node_id.salt_minion_id:
                self.node_id.salt_minion_id = self.id
        super(ClouderService, self).deploy()

    @api.multi
    def deploy_post(self):
        super(ClouderService, self).deploy_post()

        if self.application_id.type_id.name == 'salt-master' \
                and self.application_id.check_tags(['exec']):
            self.execute(['sed', '-i',
                          '"s/#publish_port: 4505/publish_port: ' +
                          self.ports['salt']['hostport'] + '/g"',
                          '/etc/salt/master'])
            self.execute(['sed', '-i', '"s/#ret_port: 4506/ret_port: ' +
                         self.ports['saltret']['hostport'] + '/g"',
                         '/etc/salt/master'])

            certfile = '/etc/ssl/private/cert.pem'
            keyfile = '/etc/ssl/private/key.pem'

            self.execute(['rm', certfile])
            self.execute(['rm', keyfile])

            self.execute([
                'openssl', 'req', '-x509', '-nodes', '-days', '365',
                '-newkey', 'rsa:2048', '-out', certfile, ' -keyout',
                keyfile, '-subj', '"/C=FR/L=Paris/O=Clouder/CN=' +
                self.node_id.name + '"'])

        if self.application_id.type_id.name == 'salt-minion':
            config_file = '/etc/salt/minion'
            self.execute([
                'sed', '-i',
                '"s/#master: salt/master: ' +
                self.env.ref('clouder.clouder_settings').
                salt_master_id.node_id.ip + '/g"',
                config_file])
            self.execute([
                'sed', '-i',
                '"s/#master_port: 4506/master_port: ' +
                str(self.env.ref('clouder.clouder_settings').
                    salt_master_id.ports['saltret']['hostport']) + '/g"',
                config_file])
            self.execute([
                'sed', '-i',
                '"s/#id:/id: ' + self.node_id.fulldomain + '/g"',
                config_file])

    @api.multi
    def purge_salt(self):

        if self.salt_master:
            self.salt_master.execute([
                'sed', '-i', r'"/services\/' + self.name + '/d"',
                '/srv/pillar/top.sls'])
            self.salt_master.execute([
                'rm', '-rf', '/srv/salt/services/build_' + self.name])
            self.salt_master.execute([
                'rm', '-rf', '/srv/pillar/services/' + self.name + '.sls'])


class ClouderServiceLink(models.Model):
    """
    """

    _inherit = 'clouder.service.link'

    @api.multi
    def deploy_link(self):
        """
        """
        super(ClouderServiceLink, self).deploy_link()
        if self.target \
                and self.target.application_id.type_id.name == 'shinken'\
                and self.service_id.application_id.type_id.name == \
                'salt-minion':

            self.target.deploy_shinken_node(self.service_id)

    @api.multi
    def purge_link(self):
        """
        """
        super(ClouderServiceLink, self).purge_link()
        if self.target \
                and self.target.application_id.type_id.name == 'shinken'\
                and self.service_id.application_id.type_id.name == \
                'salt-minion':

            self.target.purge_shinken_node(self.service_id)


class ClouderBase(models.Model):
    """
    """

    _inherit = 'clouder.base'

    @api.multi
    def deploy_salt(self):

        self.purge_salt()

        data = {
            'name': self.fullname_,
            'host': self.fulldomain,
            'user': self.admin_name,
            'password': self.admin_password,
        }
        data = yaml.safe_dump({self.fullname_: data}, default_flow_style=False)
        self.salt_master.execute([
            'echo "' + data + '" > /srv/pillar/bases/' +
            self.fullname_ + '.sls'])
        self.salt_master.execute([
            'sed', '-i',
            '"/' + self.service_id.node_id.name +
            '\':/a +++    - bases/' + self.fullname_ +
            '"',  '/srv/pillar/top.sls'])
        self.salt_master.execute([
            'sed', '-i', '"s/+++//g"', '/srv/pillar/top.sls'])
        self.salt_master.execute([
            'salt', self.service_id.node_id.fulldomain,
            'saltutil.refresh_pillar'])

    @api.multi
    def purge_salt(self):

        self.salt_master.execute([
            'sed', '-i', r'"/bases\/' + self.name + '/d"',
            '/srv/pillar/top.sls'])
        self.salt_master.execute([
            'rm', '-rf', '/srv/pillar/bases/' + self.name + '.sls'])
