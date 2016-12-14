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

import os.path

from odoo import api, fields, models, modules
from datetime import datetime, timedelta


class ClouderBase(models.Model):
    """ Add methods to manage the proxy specificities.

    Attributes:
        DELTA_CERT_RENEW: (datetime.timedelta) Timedelta for use when
            determining the renewal time after generating a cert.
    """

    _inherit = 'clouder.base'
    DELTA_CERT_RENEW = timedelta(days=45)

    dh_param = fields.Text('Diffie-Helman Params')

    @property
    def nginx_configfile(self):
        """
        Property returning the nginx config file.
        """
        return '/etc/nginx/sites-available/' + self.fullname

    @api.multi
    def generate_cert_exec(self):
        """
        Generate a new certificate
        """
        res = super(ClouderBase, self).generate_cert_exec()
        proxy_links = self._get_proxy_links()
        if proxy_links:
            proxy_link = proxy_links[0]
            proxy = proxy_link.target
            proxy_link.purge_link()
            webroot = '/var/www/' + self.fullname + '-certs'
            proxy.execute(['mkdir -p ' + webroot])
            proxy.send(
                modules.get_module_path(
                    'clouder_template_proxy'
                ) + '/res/nginx.config', self.nginx_configfile)
            proxy.execute([
                'ln', '-s', self.nginx_configfile,
                '/etc/nginx/sites-enabled/' + self.fullname])
            proxy.execute([
                'sed', '-i', '"s/BASE/' + self.name + '/g"',
                self.nginx_configfile])
            domain = self.fulldomain
            if self.is_root:
                domain = domain + ' ' + self.name + '.' + self.fulldomain
            proxy.execute([
                'sed', '-i', '"s/DOMAIN/' + domain +
                '/g"', self.nginx_configfile])
            proxy.execute([
                'sed', '-i', '"s/REPO/' + self.fullname +
                '/g"', self.nginx_configfile])
            proxy.execute(['nginx', '-s', 'reload'])
            domain = self.fulldomain
            if self.is_root:
                domain = domain + ' -d ' + self.name + '.' + self.fulldomain
            proxy.execute([
                'certbot certonly --webroot -w ' +
                webroot + ' -d ' + domain + ' -m ' + proxy.email_sysadmin +
                ' --agree-tos'])
            key = proxy.execute([
                'cat',
                '/etc/letsencrypt/live/' + self.fulldomain + '/privkey.pem'])
            cert = proxy.execute([
                'cat',
                '/etc/letsencrypt/live/' + self.fulldomain + '/fullchain.pem'])
            if key:
                self.write({
                    'cert_key': key,
                    'cert_cert': cert,
                    'cert_renewal_date': fields.Datetime.to_string(
                        datetime.now() + self.DELTA_CERT_RENEW
                    ),
                    'dh_param': self._create_dh_param(proxy),
                })
            proxy.execute([
                'rm',
                '/etc/nginx/sites-enabled/' + self.fullname])
            proxy.execute(['rm', self.nginx_configfile])
            proxy.execute(['nginx', '-s', 'reload'])
            proxy.execute(['rm -rf ' + webroot])
            proxy_link.deploy_link()
        return res

    @api.multi
    def renew_cert_exec(self):
        res = super(ClouderBase, self).renew_cert_exec()
        proxy_links = self._get_proxy_links()
        if proxy_links:
            proxy_link = proxy_links[0]
            proxy = proxy_link.target
            proxy.execute([
                'echo', '"' + self.cert_cert + '"', '>',
                '/etc/letsencrypt/live/' + self.fulldomain + '/fullchain.pem'
            ])
            proxy.execute([
                'echo', '"' + self.cert_key + '"', '>',
                '/etc/letsencrypt/live/' + self.fulldomain + '/privkey.pem'])
            proxy.execute([
                '/opt/letsencrypt/letsencrypt-auto renew --force-renew'])
            key = proxy.execute([
                'cat',
                '/etc/letsencrypt/live/' + self.fulldomain + '/privkey.pem'])
            cert = proxy.execute([
                'cat',
                '/etc/letsencrypt/live/' + self.fulldomain + '/fullchain.pem'])
            self.write({
                'cert_key': key,
                'cert_cert': cert,
                'cert_renewal_date': fields.Datetime.to_string(
                    datetime.now() + self.DELTA_CERT_RENEW
                ),
                'dh_param': self._create_dh_param(proxy),
            })
        return res

    @api.multi
    def _create_dh_param(self, proxy, length=4096):
        """ It creates & returns new Diffie-Helman parameters

        Args:
            proxy: (clouder.container) Proxy target to execute on
            length: (int) Bit length
        Returns:
            (str) Diffie-helman parameters
        """
        self.ensure_one()
        dh_dir = '/etc/ssl/dh_param'
        dh_path = os.path.join(dh_dir, '%s.pem' % self.fulldomain)
        proxy.execute(['mkdir', '-p', dh_dir])
        proxy.execute([
            'openssl', 'dhparam', '-out', dh_path, str(length),
        ])
        return proxy.execute(['cat', dh_path])

    @api.multi
    def _get_proxy_links(self):
        """ It returns the ``clouder.base.links`` for the current base """
        self.ensure_one()
        BaseLink = self.env['clouder.base.link']
        return BaseLink.search([
            ('base_id', '=', self.id),
            ('name.type_id.name', '=', 'proxy'),
            ('target', '!=', False),
        ])


class ClouderBaseLink(models.Model):
    """
    Add methods to manage the proxy specificities.
    """

    _inherit = 'clouder.base.link'

    @api.multi
    def nginx_config_update(self, target):
        return

    @api.multi
    def deploy_link(self):
        """
        Configure the proxy to redirect to the application port.
        """
        super(ClouderBaseLink, self).deploy_link()
        if self.name.type_id.name == 'proxy':
            if not self.base_id.ssl_only:
                configfile = 'proxy.config'
            else:
                configfile = 'proxy-sslonly.config'
            target = self.target
            module_path = modules.get_module_path(
                'clouder_template_' + self.base_id.application_id.type_id.name)
            proxy_module_path = modules.get_module_path(
                'clouder_template_proxy'
            )
            flag = True

            # Always transfer proxy and ssl settings
            for config in ['nginx-ssl', 'nginx-proxy']:
                target.send(
                    os.path.join(
                        proxy_module_path, 'res', '%s.config' % config,
                    ),
                    os.path.join('/etc/nginx/conf.d', config),
                )

            if module_path:
                configtemplate = module_path + '/res/' + configfile
                if self.local_file_exist(configtemplate):
                    target.send(
                        configtemplate, self.base_id.nginx_configfile)
                    flag = False
            if flag:
                target.send(
                    modules.get_module_path(
                        'clouder_template_proxy'
                    ) + '/res/' + configfile, self.base_id.nginx_configfile)

            if self.base_id.is_root:
                target.send(
                    os.path.join(
                        proxy_module_path, 'res', 'proxy-root.config',
                    ),
                    '%s-root' % self.base_id.nginx_configfile,
                )
                target.execute([
                    'cat', self.base_id.nginx_configfile + '-root',
                    '>>',  self.base_id.nginx_configfile])
                target.execute(['rm', self.base_id.nginx_configfile + '-root'])
            target.execute([
                'sed', '-i', '"s/BASE/' + self.base_id.name + '/g"',
                self.base_id.nginx_configfile])
            target.execute([
                'sed', '-i', '"s/DOMAIN/' + self.base_id.fulldomain +
                '/g"', self.base_id.nginx_configfile])

            node = self.base_id.service_id.node_id.private_ip
            type = 'hostport'
            if self.runner == 'swarm':
                node = self.base_id.service_id.host
                type = 'local_port'
            if 'http' in self.base_id.service_id.ports:
                protocol = 'http'
                port = self.base_id.service_id.ports['http'][type]
            if 'https' in self.base_id.service_id.ports:
                protocol = 'https'
                port = self.base_id.service_id.ports['https'][type]

            target.execute([
                'sed', '-i', '"s/SERVER/' +
                node + '/g"',
                self.base_id.nginx_configfile])
            target.execute([
                'sed', '-i', '"s/PORT/' +
                port +
                '/g"', self.base_id.nginx_configfile])
            target.execute([
                'sed', '-i', '"s/PROTOCOL/' +
                protocol +
                '/g"', self.base_id.nginx_configfile])

            self.nginx_config_update(target)
            # self.deploy_prepare_apache(cr, uid, vals, context)
            cert_file = '/etc/ssl/certs/' + self.base_id.fulldomain + '.crt'
            key_file = '/etc/ssl/private/' + self.base_id.fulldomain + '.key'
            if self.base_id.cert_cert and self.base_id.cert_key:
                target.execute([
                    'echo', '"' + self.base_id.cert_cert + '"', '>', cert_file
                ])
                target.execute([
                    'echo', '"' + self.base_id.cert_key + '"', '>', key_file])
            elif self.base_id.domain_id.cert_cert\
                    and self.base_id.domain_id.cert_key:
                target.execute([
                    'echo', '"' + self.base_id.domain_id.cert_cert + '"',
                    '>', cert_file])
                target.execute([
                    'echo', '"' + self.base_id.domain_id.domain_cert_key + '"',
                    '>', key_file])
            else:
                target.execute([
                    'openssl', 'req', '-x509', '-nodes', '-days', '365',
                    '-newkey', 'rsa:2048', '-out', cert_file,
                    ' -keyout', key_file, '-subj', '"/C=FR/L=Paris/O=' +
                    self.base_id.domain_id.organisation +
                    '/CN=' + self.base_id.name +
                    '.' + self.base_id.domain_id.name + '"'])

            target.execute([
                'ln', '-s', self.base_id.nginx_configfile,
                '/etc/nginx/sites-enabled/' + self.base_id.fullname])
            target.execute(['nginx', '-s', 'reload'])

    @api.multi
    def purge_link(self):
        """
        Remove the redirection.
        """
        super(ClouderBaseLink, self).purge_link()
        if self.name.type_id.name == 'proxy':
            target = self.target
            target.execute([
                'rm',
                '/etc/nginx/sites-enabled/' + self.base_id.fullname])
            target.execute(['rm', self.base_id.nginx_configfile])
            target.execute([
                'rm', '/etc/ssl/certs/' + self.base_id.fulldomain + '.*'])
            target.execute([
                'rm', '/etc/ssl/private/' + self.base_id.fulldomain + '.*'])
            target.execute(['nginx', '-s', 'reload'])
