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

from datetime import datetime, timedelta
import clouder_model

import logging

_logger = logging.getLogger(__name__)


class ClouderDomain(models.Model):
    _name = 'clouder.domain'
    _inherit = ['clouder.model']

    name = fields.Char('Domain name', size=64, required=True)
    organisation = fields.Char('Organisation', size=64, required=True)
    dns_id = fields.Many2one('clouder.container', 'DNS Server', required=True)
    cert_key = fields.Text('Wildcard Cert Key')
    cert_cert = fields.Text('Wildcart Cert')
    public = fields.Boolean('Public?')
    partner_id = fields.Many2one(
        'res.partner', 'Manager',
        default=lambda self: self.env.user.partner_id)

    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'Name must be unique!'),
    ]

    @api.one
    @api.constrains('name')
    def _validate_data(self):
        if not re.match("^[\w\d.-]*$", self.name):
            raise except_orm(_('Data error!'), _(
                "Name can only contains letters, digits - and dot"))

            # @api.multi
            # def get_vals(self):
            #
            #     vals = {}
            #
            #     vals.update(self.env.ref('clouder.clouder_settings').get_vals())
            #
            #     dns_vals = self.dns_server_id.get_vals()
            #
            #     vals.update({
            #         'dns_id': dns_vals['container_id'],
            #         'dns_name': dns_vals['container_name'],
            #         'dns_fullname': dns_vals['container_fullname'],
            #         'dns_ssh_port': dns_vals['container_ssh_port'],
            #         'dns_server_id': dns_vals['server_id'],
            #         'dns_server_domain': dns_vals['server_domain'],
            #         'dns_server_ip': dns_vals['server_ip'],
            #     })
            #
            #     vals.update({
            #         'domain_name': self.name,
            #         'domain_organisation': self.organisation,
            #         'domain_configfile': '/etc/bind/db.' + self.name,
            #         'domain_certkey': self.cert_key,
            #         'domain_certcert': self.cert_cert,
            #     })
            #
            #     return vals


class ClouderBase(models.Model):
    _name = 'clouder.base'
    _inherit = ['clouder.model']

    name = fields.Char('Name', size=64, required=True)
    title = fields.Char('Title', size=64, required=True)
    application_id = fields.Many2one('clouder.application', 'Application',
                                     required=True)
    domain_id = fields.Many2one('clouder.domain', 'Domain name', required=True)
    service_id = fields.Many2one('clouder.service', 'Service', required=True)
    service_ids = fields.Many2many('clouder.service',
                                   'clouder_base_service_rel', 'base_id',
                                   'service_id', 'Alternative Services')
    admin_name = fields.Char('Admin name', size=64, required=True)
    admin_passwd = fields.Char(
        'Admin password', size=64, required=True,
        default=clouder_model.generate_random_password(20))
    admin_email = fields.Char('Admin email', size=64, required=True)
    poweruser_name = fields.Char('PowerUser name', size=64)
    poweruser_passwd = fields.Char(
        'PowerUser password', size=64,
        default=clouder_model.generate_random_password(12))
    poweruser_email = fields.Char('PowerUser email', size=64)
    build = fields.Selection(
        [('none', 'No action'), ('build', 'Build'), ('restore', 'Restore')],
        'Build?', default='build')
    ssl_only = fields.Boolean('SSL Only?')
    test = fields.Boolean('Test?')
    lang = fields.Selection(
        [('en_US', 'en_US'), ('fr_FR', 'fr_FR')],
        'Language', required=True, default='en_US')
    state = fields.Selection(
        [('installing', 'Installing'), ('enabled', 'Enabled'),
        ('blocked', 'Blocked'), ('removing', 'Removing')],
        'State', readonly=True)
    option_ids = fields.One2many('clouder.base.option', 'base_id', 'Options')
    link_ids = fields.One2many('clouder.base.link', 'base_id', 'Links')
    save_repository_id = fields.Many2one('clouder.save.repository',
                                         'Save repository')
    time_between_save = fields.Integer('Minutes between each save')
    saverepo_change = fields.Integer('Days before saverepo change')
    saverepo_expiration = fields.Integer('Days before saverepo expiration')
    save_expiration = fields.Integer('Days before save expiration')
    date_next_save = fields.Datetime('Next save planned')
    save_comment = fields.Text('Save Comment')
    nosave = fields.Boolean('No save?')
    reset_each_day = fields.Boolean('Reset each day?')
    cert_key = fields.Text('Cert Key')
    cert_cert = fields.Text('Cert')
    parent_id = fields.Many2one('clouder.base', 'Parent Base')
    backup_ids = fields.Many2many(
        'clouder.container', 'clouder_base_backup_rel',
        'base_id', 'backup_id', 'Backup containers', required=True)
    public = fields.Boolean('Public?')
    partner_id = fields.Many2one(
        'res.partner', 'Manager',
        default=lambda self: self.user_partner)
    partner_ids = fields.Many2many('res.partner', 'clouder_base_partner_rel',
                                   'base_id', 'partner_id', 'Users')

    @property
    def fullname(self):
        return (self.application_id.code + '-' + self.name + '-'
                + self.domain_id.name).replace('.', '-')

    @property
    def fullname_(self):
        return self.fullname.replace('-', '_')

    @property
    def fulldomain(self):
        return self.name + '.' + self.domain_id.name

    @property
    def databases(self):
        databases = {'single': self.fullname_}
        if self.application_id.type_id.multiple_databases:
            databases = {}
            for database in self.application_id.type_id.multiple_databases.split(
                    ','):
                databases[database] = self.fullname_ + '_' + database
        return databases

    @property
    def databases_comma(self):
        return ','.join([d for k, d in self.databases.iteritems()])

    @property
    def options(self):
        options = {}
        for option in \
                self.service_id.container_id.application_id.type_id.option_ids:
            if option.type == 'base':
                options[option.name] = {'id': option.id, 'name': option.name,
                                        'value': option.default}
        for option in self.option_ids:
            options[option.name.name] = {'id': option.id,
                                         'name': option.name.name,
                                         'value': option.value}
        return options

    _sql_constraints = [
        ('name_uniq', 'unique (name,domain_id)',
         'Name must be unique per domain !')
    ]

    @api.one
    @api.constrains('name', 'admin_name', 'admin_email', 'poweruser_email')
    def _validate_data(self):
        if not re.match("^[\w\d_]*$", self.name):
            raise except_orm(_('Data error!'), _(
                "Name can only contains letters, digits and underscore"))
        if self.admin_name and not re.match("^[\w\d_]*$", self.admin_name):
            raise except_orm(_('Data error!'), _(
                "Admin name can only contains letters, digits and underscore"))
        if self.admin_email\
                and not re.match("^[\w\d_.@-]*$", self.admin_email):
            raise except_orm(_('Data error!'), _(
                "Admin email can only contains letters, "
                "digits, underscore, - and @"))
        if self.poweruser_email \
                and not re.match("^[\w\d_.@-]*$", self.poweruser_email):
            raise except_orm(_('Data error!'), _(
                "Poweruser email can only contains letters, "
                "digits, underscore, - and @"))

    @api.one
    @api.constrains('service_id', 'service_ids', 'application_id')
    def _check_application(self):
        if self.application_id.id != self.service_id.application_id.id:
            raise except_orm(_('Data error!'),
                             _("The application of base must be the same "
                               "than the application of service."))
        for s in self.service_ids:
            if self.application_id.id != s.application_id.id:
                raise except_orm(_('Data error!'),
                                 _("The application of base must be the same "
                                   "than the application of service."))


    @api.one
    @api.constrains('option_ids')
    def _check_option_ids(self):
        for type_option in self.application_id.type_id.option_ids:
            if type_option.type == 'base' and type_option.required:
                test = False
                for option in self.option_ids:
                    if option.name == type_option and option.value:
                        test = True
                if not test:
                    raise except_orm(
                        _('Data error!'),
                        _("You need to specify a value for the option "
                          + type_option.name + " for the base " +
                          self.name + ".")
                    )

    @api.one
    @api.constrains('link_ids')
    def _check_link_ids(self):
        for app_link in self.application_id.link_ids:
            if app_link.base and app_link.required:
                test = False
                for link in self.link_ids:
                    if link.name == app_link and link.target:
                        test = True
                if not test:
                    raise except_orm(
                        _('Data error!'),
                        _("You need to specify a link to " + app_link.name
                          + " for the container " + self.name)
                    )


    @api.multi
    @api.onchange('application_id')
    def onchange_application_id(self):
        if self.application_id:

            self.admin_name = self.application_id.admin_name
            self.admin_email = self.application_id.admin_email \
                and self.application_id.admin_email \
                or self.email_sysadmin

            options = []
            for type_option in self.application_id.type_id.option_ids:
                if type_option.type == 'base' and type_option.auto:
                    test = False
                    for option in self.option_ids:
                        if option.name == type_option:
                            test = True
                    if not test:
                        options.append((0, 0, {
                            'name': type_option,
                            'value': type_option.default}))
            self.option_ids = options

            links = []
            for app_link in self.application_id.link_ids:
                if app_link.base and app_link.auto:
                    test = False
                    for link in self.link_ids:
                        if link.name == app_link:
                            test = True
                    if not test:
                        links.append((0, 0, {'name': app_link,
                                             'target': app_link.next}))
            self.link_ids = links

            self.backup_ids = [(6, 0, [
                b.id for b in self.application_id.base_backup_ids])]
            self.time_between_save = self.application_id.base_time_between_save
            self.saverepo_change = self.application_id.base_saverepo_change
            self.saverepo_expiration = \
                    self.application_id.base_saverepo_expiration
            self.save_expiration = self.application_id.base_save_expiration

                    #########TODO La liaison entre base et service est un many2many � cause du loadbalancing. Si le many2many est vide, un service est cr�� automatiquement. Finalement il y aura un many2one pour le principal, et un many2many pour g�rer le loadbalancing
                    #########Contrainte : L'application entre base et service doit �tre la m�me, de plus la bdd/host/db_user/db_password doit �tre la m�me entre tous les services d'une m�me base

    # @api.multi
    # def get_vals(self):
    #     repo_obj = self.pool.get('clouder.save.repository')
    #     vals = {}
    #
    #     now = datetime.now()
    #     if not self.save_repository_id:
    #         repo_ids = repo_obj.search([('base_name','=',self.name),('base_domain','=',self.domain_id.name)])
    #         if repo_ids:
    #             self.write({'save_repository_id': repo_ids[0]})
    #
    #     if not self.save_repository_id or datetime.strptime(self.save_repository_id.date_change, "%Y-%m-%d") < now or False:
    #         repo_vals ={
    #             'name': now.strftime("%Y-%m-%d") + '_' + self.name + '_' + self.domain_id.name,
    #             'type': 'base',
    #             'date_change': (now + timedelta(days=self.saverepo_change or self.application_id.base_saverepo_change)).strftime("%Y-%m-%d"),
    #             'date_expiration': (now + timedelta(days=self.saverepo_expiration or self.application_id.base_saverepo_expiration)).strftime("%Y-%m-%d"),
    #             'base_name': self.name,
    #             'base_domain': self.domain_id.name,
    #         }
    #         repo_id = repo_obj.create(repo_vals)
    #         self.write({'save_repository_id': repo_id})
    #
    #
    #     vals.update(self.domain_id.get_vals())
    #     vals.update(self.service_id.get_vals())
    #     vals.update(self.save_repository_id.get_vals())
    #
    #     fullname = vals['app_code'] + '-' + self.name + '-' + self.domain_id.name
    #     fullname = fullname.replace('.','-')
    #
    #     options = {}
    #     for option in self.service_id.container_id.application_id.type_id.option_ids:
    #         if option.type == 'base':
    #             options[option.name] = {'id': option.id, 'name': option.name, 'value': option.default}
    #     for option in self.option_ids:
    #         options[option.name.name] = {'id': option.id, 'name': option.name.name, 'value': option.value}
    #
    #     links = {}
    #     if 'app_links' in vals:
    #         for app_code, link in vals['app_links'].iteritems():
    #             if link['base']:
    #                 links[app_code] = link
    #                 links[app_code]['target'] = False
    #     for link in self.link_ids:
    #         if link.name.code in links and link.target:
    #             link_vals = link.target.get_vals()
    #             links[link.name.code]['target'] = {
    #                 'link_id': link_vals['container_id'],
    #                 'link_name': link_vals['container_name'],
    #                 'link_fullname': link_vals['container_fullname'],
    #                 'link_ssh_port': link_vals['container_ssh_port'],
    #                 'link_server_id': link_vals['server_id'],
    #                 'link_server_domain': link_vals['server_domain'],
    #                 'link_server_ip': link_vals['server_ip'],
    #             }
    #     links_temp = links
    #     for app_code, link in links.iteritems():
    #         if link['required'] and not link['target']:
    #             raise except_orm(_('Data error!'),
    #                 _("You need to specify a link to " + link['name'] + " for the base " + self.name))
    #     links = links_temp
    #
    #     backup_servers = []
    #     for backup in self.backup_server_ids:
    #         backup_vals = backup.get_vals()
    #         backup_servers.append({
    #             'container_id': backup_vals['container_id'],
    #             'container_fullname': backup_vals['container_fullname'],
    #             'server_id': backup_vals['server_id'],
    #             'server_ssh_port': backup_vals['server_ssh_port'],
    #             'server_domain': backup_vals['server_domain'],
    #             'server_ip': backup_vals['server_ip'],
    #             'backup_method': backup_vals['app_options']['backup_method']['value']
    #         })
    #
    #     fullname_ = fullname.replace('-','_')
    #     databases = {'single': fullname_}
    #     databases_comma = ''
    #     if vals['apptype_multiple_databases']:
    #         databases = {}
    #         first = True
    #         for database in vals['apptype_multiple_databases'].split(','):
    #             if not first:
    #                 databases_comma += ','
    #             databases[database] = fullname_ + '_' + database
    #             databases_comma += databases[database]
    #             first = False
    #     vals.update({
    #         'base_id': self.id,
    #         'base_name': self.name,
    #         'base_fullname': fullname,
    #         'base_fulldomain': self.name + '.' + self.domain_id.name,
    #         'base_fullname': fullname,
    #         'base_fullname_': fullname_,
    #         'base_title': self.title,
    #         'base_domain': self.domain_id.name,
    #         'base_admin_name': self.admin_name,
    #         'base_admin_passwd': self.admin_passwd,
    #         'base_admin_email': self.admin_email,
    #         'base_poweruser_name': self.poweruser_name,
    #         'base_poweruser_password': self.poweruser_passwd,
    #         'base_poweruser_email': self.poweruser_email,
    #         'base_build': self.build,
    #         'base_sslonly': self.ssl_only,
    #         'base_certkey': self.cert_key,
    #         'base_certcert': self.cert_cert,
    #         'base_test': self.test,
    #         'base_lang': self.lang,
    #         'base_nosave': self.nosave,
    #         'base_options': options,
    #         'base_links': links,
    #         'base_nginx_configfile': '/etc/nginx/sites-available/' + fullname,
    #         'base_shinken_configfile': '/usr/local/shinken/etc/services/' + fullname + '.cfg',
    #         'base_databases': databases,
    #         'base_databases_comma': databases_comma,
    #         'base_backup_servers': backup_servers
    #     })
    #
    #     return vals

    @api.model
    def create(self, vals):
        if (not 'service_id' in vals) or (not vals['service_id']):
            application_obj = self.env['clouder.application']
            domain_obj = self.env['clouder.domain']
            container_obj = self.env['clouder.container']
            service_obj = self.env['clouder.service']
            if 'application_id' not in vals or not vals['application_id']:
                raise except_orm(_('Error!'), _(
                    "You need to specify the application of the base."))
            application = application_obj.browse(vals['application_id'])
            if not application.next_server_id:
                raise except_orm(_('Error!'), _(
                    "You need to specify the next server in "
                    "application for the container autocreate."))
            if not application.default_image_id.version_ids:
                raise except_orm(_('Error!'), _(
                    "No version for the image linked to the application, "
                    "abandoning container autocreate..."))
            if not application.version_ids:
                raise except_orm(_('Error!'), _(
                    "No version for the application, "
                    "abandoning service autocreate..."))
            if 'domain_id' not in vals or not vals['domain_id']:
                raise except_orm(_('Error!'), _(
                    "You need to specify the domain of the base."))
            domain = domain_obj.browse(vals['domain_id'])
            container_vals = {
                'name': vals['name'] + '_' +
                        domain.name.replace('.', '_').replace('-', '_'),
                'server_id': application.next_server_id.id,
                'application_id': application.id,
                'image_id': application.default_image_id.id,
                'image_version_id':
                application.default_image_id.version_ids[0].id,
            }
            container_id = container_obj.create(container_vals)
            service_vals = {
                'name': 'production',
                'container_id': container_id,
                'application_version_id': application.version_ids[0].id,
            }
            vals['service_id'] = service_obj.create(service_vals)

        return super(ClouderBase, self).create(vals)

    @api.multi
    def write(self, vals):
        if 'service_id' in vals:
            self = self.with_context(self.create_log('service change'))
            self = self.with_context(save_comment='Before service change')
            self = self.with_context(forcesave=True)
            save = self.save()
            self = self.with_context(forcesave=False)
            self.purge()

        res = super(ClouderBase, self).write(vals)
        if 'service_id' in vals:
            save.service_id = vals['service_id']
            self = self.with_context(base_restoration=True)
            self.deploy()
            save.restore()
            self.end_log()
        if 'nosave' in vals or 'ssl_only' in vals:
            self.deploy_links()

        return res

    @api.one
    def unlink(self):
        self = self.with_context(save_comment='Before unlink')
        self.save()
        return super(ClouderBase, self).unlink()

    @api.multi
    def save(self):
        save_obj = self.pool.get('clouder.save.save')
        repo_obj = self.pool.get('clouder.save.repository')

        save = False

        now = datetime.now()
        if not self.save_repository_id:
            repo_ids = repo_obj.search([('base_name', '=', self.name), (
            'base_domain', '=', self.domain_id.name)])
            if repo_ids:
                self.save_repository_id = repo_ids[0]

        if not self.save_repository_id or datetime.strptime(
                self.save_repository_id.date_change,
                "%Y-%m-%d") < now or False:
            repo_vals = {
                'name': now.strftime(
                    "%Y-%m-%d") + '_' + self.name + '_' + self.domain_id.name,
                'type': 'base',
                'date_change': (now + timedelta(days=self.saverepo_change
                                or self.application_id.base_saverepo_change)
                                ).strftime("%Y-%m-%d"),
                'date_expiration': (now + timedelta(
                    days=self.saverepo_expiration
                    or self.application_id.base_saverepo_expiration)
                ).strftime("%Y-%m-%d"),
                'base_name': self.name,
                'base_domain': self.domain_id.name,
            }
            repo_id = repo_obj.create(repo_vals)
            self.save_repository_id = repo_id

        if 'nosave' in self.env.context \
                or (self.nosave and not 'forcesave' in self.env.context):
            self.log(
                'This base shall not be saved or the backup '
                'isnt configured in conf, skipping save base')
            return
        self = self.with_context(self.create_log('save'))
        if not self.backup_ids:
            self.log('The backup isnt configured in conf, skipping save base')
        for backup_server in self.backup_ids:
            save_vals = {
                'name': self.now_bup + '_' + self.fullname,
                'backup_id': backup_server.id,
                'repo_id': self.save_repository_id,
                'date_expiration': (now + timedelta(
                    days=self.save_expiration
                    or self.application_id.base_save_expiration)
                ).strftime("%Y-%m-%d"),
                'comment': 'save_comment' in self.env.context
                           and self.env.context['save_comment']
                           or self.save_comment or 'Manual',
                'now_bup': self.now_bup,
                'container_id': self.service_id.container_id.id,
                'service_id': self.service_id.id,
                'base_id': self.id,
            }
            save = save_obj.create(save_vals)
        next = (datetime.now() + timedelta(
            minutes=self.time_between_save
            or self.application_id.base_time_between_save)
        ).strftime("%Y-%m-%d %H:%M:%S")
        self.write({'save_comment': False, 'date_next_save': next})
        self.end_log()
        return save

    #
    # @api.multi
    # def reset_base(self, cr, uid, ids, context={}):
    #     self._reset_base(cr, uid,ids, context=context)

    def post_reset(self):
        self.deploy_links()
        return

    def _reset_base(self, base_name=False, service_id=False):
        base_parent_id = self.parent_id and self.parent_id or self
        # vals_parent = self.get_vals(cr, uid, base_parent_id, context=context)
        if not 'save_comment' in self.env.context:
            self = self.with_context(save_comment='Reset base')
        self.with_context(forcesave=True)
        save = base_parent_id.save()
        self.with_context(forcesave=False)
        self.with_context(nosave=True)
        vals = {'base_id': self.id, 'base_restore_to_name': self.name,
                'base_restore_to_domain_id': self.domain_id.id,
                'service_id': self.service_id.id, 'base_nosave': True}
        if base_name:
            vals = {'base_id': False, 'base_restore_to_name': base_name,
                    'base_restore_to_domain_id': self.domain_id.id,
                    'service_id': service_id, 'base_nosave': True}
        save.write(vals)
        base = save.restore()
        base.write({'parent_id': base_parent_id})
        base.with_context(base_parent_fullname_=base_parent_id.fullname_)
        base.with_context(service_parent_name=base_parent_id.service_id.name)
        base.update_base()
        base.post_reset()
        base.deploy_post()

    @api.multi
    def deploy_create_database(self):
        return False

    @api.multi
    def deploy_build(self):
        return

    @api.multi
    def deploy_post_restore(self):
        return

    @api.multi
    def deploy_create_poweruser(self):
        return

    @api.multi
    def deploy_test(self):
        return

    @api.multi
    def deploy_post(self):
        return

    #TODO remove
    @api.multi
    def deploy_prepare_apache(self):
        return

    @api.multi
    def deploy(self):
        self.purge()

        if 'base_restoration' in self.env.context:
            return

        res = self.deploy_create_database()
        if not res:
            for key, database in self.databases().iteritems():
                if self.service_id.database_type != 'mysql':
                    ssh = self.connect(
                        self.service_id.container_id.fullname,
                        username=self.application_id.type_id.system_user)
                    self.execute(ssh, ['createdb', '-h',
                                       self.service_id.database_server, '-U',
                                       self.db_user, database])
                    ssh.close()
                else:
                    ssh = self.connect(
                        self.service_id.database.fullname)
                    self.execute(ssh, [
                        "mysql -u root -p'"
                        + self.service_id.database.root_password
                        + "' -se \"create database " + database + ";\""
                    ])
                    self.execute(ssh, [
                        "mysql -u root -p'"
                        + self.service_id.database.root_password
                        + "' -se \"grant all on " + database
                        + ".* to '" + self.service_id.db_user + "';\""
                    ])
                    ssh.close()

        self.log('Database created')
        if self.build == 'build':
            self.deploy_build()

        elif self.build == 'restore':
            if self.service_id.database_type != 'mysql':
                ssh = self.connect(
                    self.service_id.container_id.fullname,
                    username=self.application_id.type_id.system_user)
                self.execute(ssh, [
                    'pg_restore', '-h', self.service_id.database_server,
                    '-U', self.service_id.db_user, '--no-owner',
                    '-Fc', '-d', self.fullname_,
                    self.service_id.application_version_id.full_localpath
                    + '/' + self.service_id.database_type + '/build.sql'
                ])
                ssh.close()
            else:
                ssh = self.connect(
                    self.service_id.container_id.fullname,
                    username=self.application_id.type_id.system_user)
                self.execute(ssh, [
                    'mysql', '-h', self.service_id.database_server,
                    '-u', self.service_id.db_user,
                    '-p' + self.service_id.database.root_password,
                    self.fullname_, '<',
                    self.service_id.application_version_id.full_localpath
                    + '/' + self.service_id.database_type + '/build.sql'
                ])
                ssh.close()

            self.deploy_post_restore()

        if self.build != 'none':
            if self.poweruser_name and self.poweruser_email \
                    and self.admin_name != self.poweruser_name:
                self.deploy_create_poweruser()
            if self.test:
                self.deploy_test()

        self.deploy_post()

        #For shinken
        self.save()


    @api.multi
    def purge_post(self):
        return

    @api.multi
    def purge_db(self):
        for key, database in self.databases().iteritems():
            if self.service_id.database_type != 'mysql':
                ssh = self.connect(self.service_id.database.fullname,
                                         username='postgres')
                self.execute(ssh, [
                    'psql', '-c',
                    '"update pg_database set datallowconn = \'false\' '
                    'where datname = \'' + database + '\'; '
                    'SELECT pg_terminate_backend(procpid) '
                    'FROM pg_stat_activity WHERE datname = \''
                    + database + '\';"'
                ])
                self.execute(ssh, ['dropdb', database])
                ssh.close()
            else:
                ssh = self.connect(self.service_id.database.fullname)
                self.execute(ssh, [
                    "mysql -u root -p'"
                    + self.service_id.database.root_password
                    + "' -se \"drop database " + database + ";\""
                ])
                ssh.close()
        return

    @api.multi
    def purge(self):

        self.purge_db()

        self.purge_post()

    def update_base(self):
        return


class ClouderBaseOption(models.Model):
    _name = 'clouder.base.option'

    base_id = fields.Many2one('clouder.base', 'Base', ondelete="cascade",
                              required=True)
    name = fields.Many2one('clouder.application.type.option', 'Option',
                           required=True)
    value = fields.Text('Value')

    _sql_constraints = [
        ('name_uniq', 'unique(base_id,name)',
         'Option name must be unique per base!'),
    ]


    @api.one
    @api.constrains('base_id')
    def _check_required(self):
        if self.name.required and not self.value:
            raise except_orm(
                _('Data error!'),
                _("You need to specify a value for the option "
                  + self.name.name + " for the base "
                  + self.base_id.name + ".")
            )


class ClouderBaseLink(models.Model):
    _name = 'clouder.base.link'
    _inherit = ['clouder.model']

    base_id = fields.Many2one('clouder.base', 'Base', ondelete="cascade",
                              required=True)
    name = fields.Many2one('clouder.application.link', 'Application Link',
                           required=True)
    target = fields.Many2one('clouder.container', 'Target')

    target_base = lambda self: self.target.service_ids and \
                               self.target.service_ids[0].base_ids and \
                               self.target.service_ids[0].base_ids[0]

    @api.one
    @api.constrains('base_id')
    def _check_required(self):
        if self.name.required and not self.target:
            raise except_orm(
                _('Data error!'),
                _("You need to specify a link to "
                  + self.name.application_id.name + " for the base "
                  + self.base_id.name)
            )

    #
    # @api.multi
    # def get_vals(self):
    #     vals = {}
    #
    #     vals.update(self.base_id.get_vals())
    #     if self.target:
    #         target_vals = self.target_id.get_vals()
    #         vals.update({
    #             'link_target_container_id': target_vals['container_id'],
    #             'link_target_container_name': target_vals['container_name'],
    #             'link_target_container_fullname': target_vals['container_fullname'],
    #             'link_target_app_id': target_vals['app_id'],
    #             'link_target_app_code': target_vals['app_code'],
    #         })
    #         service_ids = self.env['clouder.service'].search([('container_id', '=', self.target.id)])
    #         base_ids = self.env['clouder.base'].search([('service_id', 'in', service_ids)])
    #         if base_ids:
    #             base_vals = base_ids[0].get_vals()
    #             vals.update({
    #                 'link_target_service_db_user': base_vals['service_db_user'],
    #                 'link_target_service_db_password': base_vals['service_db_password'],
    #                 'link_target_database_server': base_vals['database_server'],
    #                 'link_target_base_fullname_': base_vals['base_fullname_'],
    #                 'link_target_base_fulldomain': base_vals['base_fulldomain'],
    #             })
    #
    #
    #     return vals

    # def reload(self, cr, uid, ids, context=None):
    #     for link_id in ids:
    #         vals = self.get_vals(cr, uid, link_id, context=context)
    #         self.deploy(cr, uid, vals, context=context)
    #     return

    def deploy_link(self, cr, uid, vals, context={}):
        return

    def purge_link(self, cr, uid, vals, context={}):
        return

    def control(self):
        if not self.target:
            self.log(
                'The target isnt configured in the link, skipping deploy link')
            return False
        app_links = self.env['clouder.application.link'].search([
            ('application_id', '=', self.base_id.application_id.id),
            ('name.code', '=', self.target.application_id.code)])
        if app_links:
            self.log(
                'The target isnt in the application link '
                'for base, skipping deploy link')
            return
        if app_links[0].base:
            self.log('This application isnt for base, skipping deploy link')
            return

    @api.multi
    def deploy_(self):
        self.purge_()
        self.control() and self.deploy_link()

    @api.multi
    def purge_(self):
        self.control() and self.purge_link()
