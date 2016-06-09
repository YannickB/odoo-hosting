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

from openerp import models, api, modules


class ClouderServer(models.Model):
    """
    Add methods to manage the postgres specificities.
    """

    _inherit = 'clouder.server'

    @api.multi
    def oneclick_clouder_deploy(self):
        self = self.with_context(no_enqueue=True)
        # TODO
        # container_ports={'nginx':80,'nginx-ssl':443,'bind':53})

        image_obj = self.env['clouder.image']
        image_version_obj = self.env['clouder.image.version']

        container_obj = self.env['clouder.container']
        port_obj = self.env['clouder.container.port']
        application_obj = self.env['clouder.application']

        image = image_obj.search([('name', '=', 'img_registry')])
        image.build()

        application = application_obj.search([('code', '=', 'registry')])
        registry = container_obj.create({
            'suffix': 'registry',
            'environment_id': self.environment_id.id,
            'server_id': self.id,
            'application_id': application.id,
        })


        image = image_obj.search([('name', '=', 'img_base')])
        if not image.has_version:
            image = image_obj.search([('name', '=', 'img_base')])
            image.registry_id = registry.id
            image.build()
        base = image_version_obj.search([('image_id', '=', image.id)])

        image = image_obj.search([('name', '=', 'img_backup_bup')])
        if not image.has_version:
            image.registry_id = registry.id
            image.parent_version_id = base.id
            image.build()

        image = image_obj.search([('name', '=', 'img_spamassassin')])
        if not image.has_version:
            image.registry_id = registry.id
            image.parent_version_id = base.id
            image.build()

        image = image_obj.search([('name', '=', 'img_postfix')])
        if not image.has_version:
            image.registry_id = registry.id
            image.parent_version_id = base.id
            image.build()

        image = image_obj.search([('name', '=', 'img_bind')])
        if not image.has_version:
            image.registry_id = registry.id
            image.parent_version_id = base.id
            image.build()

        image = image_obj.search([('name', '=', 'img_nginx')])
        if not image.has_version:
            image.registry_id = registry.id
            image.parent_version_id = base.id
            image.build()
        nginx = image_version_obj.search([('image_id', '=', image.id)])

        image = image_obj.search([('name', '=', 'img_proxy')])
        if not image.has_version:
            image.registry_id = registry.id
            image.parent_version_id = nginx.id
            image.build()

        image = image_obj.search([('name', '=', 'img_shinken')])
        if not image.has_version:
            image.registry_id = registry.id
            image.parent_version_id = base.id
            image.build()

        image = image_obj.search([('name', '=', 'img_glances')])
        if not image.has_version:
            image.registry_id = registry.id
            image.parent_version_id = base.id
            image.build()

        image = image_obj.search([('name', '=', 'img_postgres')])
        if not image.has_version:
            image.registry_id = registry.id
            image.parent_version_id = base.id
            image.build()

        image = image_obj.search([('name', '=', 'img_odoo_data')])
        if not image.has_version:
            image.registry_id = registry.id
            image.parent_version_id = base.id
            image.build()

        image = image_obj.search([('name', '=', 'img_odoo_clouder_files8')])
        if not image.has_version:
            image.registry_id = registry.id
            image.parent_version_id = base.id
            image.build()

        image = image_obj.search([('name', '=', 'img_odoo_clouder_exec')])
        if not image.has_version:
            image.registry_id = registry.id
            image.parent_version_id = base.id
            image.build()

        application = application_obj.search([('code', '=', 'backup-bup')])
        container_obj.create({
            'suffix': 'backup',
            'environment_id': self.environment_id.id,
            'server_id': self.id,
            'application_id': application.id,
        })

        application = application_obj.search([('code', '=', 'spamassassin')])
        container_obj.create({
            'suffix': 'spamassassin',
            'environment_id': self.environment_id.id,
            'server_id': self.id,
            'application_id': application.id,
        })

        application = application_obj.search([('code', '=', 'postfix')])
        ports = []
        if self.oneclick_ports:
            ports = [(0,0,{'name':'postfix', 'localport': 25, 'hostport': 25, 'expose': 'internet'})]
        postfix = container_obj.create({
            'suffix': 'postfix',
            'environment_id': self.environment_id.id,
            'server_id': self.id,
            'application_id': application.id,
#            'port_ids': ports
        })
        if self.oneclick_ports:
            port = port_obj.search([('container_id', '=', postfix.id),('name','=','postfix')])
            port.write({'hostport': 25})
            postfix.reinstall()

        application = application_obj.search([('code', '=', 'bind')])
        ports = []
        if self.oneclick_ports:
            ports = [(0,0,{'name':'bind', 'localport': 53, 'hostport': 53, 'expose': 'internet', 'udp': True})]
        bind = container_obj.create({
            'suffix': 'bind',
            'environment_id': self.environment_id.id,
            'server_id': self.id,
            'application_id': application.id,
#            'port_ids': ports
        })
        if self.oneclick_ports:
            port = port_obj.search([('container_id', '=', bind.id),('name','=','bind')])
            port.write({'hostport': 53})
            bind.reinstall()


        application = application_obj.search([('code', '=', 'proxy')])
        ports = []
        if self.oneclick_ports:
            ports = [(0,0,{'name':'nginx', 'localport': 80, 'hostport': 80, 'expose': 'internet'}),
                     (0,0,{'name':'nginx-ssl', 'localport': 443, 'hostport': 443, 'expose': 'internet'})]
        proxy = container_obj.create({
            'suffix': 'proxy',
            'environment_id': self.environment_id.id,
            'server_id': self.id,
            'application_id': application.id,
#            'port_ids': ports
        })
        if self.oneclick_ports:
            port = port_obj.search([('container_id', '=', proxy.id),('name','=','nginx')])
            port.write({'hostport': 80})
            port = port_obj.search([('container_id', '=', proxy.id),('name','=','nginx-ssl')])
            port.write({'hostport': 443})
            proxy.reinstall()


        application = application_obj.search([('code', '=', 'shinken')])
        shinken = container_obj.create({
            'suffix': 'shinken',
            'environment_id': self.environment_id.id,
            'server_id': self.id,
            'application_id': application.id,
        })

        application = application_obj.search([('code', '=', 'glances')])
        container_obj.create({
            'suffix': 'glances',
            'environment_id': self.environment_id.id,
            'server_id': self.id,
            'application_id': application.id,
        })

        application = application_obj.search([('code', '=', 'postgres')])
        container_obj.create({
            'suffix': 'postgres',
            'environment_id': self.environment_id.id,
            'server_id': self.id,
            'application_id': application.id,
        })

        application = application_obj.search([('code', '=', 'clouder')])
        clouder = container_obj.create({
            'suffix': 'clouder',
            'environment_id': self.environment_id.id,
            'server_id': self.id,
            'application_id': application.id,
            'subservice_name': 'test'
        })

        domain_obj = self.env['clouder.domain']
        domain = domain_obj.create({
            'name': self.oneclick_domain,
            'organisation': self.oneclick_domain,
            'dns_id': bind.id
        })

        base_obj = self.env['clouder.base']
        application = application_obj.search([('code', '=', 'shinken')])
        base_obj.create({
            'name': 'shinken',
            'domain_id': domain.id,
            'environment_id': self.environment_id.id,
            'title': 'Shinken',
            'application_id': application.id,
            'container_id': shinken.id,
            'admin_name': 'admin',
            'admin_password': 'admin',
        })

        application = application_obj.search([('code', '=', 'clouder')])
        base_obj.create({
            'name': 'clouder',
            'domain_id': domain.id,
            'environment_id': self.environment_id.id,
            'title': 'My Clouder',
            'application_id': application.id,
            'container_id': clouder.id,
            'admin_name': 'admin',
            'admin_password': 'admin',
            'test': True
        })

#        clouder.install_subservice()

    @api.multi
    def oneclick_clouder_purge(self):
        self = self.with_context(no_enqueue=True)

        container_obj = self.env['clouder.container']

        container_obj.search([('environment_id', '=', self.environment_id.id),
                              ('suffix', '=', 'clouder-test')]).unlink()

        container_obj.search([('environment_id', '=', self.environment_id.id),
                              ('suffix', '=', 'clouder')]).unlink()

        container_obj.search([('environment_id', '=', self.environment_id.id),
                              ('suffix', '=', 'postgres')]).unlink()

        container_obj.search([('environment_id', '=', self.environment_id.id),
                              ('suffix', '=', 'glances')]).unlink()

        container_obj.search([('environment_id', '=', self.environment_id.id),
                              ('suffix', '=', 'shinken')]).unlink()

        self.env['clouder.domain'].search([('name', '=', self.oneclick_domain)]).unlink()

        container_obj.search([('environment_id', '=', self.environment_id.id),
                              ('suffix', '=', 'proxy')]).unlink()

        container_obj.search([('environment_id', '=', self.environment_id.id),
                              ('suffix', '=', 'bind')]).unlink()

        container_obj.search([('environment_id', '=', self.environment_id.id),
                              ('suffix', '=', 'postfix')]).unlink()

        container_obj.search([('environment_id', '=', self.environment_id.id),
                              ('suffix', '=', 'spamassassin')]).unlink()

        container_obj.search([('environment_id', '=', self.environment_id.id),
                              ('suffix', '=', 'backup')]).unlink()

        container_obj.search([('environment_id', '=', self.environment_id.id),
                              ('suffix', '=', 'registry')]).unlink()
