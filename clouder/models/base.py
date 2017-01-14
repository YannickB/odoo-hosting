# -*- coding: utf-8 -*-
# Copyright 2015 Clouder SASU
# License LGPL-3.0 or later (http://gnu.org/licenses/lgpl.html).


from datetime import datetime, timedelta
import logging
import re

try:
    from odoo import models, fields, api
except ImportError:
    from openerp import models, fields, api


from ..tools import generate_random_password


_logger = logging.getLogger(__name__)


class ClouderBase(models.Model):
    """
    Define the base object, which represent all websites hosted in this clouder
    with a specific url and a specific database.
    """

    _name = 'clouder.base'
    _inherit = ['clouder.model']
    _sql_constraints = [
        ('name_uniq', 'unique (name,domain_id)',
         'Name must be unique per domain !')
    ]

    name = fields.Char('Name', required=True)
    domain_id = fields.Many2one('clouder.domain', 'Domain name', required=True)
    environment_id = fields.Many2one('clouder.environment', 'Environment',
                                     required=True)
    title = fields.Char('Title', required=True)
    application_id = fields.Many2one('clouder.application', 'Application',
                                     required=True)
    service_id = fields.Many2one(
        'clouder.service', 'Service', required=True)
    admin_name = fields.Char('Admin name', required=True)
    admin_password = fields.Char(
        'Admin password',
        required=True,
        default=lambda s: generate_random_password(20),
    )
    admin_email = fields.Char('Admin email', required=True)
    poweruser_name = fields.Char('PowerUser name')
    poweruser_password = fields.Char(
        'PowerUser password',
        default=lambda s: generate_random_password(12),
    )
    poweruser_email = fields.Char('PowerUser email')
    build = fields.Selection(
        [('none', 'No action'), ('build', 'Build'), ('restore', 'Restore')],
        'Build?', default='build')
    ssl_only = fields.Boolean('SSL Only?', default=True)
    test = fields.Boolean('Test?')
    lang = fields.Selection(
        [('en_US', 'en_US'), ('fr_FR', 'fr_FR')],
        'Language', required=True, default='en_US')
    state = fields.Selection([
        ('installing', 'Installing'), ('enabled', 'Enabled'),
        ('blocked', 'Blocked'), ('removing', 'Removing')],
        'State', readonly=True)
    option_ids = fields.One2many('clouder.base.option', 'base_id', 'Options')
    link_ids = fields.One2many('clouder.base.link', 'base_id', 'Links')
    parent_id = fields.Many2one('clouder.base.child', 'Parent')
    child_ids = fields.One2many('clouder.base.child',
                                'base_id', 'Childs')
    metadata_ids = fields.One2many(
        'clouder.base.metadata', 'base_id', 'Metadata')
    time_between_backup = fields.Integer('Minutes between each backup')
    backup_expiration = fields.Integer('Days before backup expiration')
    date_next_backup = fields.Datetime('Next backup planned')
    backup_comment = fields.Text('Backup Comment')
    auto_backup = fields.Boolean('Backup?', default=True)
    reset_each_day = fields.Boolean('Reset each day?')
    cert_key = fields.Text('Cert Key')
    cert_cert = fields.Text('Cert')
    cert_renewal_date = fields.Date('Cert renewal date')
    reset_id = fields.Many2one('clouder.base', 'Reset with this base')
    backup_ids = fields.Many2many(
        'clouder.service', 'clouder_base_backup_rel',
        'base_id', 'backup_id', 'Backup services', required=True)
    public = fields.Boolean('Public?')

    @property
    def is_root(self):
        """
        Property returning is this base is the root of the domain or not.
        """
        if self.name == 'www':
            return True
        return False

    @property
    def fullname(self):
        """
        Property returning the full name of the base.
        """
        return '%s-%s' % (
            self.application_id.fullcode,
            self.fulldomain.replace('.', '-'),
        )

    @property
    def fullname_(self):
        """
        Property returning the full name of the base with all - replace by
        underscore (databases compatible names).
        """
        return self.fullname.replace('-', '_')

    @property
    def fulldomain(self):
        """
        Property returning the full url of the base.
        """
        if self.is_root:
            return self.domain_id.name
        return '%s.%s' % (self.name, self.domain_id.name)

    @property
    def databases(self):
        """
        Property returning all databases names used for this base, in a dict.
        """
        databases = {'single': self.fullname_}
        if self.application_id.type_id.multiple_databases:
            dbs = self.application_id.type_id.multiple_databases.split(',')
            databases = {
                db: '%s_%s' % (self.fullname_, db) for db in dbs
            }
        return databases

    @property
    def databases_comma(self):
        """
        Property returning all databases names used for this base,
        separated by a comma.
        """
        return ','.join([d for k, d in self.databases.iteritems()])

    @property
    def http_port(self):
        return self.service_id.childs['exec'] and \
            self.service_id.childs['exec'].ports['http']['hostport']

    @property
    def options(self):
        """
        Property returning a dictionary containing the value of all options
        for this base, even is they are not defined here.
        """
        options = {}
        for option in \
                self.application_id.type_id.option_ids:
            if option.type == 'base':
                options[option.name] = {'id': option.id, 'name': option.id,
                                        'value': option.default}
        for option in self.option_ids:
            options[option.name.name] = {'id': option.id,
                                         'name': option.name.id,
                                         'value': option.value}
        return options

    @property
    def links(self):
        """
        Property returning a dictionary containing the value of all links
        for this base.
        """
        links = {}
        for link in self.link_ids:
            links[link.name.name.code] = link
        return links

    @api.multi
    @api.constrains('name', 'admin_name', 'admin_email', 'poweruser_email')
    def _check_forbidden_chars_credentials(self):
        """
        Check that the base name and some other fields does not contain any
        forbidden characters.
        """
        if not re.match(r"^[\w\d-]*$", self.name):
            self.raise_error(
                "Name can only contains letters, digits and -",
            )
        if not re.match(r"^[\w\d_.@-]*$", self.admin_name):
            self.raise_error(
                "Admin name can only contains letters, digits and underscore",
            )
        if self.admin_email\
                and not re.match(r"^[\w\d_.@-]*$", self.admin_email):
            self.raise_error(
                "Admin email can only contains letters, "
                "digits, underscore, - and @"
            )
        if self.poweruser_email \
                and not re.match(r"^[\w\d_.@-]*$", self.poweruser_email):
            self.raise_error(
                "Poweruser email can only contains letters, "
                "digits, underscore, - and @"
            )

    @api.multi
    @api.constrains('service_id', 'application_id')
    def _check_application(self):
        """
        Check that the application of the base is the same than application
        of services.
        """
        if self.application_id.id != \
                self.service_id.application_id.id:
            self.raise_error(
                "The application of base must be the same "
                "than the application of the service."
            )

    @api.multi
    def onchange_application_id_vals(self, vals):
        """
        Update the options, links and some other fields when we change
        the application_id field.
        """
        if 'application_id' in vals and vals['application_id']:
            application = self.env['clouder.application'].browse(
                vals['application_id'])

            if 'admin_name' not in vals or not vals['admin_name']:
                vals['admin_name'] = application.admin_name \
                    and application.admin_name \
                    or self.email_sysadmin
            if 'admin_email' not in vals or not vals['admin_email']:
                vals['admin_email'] = application.admin_email \
                    and application.admin_email \
                    or self.email_sysadmin

            options = []
            # Getting sources for new options
            option_sources = {x.id: x for x in application.type_id.option_ids}
            sources_to_add = option_sources.keys()
            # Checking old options
            if 'option_ids' in vals:
                for option in vals['option_ids']:
                    # Standardizing for possible odoo x2m input
                    if isinstance(option, (list, tuple)):
                        option = {
                            'name': option[2].get('name', False),
                            'value': option[2].get('value', False)
                        }
                        # This case means we do not have an odoo recordset
                        # and need to load the link manually
                        if isinstance(option['name'], int):
                            option['name'] = \
                                self.env['clouder.application.type.option'].\
                                browse(option['name'])
                    else:
                        option = {
                            'name': getattr(option, 'name', False),
                            'value': getattr(option, 'value', False)
                        }
                    # Keeping the option if there is a match with the sources
                    if option['name'] and option['name'].id in option_sources:
                        option['source'] = option_sources[option['name'].id]

                        if option['source'].type == 'base' \
                                and option['source'].auto:
                            # Updating the default value
                            # if there is no current one set
                            options.append((0, 0, {
                                'name': option['source'].id,
                                'value':
                                    option['value'] or
                                    option['source'].get_default}))

                            # Removing the source id from those to add later
                            sources_to_add.remove(option['name'].id)

            # Adding missing option from sources
            for def_opt_key in sources_to_add:
                if option_sources[def_opt_key].type == 'base' \
                        and option_sources[def_opt_key].auto:
                    options.append((0, 0, {
                        'name': option_sources[def_opt_key].id,
                        'value': option_sources[def_opt_key].get_default
                    }))

            # Replacing old options
            vals['option_ids'] = options

            link_sources = {
                x.id: x for code, x in application.links.iteritems()}
            sources_to_add = link_sources.keys()
            links_to_process = []
            # Checking old links
            if 'link_ids' in vals:
                for link in vals['link_ids']:
                    # Standardizing for possible odoo x2m input
                    if isinstance(link, (list, tuple)):
                        link = {
                            'name': link[2].get('name', False),
                            'required': link[2].get('required', False),
                            'auto': link[2].get('auto', False),
                            'next': link[2].get('next', False)
                        }
                        # This case means we do not have an odoo recordset
                        # and need to load the link manually
                        if isinstance(link['name'], int):
                            link['name'] = \
                                self.env['clouder.application.link'].\
                                browse(link['name'])
                    else:
                        link = {
                            'name': getattr(link, 'name', False),
                            'required': getattr(link, 'required', False),
                            'auto': getattr(link, 'auto', False),
                            'next': getattr(link, 'next', False)
                        }
                    # Keeping the link if there is a match with the sources
                    if link['name'] and link['name'].id in link_sources:
                        link['source'] = link_sources[link['name'].id]
                        links_to_process.append(link)

                        # Remove used link from sources
                        sources_to_add.remove(link['name'].id)

            # Adding links from source
            for def_key_link in sources_to_add:
                link = {
                    'name': getattr(link_sources[def_key_link], 'name', False),
                    'required': getattr(
                        link_sources[def_key_link], 'required', False),
                    'auto': getattr(link_sources[def_key_link], 'auto', False),
                    'next': getattr(link_sources[def_key_link], 'next', False),
                    'source': link_sources[def_key_link]
                }
                links_to_process.append(link)

            # Running algorithm to determine new links
            links = []
            for link in links_to_process:
                if link['source'].base and link['source'].auto:
                    next_id = link['next']
                    if 'parent_id' in vals and vals['parent_id']:
                        parent = self.env['clouder.base.child'].browse(
                            vals['parent_id'])
                        for parent_link in parent.base_id.link_ids:
                            if link['source'].name.code == \
                                    parent_link.name.name.code \
                                    and parent_link.target:
                                next_id = parent_link.target.id
                    context = self.env.context
                    if not next_id and 'base_links' in context:
                        fullcode = link['source'].name.fullcode
                        if fullcode in context['base_links']:
                            next_id = context['base_links'][fullcode]
                    if not next_id:
                        next_id = link['source'].next.id
                    if not next_id:
                        target_ids = self.env['clouder.service'].search([
                            ('application_id.code', '=',
                             link['source'].name.code),
                            ('parent_id', '=', False)])
                        if target_ids:
                            next_id = target_ids[0].id
                    links.append((0, 0, {'name': link['source'].name.id,
                                         'required': link['required'],
                                         'auto': link['auto'],
                                         'target': next_id}))
            # Replacing old links
            vals['link_ids'] = links

            childs = []
            # Getting source for childs
            child_sources = {x.id: x for x in application.child_ids}
            sources_to_add = child_sources.keys()
            childs_to_process = []

            # Checking for old childs
            if 'child_ids' in vals:
                for child in vals['child_ids']:
                    # Standardizing for possible odoo x2m input
                    if isinstance(child, (list, tuple)):
                        child = {
                            'name': child[2].get('name', False),
                            'sequence': child[2].get('sequence', False)
                        }
                        # This case means we do not have an odoo recordset
                        # and need to load the link manually
                        if isinstance(child['name'], int):
                            child['name'] = self.env['clouder.application'].\
                                browse(child['name'])
                    else:
                        child = {
                            'name': getattr(child, 'name', False),
                            'sequence': getattr(child, 'sequence', False)
                        }
                    if child['name'] and child['name'].id in child_sources:
                        child['source'] = child_sources[child['name'].id]
                        childs_to_process.append(child)

                        # Removing from sources
                        sources_to_add.remove(child['name'].id)

            # Adding remaining childs from source
            for def_child_key in sources_to_add:
                child = {
                    'name': getattr(
                        child_sources[def_child_key], 'name', False),
                    'sequence': getattr(
                        child_sources[def_child_key], 'sequence', False),
                    'source': child_sources[def_child_key]
                }
                childs_to_process.append(child)

            # Processing new childs
            for child in childs_to_process:
                if child['source'].required and child['source'].base:
                    childs.append((0, 0, {
                        'name': child['source'].id,
                        'sequence':  child['sequence']}))

            # Replacing old childs
            vals['child_ids'] = childs

            # Processing Metadata
            metadata_vals = []
            metadata_sources = {
                x.id: x for x in application.metadata_ids
                if x.clouder_type == 'base'}
            sources_to_add = metadata_sources.keys()
            metadata_to_process = []
            if 'metadata_ids' in vals:
                for metadata in vals['metadata_ids']:
                    # Standardizing for possible odoo x2m input
                    if isinstance(metadata, (list, tuple)):
                        metadata = {
                            'name': metadata[2].get('name', False),
                            'value_data': metadata[2].get('value_data', False)
                        }
                        # This case means we do not have an odoo recordset
                        # and need to load the link manually
                        if isinstance(metadata['name'], int):
                            metadata['name'] = \
                                self.env['clouder.application']\
                                .browse(metadata['name'])
                    else:
                        metadata = {
                            'name': getattr(metadata, 'name', False),
                            'value_data': getattr(
                                metadata, 'value_data', False)
                        }
                    # Processing metadata and adding to list
                    if metadata['name'] \
                            and metadata['name'].id in metadata_sources:
                        metadata['source'] = \
                            metadata_sources[metadata['name'].id]
                        metadata['value_data'] = \
                            metadata['value_data'] \
                            or metadata['source'].default_value
                        metadata_to_process.append(metadata)

                        # Removing from sources
                        sources_to_add.remove(metadata['name'].id)

            # Adding remaining metadata from source
            for metadata_key in sources_to_add:
                metadata = {
                    'name': getattr(
                        metadata_sources[metadata_key], 'name', False),
                    'value_data': metadata_sources[metadata_key].default_value,
                    'source': metadata_sources[metadata_key]
                }
                metadata_to_process.append(metadata)

            # Processing new metadata
            for metadata in metadata_to_process:
                if metadata['source'].clouder_type == 'base':
                    metadata_vals.append((0, 0, {
                        'name': metadata['source'].id,
                        'value_data':  metadata['value_data']}))

            # Replacing old metadata
            vals['metadata_ids'] = metadata_vals

            if 'backup_ids' not in vals or not vals['backup_ids']:
                if application.base_backup_ids:
                    vals['backup_ids'] = [(6, 0, [
                        b.id for b in application.base_backup_ids])]
                else:
                    backups = self.env['clouder.service'].search([
                        ('application_id.type_id.name', '=', 'backup')])
                    if backups:
                        vals['backup_ids'] = [(6, 0, [backups[0].id])]

            vals['auto_backup'] = application.auto_backup

            vals['time_between_backup'] = \
                application.base_time_between_backup
            vals['backup_expiration'] = \
                application.base_backup_expiration

        return vals

    @api.multi
    @api.onchange('application_id')
    def onchange_application_id(self):
        vals = {
            'application_id': self.application_id.id,
            'service_id':
                self.application_id.next_service_id and
                self.application_id.next_service_id.id or False,
            'admin_name': self.admin_name,
            'admin_email': self.admin_email,
            'option_ids': self.option_ids,
            'link_ids': self.link_ids,
            'child_ids': self.child_ids,
            'metadata_ids': self.metadata_ids,
            'parent_id': self.parent_id and self.parent_id.id or False
            }
        vals = self.onchange_application_id_vals(vals)
        self.env['clouder.service.option'].search(
            [('service_id', '=', self.id)]).unlink()
        self.env['clouder.service.link'].search(
            [('service_id', '=', self.id)]).unlink()
        self.env['clouder.service.child'].search(
            [('service_id', '=', self.id)]).unlink()
        for key, value in vals.iteritems():
            setattr(self, key, value)

    @api.multi
    def control_priority(self):
        return self.service_id.check_priority_childs(self)

    @api.model
    def create(self, vals):
        """
        Override create method to create a service and a service if none
        are specified.

        :param vals: The values needed to create the record.
        """
        if ('service_id' not in vals) or (not vals['service_id']):
            application_obj = self.env['clouder.application']
            domain_obj = self.env['clouder.domain']
            service_obj = self.env['clouder.service']
            if 'application_id' not in vals or not vals['application_id']:
                self.raise_error(
                    "You need to specify the application of the base."
                )
            application = application_obj.browse(vals['application_id'])
            if not application.next_node_id:
                self.raise_error(
                    "You need to specify the next node in "
                    "application for the service autocreate."
                )
            if not application.default_image_id.version_ids:
                self.raise_error(
                    "No version for the image linked to the application, "
                    "abandoning service autocreate..."
                )
            if 'domain_id' not in vals or not vals['domain_id']:
                self.raise_error(
                    "You need to specify the domain of the base."
                )
            if 'environment_id' not in vals or not vals['environment_id']:
                self.raise_error(
                    "You need to specify the environment of the base."
                )
            domain = domain_obj.browse(vals['domain_id'])
            service_vals = {
                'name': vals['name'] + '-' +
                domain.name.replace('.', '-'),
                'node_id': application.next_node_id.id,
                'application_id': application.id,
                'image_id': application.default_image_id.id,
                'image_version_id':
                    application.default_image_id.version_ids[0].id,
                'environment_id': vals['environment_id'],
                'suffix': vals['name']
            }
            vals['service_id'] = service_obj.create(service_vals).id

        vals = self.onchange_application_id_vals(vals)

        return super(ClouderBase, self).create(vals)

    @api.multi
    def write(self, vals):
        """
        Override write method to move base if we change the service.

        :param vals: The values to update.
        """

        backup = False
        if 'service_id' in vals:
            self = self.with_context(self.create_log('service change'))
            self = self.with_context(backup_comment='Before service change')
            backup = self.backup_exec(no_enqueue=True, forcebackup=True)
            self.purge()

        res = super(ClouderBase, self).write(vals)
        if backup:
            backup.service_id = vals['service_id']
            self = self.with_context(base_restoration=True)
            self.deploy()
            backup.restore()
            self.end_log()
        if 'auto_backup' in vals and self.auto_backup != vals['auto_backup'] \
                or 'ssl_only' in vals and self.ssl_only != vals['ssl_only']:
            self.deploy_links()

        return res

    @api.multi
    def unlink(self):
        """
        Override unlink method to make a backup before we delete a base.
        """
        self = self.with_context(backup_comment='Before unlink')
        backup = self.backup_exec(no_enqueue=True)
        if self.parent_id:
            self.parent_id.backup_id = backup
        return super(ClouderBase, self).unlink()

    @api.multi
    def backup(self):
        self.do('backup', 'backup_exec')

    @api.multi
    def backup_exec(self, no_enqueue=False, forcebackup=False):
        """
        Make a new backup.
        """
        backup = False
        now = datetime.now()

        if forcebackup:
            self = self.with_context(forcebackup=True)

        if no_enqueue:
            self = self.with_context(no_enqueue=True)

        if 'no_backup' in self.env.context \
                or (not self.auto_backup and
                    'forcebackup' not in self.env.context):
            self.log(
                'This base shall not be backupd or the backup '
                'isnt configured in conf, skipping backup base')
            return

        if no_enqueue:
            self = self.with_context(no_enqueue=True)

        for backup_node in self.backup_ids:
            backup_vals = {
                'name': self.now_bup + '_' + self.fullname,
                'backup_id': backup_node.id,
                # 'repo_id': self.backup_repository_id.id,
                'date_expiration': (now + timedelta(
                    days=self.backup_expiration or
                    self.application_id.base_backup_expiration)
                ).strftime("%Y-%m-%d"),
                'comment': 'backup_comment' in self.env.context and
                           self.env.context['backup_comment'] or
                           self.backup_comment or 'Manual',
                'now_bup': self.now_bup,
                'service_id': self.service_id.id,
                'base_id': self.id,
            }
            backup = self.env['clouder.backup'].create(backup_vals)
        date_next_backup = (datetime.now() + timedelta(
            minutes=self.time_between_backup or
            self.application_id.base_time_between_backup)
        ).strftime("%Y-%m-%d %H:%M:%S")
        self.write({'backup_comment': False,
                    'date_next_backup': date_next_backup})
        return backup

    @api.multi
    def post_reset(self):
        """
        Hook which can be called by submodules to execute commands after we
        reset a base.
        """
        self.deploy_links()
        return

    @api.multi
    def reset_base(self):
        self = self.with_context(no_enqueue=True)
        self.do('reset_base', 'reset_base_exec')

    @api.multi
    def reset_base_exec(self):
        """
        Reset the base with the parent base.

        :param base_name: Specify another base name
        if the reset need to be done in a new base.

        :param service_id: Specify the service_id is the reset
        need to be done in another service.
        """
        base_name = False
        if 'reset_base_name' in self.env.context:
            base_name = self.env.context['reset_base_name']
        service = False
        if 'reset_service' in self.env.context:
            service = self.env.context['reset_service']
        base_reset_id = self.reset_id and self.reset_id or self
        if 'backup_comment' not in self.env.context:
            self = self.with_context(backup_comment='Reset base')
        backup = base_reset_id.backup_exec(no_enqueue=True, forcebackup=True)
        self.with_context(no_backup=True)
        vals = {'base_id': self.id, 'base_restore_to_name': self.name,
                'base_restore_to_domain_id': self.domain_id.id,
                'service_id': self.service_id.id, 'base_no_backup': True}
        if base_name and service:
            vals = {'base_id': False, 'base_restore_to_name': base_name,
                    'base_restore_to_domain_id': self.domain_id.id,
                    'service_id': service.id, 'base_no_backup': True}
        backup.write(vals)
        base = backup.restore()
        base.write({'reset_id': base_reset_id.id})
        base = base.with_context(
            base_reset_fullname_=base_reset_id.fullname_)
        base = base.with_context(
            service_reset_name=base_reset_id.service_id.name)
        # base.deploy_salt()
        base.update_exec()
        base.post_reset()
        base.deploy_post()

    @api.multi
    def deploy_database(self):
        """
        Hook which can be called by submodules to execute commands when we
        want to create the database. If return False, the database will be
        created by default method.
        """
        return False

    @api.multi
    def deploy_build(self):
        """
        Hook which can be called by submodules to execute commands when we
        want to build the database.
        """
        return

    @api.multi
    def deploy_post_restore(self):
        """
        Hook which can be called by submodules to execute commands after we
        restore a database.
        """
        return

    @api.multi
    def deploy_create_poweruser(self):
        """
        Hook which can be called by submodules to execute commands when we
        want to create a poweruser.
        """
        return

    @api.multi
    def deploy_test(self):
        """
        Hook which can be called by submodules to execute commands when we
        want to deploy test datas.
        """
        return

    @api.multi
    def deploy_post(self):
        """
        Hook which can be called by submodules to execute commands after we
        deploy a base.
        """
        return

    @api.multi
    def deploy(self):
        """
        Deploy the base.
        """
        super(ClouderBase, self).deploy()

        if 'base_restoration' in self.env.context:
            return

        if self.child_ids:
            for child in self.child_ids:
                child.create_child_exec()
            return

        # self.deploy_salt()

        self.deploy_database()
        self.log('Database created')

        if self.build == 'build':
            self.deploy_build()

        elif self.build == 'restore':
            # TODO restore from a selected backup
            self.deploy_post_restore()

        if self.build != 'none':
            if self.poweruser_name and self.poweruser_email \
                    and self.admin_name != self.poweruser_name:
                self.deploy_create_poweruser()
            if self.test:
                self.deploy_test()

        self.deploy_post()

        # For shinken
        self = self.with_context(backup_comment='First backup')
        self.backup_exec(no_enqueue=True)

        # if self.application_id.update_bases:
        #     self.service_id.deploy_salt()
        # for key, child in self.service_id.childs.iteritems():
        #     if child.application_id.update_bases:
        #         child.deploy_salt()

    @api.multi
    def purge_post(self):
        """
        Hook which can be called by submodules to execute commands after we
        purge a base.
        """
        return

    @api.multi
    def purge_database(self):
        """
        Purge the database.
        """
        return

    @api.multi
    def purge(self):
        """
        Purge the base.
        """
        self.purge_database()
        self.purge_post()
        # self.purge_salt()

        # if self.application_id.update_bases:
        #     self.service_id.deploy_salt()
        # for key, child in self.service_id.childs.iteritems():
        #     if child.application_id.update_bases:
        #         child.deploy_salt()

        super(ClouderBase, self).purge()

    @api.multi
    def update(self):
        self = self.with_context(no_enqueue=True)
        self.do('update', 'update_exec')

    @api.multi
    def update_exec(self):
        """
        Hook which can be called by submodules to execute commands when we
        want to update a base.
        """
        self = self.with_context(backup_comment='Before update')
        self.backup_exec(no_enqueue=True)
        return

    @api.multi
    def generate_cert(self):
        self = self.with_context(no_enqueue=True)
        self.do('generate_cert', 'generate_cert_exec')

    @api.multi
    def generate_cert_exec(self):
        """
        Generate a new certificate
        """
        return True

    @api.multi
    def renew_cert(self):
        self = self.with_context(no_enqueue=True)
        self.do('renew_cert', 'renew_cert_exec')

    @api.multi
    def renew_cert_exec(self):
        """
        Renew a certificate
        """
        return True
