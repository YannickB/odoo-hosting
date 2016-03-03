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
        prefix = self.oneclick_prefix

        image_obj = self.env['clouder.image']
        image_version_obj = self.env['clouder.image.version']

        container_obj = self.env['clouder.container']
        application_obj = self.env['clouder.application']

        image = image_obj.search([('name', '=', 'img_registry')])
        image.build()

        application = application_obj.search([('code', '=', 'registry')])
        registry = container_obj.create({
            'name': 'registry',
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

        image = image_obj.search([('name', '=', 'img_odoo_exec')])
        if not image.has_version:
            image.registry_id = registry.id
            image.parent_version_id = base.id
            image.build()

        application = application_obj.search([('code', '=', 'backup-bup')])
        container_obj.create({
            'name': 'backup',
            'environment_id': self.environment_id.id,
            'server_id': self.id,
            'application_id': application.id,
        })

        application = application_obj.search([('code', '=', 'postfix')])
        container_obj.create({
            'name': 'postfix',
            'environment_id': self.environment_id.id,
            'server_id': self.id,
            'application_id': application.id,
        })

        application = application_obj.search([('code', '=', 'bind')])
        bind = container_obj.create({
            'name': 'bind',
            'environment_id': self.environment_id.id,
            'server_id': self.id,
            'application_id': application.id,
        })

        application = application_obj.search([('code', '=', 'proxy')])
        container_obj.create({
            'name': 'proxy',
            'environment_id': self.environment_id.id,
            'server_id': self.id,
            'application_id': application.id,
        })

        application = application_obj.search([('code', '=', 'shinken')])
        container_obj.create({
            'name': 'shinken',
            'environment_id': self.environment_id.id,
            'server_id': self.id,
            'application_id': application.id,
        })

        application = application_obj.search([('code', '=', 'glances')])
        container_obj.create({
            'name': 'glances',
            'environment_id': self.environment_id.id,
            'server_id': self.id,
            'application_id': application.id,
        })

        application = application_obj.search([('code', '=', 'postgres')])
        container_obj.create({
            'name': 'postgres',
            'environment_id': self.environment_id.id,
            'server_id': self.id,
            'application_id': application.id,
        })

        application = application_obj.search([('code', '=', 'clouder')])
        clouder = container_obj.create({
            'name': 'clouder',
            'environment_id': self.environment_id.id,
            'server_id': self.id,
            'application_id': application.id,
            'subservice_name': 'test'
        })

        domain_obj = self.env['clouder.domain']
        domain = domain_obj.create({
            'name': 'mydomain',
            'organisation': 'My Company',
            'dns_id': bind.id
        })

        base_obj = self.env['clouder.base']
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

        clouder.install_subservice()

    @api.multi
    def oneclick_clouder_purge(self):

        self = self.with_context(no_enqueue=True)
        prefix = self.oneclick_prefix

        container_obj = self.env['clouder.container']

        container_obj.search([('environment_id', '=', self.environment_id.id),
                              ('name', '=', 'clouder-test')]).unlink()

        container_obj.search([('environment_id', '=', self.environment_id.id),
                              ('name', '=', 'clouder')]).unlink()

        self.env['clouder.domain'].search([('name', '=', 'mydomain')]).unlink()

        container_obj.search([('environment_id', '=', self.environment_id.id),
                              ('name', '=', 'postgres')]).unlink()

        container_obj.search([('environment_id', '=', self.environment_id.id),
                              ('name', '=', 'glances')]).unlink()

        container_obj.search([('environment_id', '=', self.environment_id.id),
                              ('name', '=', 'shinken')]).unlink()

        container_obj.search([('environment_id', '=', self.environment_id.id),
                              ('name', '=', 'proxy')]).unlink()

        container_obj.search([('environment_id', '=', self.environment_id.id),
                              ('name', '=', 'bind')]).unlink()

        container_obj.search([('environment_id', '=', self.environment_id.id),
                              ('name', '=', 'postfix')]).unlink()

        container_obj.search([('environment_id', '=', self.environment_id.id),
                              ('name', '=', 'backup')]).unlink()

        container_obj.search([('environment_id', '=', self.environment_id.id),
                              ('name', '=', 'registry')]).unlink()