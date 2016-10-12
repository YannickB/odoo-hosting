# -*- coding: utf-8 -*-
##############################################################################
#
# Author: Yannick Buron, Nicolas Petit
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
import logging

_logger = logging.getLogger(__name__)


class ClouderApplication(models.Model):
    """
    Adds information for web-creation on applications
    """

    _inherit = 'clouder.application'

    web_create_type = fields.Selection(
        [
            ('disabled', 'Disabled'),
            ('container', 'Container'),
            ('base', 'Base')
        ],
        'Web creation',
        default='disabled',
        required=True
    )

    @api.one
    @api.constrains('web_create_type', 'next_server_id',
                    'next_container_id', 'base')
    def _check_web_create_type_next(self):
        """
        Checks that the base web type can only
        be applied on application that can have bases
        Checks that the next container/server
        is correctly set depending on the web_create type
        """
        if self.web_create_type == 'base':
            if not self.base:
                raise except_orm(
                    _('Data error!'),
                    _("You cannot attribute the web type 'Base' to an "
                      "application that cannot have bases."))
            if not self.next_container_id:
                raise except_orm(
                    _('Data error!'),
                    _("You need to specify the next container "
                      "for web type 'Base'"))
        elif self.web_create_type == 'container' and not self.next_server_id:
            raise except_orm(
                _('Data error!'),
                _("You need to specify the next server for "
                  "web type 'Container'"))

    @api.multi
    def create_instance_from_request(self, session_id):
        """
        Creates a clouder container or base using provided data
        """
        orm_clws = self.env['clouder.web.session'].sudo()
        data = orm_clws.browse([session_id])[0]

        orm_user = self.env['res.users'].sudo()
        user = orm_user.search([
            ('partner_id', '=', data.partner_id.id),
            ('login', '=', data.partner_id.email)
        ])

        # Create user if it doesn't exist yet
        if not user:
            user = orm_user.create({
                'login': data.partner_id.email,
                'partner_id': data.partner_id.id
            })
            # Add user to Clouder user group
            self.env.ref('clouder.group_clouder_user').sudo().write({
                'users': [(4, user.id)]
            })

        # Create environment if it doesn't exist
        if not data.environment_id:
            env_obj = self.env['clouder.environment']
            env_id = env_obj.search([('partner_id', '=', data.partner_id.id)])
            if env_id:
                data.environment_id = env_id[0]
            else:
                data.environment_id = env_obj.create({
                    'name': data.partner_id.name,
                    'partner_id': data.partner_id.id,
                    'prefix': data.environment_prefix
                })

        # Create the requested instance
        if data.application_id.web_create_type == 'container':
            return self.env['clouder.container'].create({
                'environment_id': data.environment_id.id,
                'suffix': data.suffix,
                'application_id': data.application_id.id
            })
        elif data.application_id.web_create_type == 'base':
            return self.env['clouder.base'].create({
                'name': data.prefix,
                'domain_id': data.domain_id.id,
                'container_id': data.application_id.next_container_id.id,
                'environment_id': data.environment_id.id,
                'title': data.title,
                'application_id': data.application_id.id,
                'poweruser_name': data.partner_id.email,
                'poweruser_email': data.partner_id.email,
                'lang': 'lang' in self.env.context and
                        self.env.context['lang'] or 'en_US',
                'ssl_only': True,
                'autosave': True,
            })

        return False


class ClouderWebSession(models.Model):
    """
    A class to store session info from the external web form
    """
    _name = 'clouder.web.session'

    @api.one
    def _get_name(self):
        """
        Computes a name for a clouder web session
        """
        name = "App{0}-{1}".format(
            self.application_id.name,
            self.application_id.web_create_type
        )
        if self.application_id.web_create_type == 'base':
            name += "_{0}-{1}".format(
                self.prefix,
                self.domain_id.name
            )
        elif self.application_id.web_create_type == 'container':
            name += "_{0}-{1}".format(
                self.environment_id and self.environment_id.prefix or
                self.environment_prefix,
                self.prefix
            )
        self.name = name

    name = fields.Char("Name", compute='_get_name', required=False)
    partner_id = fields.Many2one('res.partner', 'Partner', required=True)
    clouder_partner_id = fields.Many2one(
        'res.partner', 'Sales Partner', required=True)
    application_id = fields.Many2one(
        'clouder.application', 'Application', required=True)
    domain_id = fields.Many2one('clouder.domain', 'Domain', required=False)
    prefix = fields.Char('Prefix', required=False)
    suffix = fields.Char('Prefix', required=False)
    title = fields.Char('Title', required=False)
    environment_id = fields.Many2one(
        'clouder.environment', 'Environment', required=False)
    environment_prefix = fields.Char('Environment prefix', required=False)

    @api.one
    @api.constrains('environment_id', 'suffix', 'application_id')
    def _check_env_and_prefix_not_used(self):
        """
        Checks that there is no existing container
        using this environment with the same container suffix
        """
        if self.application_id.web_create_type == 'container' \
                and self.environment_id:
            container = self.env['clouder.container'].search([
                ('suffix', '=', self.suffix),
                ('environment_id', '=', self.environment_id.id)
            ])

            if container:
                raise except_orm(
                    _('Session duplicate error!'),
                    _('Container already exists with environment '
                      '{0} and prefix {1}').format(
                        self.environment_id.prefix,
                        self.suffix
                    )
                )
            session = self.search([
                ('id', '!=', self.id),
                ('suffix', '=', self.suffix),
                ('environment_id', '=', self.environment_id.id)
            ])
            if session:
                raise except_orm(
                    _('Session duplicate error!'),
                    _('Session already exists with environment '
                      '{0} and prefix {1}').format(
                        self.environment_id.prefix,
                        self.suffix
                    )
                )

    @api.one
    @api.constrains('environment_prefix', 'environment_id')
    def _check_envprefix_not_used(self):
        """
        Checks that there is no existing environment using the same prefix
        """
        if self.application_id.web_create_type == 'container' \
                and self.prefix and not self.environment_id:
            env = self.env['clouder.environment'].search([
                ('prefix', '=', self.environment_prefix)
            ])
            if env:
                raise except_orm(
                    _('Session duplicate error!'),
                    _('Environment prefix \'{0}\' already exists.').format(
                        self.environment_prefix
                    )
                )

            app_ids = [
                app.id for app in self.env['clouder.application'].search([
                    ('web_create_type', '=', 'container')
                ])
            ]
            session = self.search([
                ('id', '!=', self.id),
                ('application_id', 'in', app_ids),
                ('environment_id', '=', False),
                ('environment_prefix', '=', self.environment_prefix)
            ])
            if session:
                raise except_orm(
                    _('Session duplicate error!'),
                    _('Environment prefix \'{0}\' is already reserved.')
                    .format(self.environment_prefix)
                )

    @api.one
    @api.constrains('application_id', 'domain_id', 'prefix')
    def _check_base_domain_prefix_not_used(self):
        """
        Checks that there is no domain/prefix combination in bases
        """
        if self.application_id.web_create_type == 'base':
            base = self.env['clouder.base'].search([
                ('name', '=', self.prefix),
                ('domain_id', '=', self.domain_id.id)
            ])
            if base:
                raise except_orm(
                    _('Session duplicate error!'),
                    _('Base with domain \'{0}\' and name \'{1}\' '
                      'already exists.').format(
                        self.domain_id.name,
                        self.prefix
                    )
                )

            app_ids = [
                app.id for app in self.env['clouder.application'].search([
                    ('web_create_type', '=', 'base')
                ])
            ]
            session = self.search([
                ('id', '!=', self.id),
                ('application_id', 'in', app_ids),
                ('prefix', '=', self.prefix),
                ('domain_id', '=', self.domain_id.id)
            ])
            if session:
                raise except_orm(
                    _('Session duplicate error!'),
                    _('Base with domain \'{0}\' and name \'{1}\' '
                      'is already reserved.').format(
                        self.domain_id.name,
                        self.prefix
                    )
                )

    @api.one
    @api.constrains('application_id', 'title', 'prefix', 'domain_id',
                    'suffix', 'environment_id', 'environment_prefix')
    def _check_complex_requirements(self):
        """
        Checks fields requirements that are dependant on others
        """
        if self.application_id.web_create_type == "base":
            if not self.title:
                raise except_orm(
                    _('Data error!'),
                    _("You need to specify a title when applying for a base")
                )
            if not self.prefix:
                raise except_orm(
                    _('Data error!'),
                    _("You need to specify a prefix when applying for a base")
                )
            if not self.domain_id:
                raise except_orm(
                    _('Data error!'),
                    _("You need to specify a domain when applying for a base")
                )
        elif self.application_id.web_create_type == "container":
            if not self.suffix:
                raise except_orm(
                    _('Data error!'),
                    _("You need to specify a suffix when "
                      "applying for a container")
                )
            if not (self.environment_id or self.environment_prefix):
                raise except_orm(
                    _('Data error!'),
                    _("You need to specify an existing or new environment "
                      "when applying for a container")
                )
