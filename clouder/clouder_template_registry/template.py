# -*- coding: utf-8 -*-
# Copyright 2015 Clouder SASU
# License LGPL-3.0 or later (http://gnu.org/licenses/lgpl.html).

try:
    from odoo import models, api
except ImportError:
    from openerp import models, api

from ..tools import generate_random_password


class ClouderApplicationTypeOption(models.Model):
    """
    """

    _inherit = 'clouder.application.type.option'

    @api.multi
    def generate_default(self):
        res = super(ClouderApplicationTypeOption, self).generate_default()
        if self.name == 'registry_password':
            res = generate_random_password(20)
        return res


class ClouderService(models.Model):
    """
    Add some methods to manage specificities of the registry building.
    """

    _inherit = 'clouder.service'

    @api.multi
    def get_service_res(self):
        res = super(ClouderService, self).get_service_res()
        if self.image_id.type_id.name == 'registry':
            res['environment'].update({
                'REGISTRY_HTTP_TLS_CERTIFICATE': '/certs/domain.crt',
                'REGISTRY_HTTP_TLS_KEY': '/certs/domain.key',
                'REGISTRY_AUTH': 'htpasswd',
                'REGISTRY_AUTH_HTPASSWD_REALM': 'Registry Realm',
                'REGISTRY_AUTH_HTPASSWD_PATH': '/auth/htpasswd'})
        return res

    @api.multi
    def deploy_post(self):
        """
        Regenerate the ssl certs after the registry deploy.
        """
        if self.application_id.type_id.name == 'registry' and \
                self.application_id.check_tags(['data']):

            certfile = '/certs/domain.crt'
            keyfile = '/certs/domain.key'
            partner_id = self.environment_id.partner_id

            self.execute(['rm', certfile])
            self.execute(['rm', keyfile])

            self.execute([
                'openssl', 'req', '-x509', '-nodes', '-days', '365',
                '-newkey', 'rsa:2048', '-out', certfile, ' -keyout',
                keyfile, '-subj',
                '"/C=%s/L=%s/O=%s/CN=%s"' % (
                    partner_id.country_id.code,
                    partner_id.city,
                    partner_id.commercial_partner_id.name,
                    self.node_id.name,
                ),
            ])

        return super(ClouderService, self).deploy_post()


class ClouderServiceLink(models.Model):
    """
    Add methods to manage the registry specificities.
    """

    _inherit = 'clouder.service.link'

    @api.multi
    def deploy_link(self):
        """
        """
        super(ClouderServiceLink, self).deploy_link()

        if self.name.type_id.name == 'registry':
            if 'exec' in self.target.childs:
                self.target.execute([
                    'htpasswd', '-Bbn',  self.service_id.name,
                    self.service_id.options['registry_password']['value'],
                    '>', 'auth/htpasswd',
                ],
                    executor='sh',
                )
                self.target.start()

    @api.multi
    def purge_link(self):
        """
        """
        super(ClouderServiceLink, self).purge_link()

        if self.name.type_id.name == 'registry':
            if 'exec' in self.target.childs:
                self.target.execute([
                    'sed', '-i', '"/%s/d"' % self.service_id.name,
                    'auth/htpasswd',
                ],
                    executor='sh',
                )
                self.target.start()


class ClouderBaseLink(models.Model):
    """
    Add methods to manage the registry specificities.
    """

    _inherit = 'clouder.base.link'

    @api.multi
    def deploy_link(self):
        """
        """
        super(ClouderBaseLink, self).deploy_link()

        if self.name.type_id.name == 'proxy' \
                and self.base_id.application_id.type_id.name == 'registry':
            registry = self.base_id.service_id.childs['exec']
            if self.base_id.cert_cert and self.base_id.cert_key:
                registry.execute([
                    'echo', '"%s"' % self.base_id.cert_cert,
                    '>', '/certs/domain.crt',
                ], executor='sh')
                registry.execute([
                    'echo', '"%s"' % self.base_id.cert_key,
                    '>', '/certs/domain.key',
                ],
                    executor='sh',
                )
                registry.start()
