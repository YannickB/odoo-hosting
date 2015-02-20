# -*- coding: utf-8 -*-
##############################################################################
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

import execute

import logging
_logger = logging.getLogger(__name__)


class ClouderService(models.Model):
    _name = 'clouder.service'
    _inherit = ['clouder.model']


    def name_get(self,cr,uid,ids,context=None):
        res=[]
        for service in self.browse(cr, uid, ids, context=context):
            res.append((service.id,service.name + ' [' + service.container_id.name + '_' + service.container_id.server_id.name +  ']'))
        return res

    def name_search(self, cr, user, name='', args=None, operator='ilike', context=None, limit=100):
        if not args:
            args = []
        # container_obj = self.pool.get('clouder.container')
        if name:
            #
            # container_ids = container_obj.search(cr, user, ['|',('name','=',name),('domain_id.name','=',name)]+ args, limit=limit, context=context)
            # if container_ids:
            #     containers = self.browse(cr, user, container_ids, context=context)
            #     ids = [s.id for s in containers.service_ids]
            # else
            ids = self.search(cr, user, ['|',('name','like',name),'|',('container_id.name','like',name),('container_id.server_id.name','like',name)]+ args, limit=limit, context=context)
        else:
            ids = self.search(cr, user, args, limit=limit, context=context)
        result = self.name_get(cr, user, ids, context=context)
        return result


    name = fields.Char('Name', size=64, required=True)
    application_id = fields.Many2one('clouder.application', 'Application', relation='container_id.application_id', readonly=True)
    application_version_id = fields.Many2one('clouder.application.version', 'Version', domain="[('application_id.container_ids','in',container_id)]", required=True)
    database_password = fields.Char('Database password', size=64, required=True)
    container_id = fields.Many2one('clouder.container', 'Container', required=True)
    skip_analytics = fields.Boolean('Skip Analytics?')
    option_ids = fields.One2many('clouder.service.option', 'service_id', 'Options')
    link_ids = fields.One2many('clouder.service.link', 'service_id', 'Links')
    base_ids = fields.One2many('clouder.base', 'service_id', 'Bases')
    parent_id = fields.Many2one('clouder.service', 'Parent Service')
    sub_service_name = fields.Char('Subservice Name', size=64)
    custom_version = fields.Boolean('Custom Version?')


    _defaults = {
      'database_password': execute.generate_random_password(20),
    }

    _sql_constraints = [
        ('name_uniq', 'unique(container_id,name)', 'Name must be unique per container!'),
    ]

    def _check_application(self, cr, uid, ids, context=None):
        for s in self.browse(cr, uid, ids, context=context):
            if s.application_id.id != s.container_id.application_id.id:
                return False
        return True


    def _check_application_version(self, cr, uid, ids, context=None):
        for s in self.browse(cr, uid, ids, context=context):
            if s.application_id.id != s.application_version_id.application_id.id:
                return False
        return True

    _constraints = [
        (_check_application, "The application of service must be the same than the application of container." , ['container_id']),
        (_check_application_version, "The application of application version must be the same than the application of service." , ['application_id','application_version_id']),
    ]


    @api.multi
    def get_vals(self):

        vals = {}

        vals.update(self.application_version_id.get_vals())

        vals.update(self.container_id.get_vals())

        options = {}
        for option in self.container_id.application_id.type_id.option_ids:
            if option.type == 'service':
                options[option.name] = {'id': option.id, 'name': option.name, 'value': option.default}
        for option in self.option_ids:
            options[option.name.name] = {'id': option.id, 'name': option.name.name, 'value': option.value}

        links = {}
        if 'app_links' in vals:
            for app_code, link in vals['app_links'].iteritems():
                if link['service']:
                    links[app_code] = link
                    links[app_code]['target'] = False
        for link in self.link_ids:
            if link.name.code in links and link.target:
                link_vals = link.target.get_vals()
                links[link.name.code]['target'] = {
                    'link_id': link_vals['container_id'],
                    'link_name': link_vals['container_name'],
                    'link_fullname': link_vals['container_fullname'],
                    'link_ssh_port': link_vals['container_ssh_port'],
                    'link_server_id': link_vals['server_id'],
                    'link_server_domain': link_vals['server_domain'],
                    'link_server_ip': link_vals['server_ip'],
                }
                database = False
                if link.name.code == 'postgres':
                    vals['database_type'] = 'pgsql'
                    database = 'postgres'
                elif link.name.code == 'mysql':
                    vals['database_type'] = 'mysql'
                    database = 'mysql'
                if database:
                    vals.update({
                        'database_id': link_vals['container_id'],
                        'database_fullname': link_vals['container_fullname'],
                        'database_ssh_port': link_vals['container_ssh_port'],
                        'database_server_id': link_vals['server_id'],
                        'database_server_domain': link_vals['server_domain'],
                        'database_root_password': link_vals['container_root_password'],
                    })
                    if links[link.name.code]['make_link'] and vals['database_server_id'] == vals['server_id']:
                        vals['database_server'] = database
                    else:
                        vals['database_server'] = vals['database_server_domain']
        for app_code, link in links.iteritems():
            if link['required'] and not link['target']:
                raise except_orm(_('Data error!'),
                    _("You need to specify a link to " + link['name'] + " for the service " + self.name))
            if not link['target']:
                del links[app_code]

        service_fullname = vals['container_name'] + '-' + self.name
        db_user = service_fullname.replace('-','_')
        if not 'database_type' in vals:
            raise except_orm(_('Data error!'),
                _("You need to specify a database in the links of the service " + self.name + " " + vals['container_fullname']))
        if vals['database_type'] == 'mysql':
            db_user = vals['container_name'][:10] + '_' + self.name[:4]
            db_user = db_user.replace('-','_')
        vals.update({
            'service_id': self.id,
            'service_name': self.name,
            'service_fullname': service_fullname,
            'service_db_user': db_user,
            'service_db_password': self.database_password,
            'service_skip_analytics': self.skip_analytics,
            'service_full_localpath': vals['apptype_localpath_services'] + '/' + self.name,
            'service_full_localpath_files': vals['apptype_localpath_services'] + '/' + self.name + '/files',
            'service_options': options,
            'service_links': links,
            'service_subservice_name': self.sub_service_name,
            'service_custom_version': self.custom_version
        })

        return vals

    def create(self, cr, uid, vals, context={}):
        if 'container_id' in vals:
            container = self.pool.get('clouder.container').browse(cr, uid, vals['container_id'], context=context)
            application = container.application_id
            links = {}
            for link in  application.link_ids:
                if link.service:
                    links[link.name.id] = {}
                    links[link.name.id]['required'] = link.required
                    links[link.name.id]['name'] = link.name.name
                    links[link.name.id]['target'] = link.auto and link.next and link.next.id or False
            if 'link_ids' in vals:
                for link in vals['link_ids']:
                    link = link[2]
                    if link['name'] in links:
                        links[link['name']]['target'] = link['target']
                del vals['link_ids']
            vals['link_ids'] = []
            for application_id, link in links.iteritems():
                if link['required'] and not link['target']:
                    raise except_orm(_('Data error!'),
                        _("You need to specify a link to " + link['name'] + " for the service " + vals['name']))
                vals['link_ids'].append((0,0,{'name': application_id, 'target': link['target']}))
        return super(ClouderService, self).create(cr, uid, vals, context=context)

    def write(self, cr, uid, ids, vals, context={}):
        if 'application_version_id' in vals:
            services_old = []
            for service in self.browse(cr, uid, ids, context=context):
                services_old.append(self.get_vals(cr, uid, service.id, context=context))
        res = super(ClouderService, self).write(cr, uid, ids, vals, context=context)
        if 'application_version_id' in vals:
            for service_vals in services_old:
                self.check_files(cr, uid, service_vals, context=context)
        if 'application_version_id' in vals or 'custom_version' in vals:
            for service in self.browse(cr, uid, ids, context=context):
                vals = self.get_vals(cr, uid, service.id, context=context)
                self.deploy_files(cr, uid, vals, context=context)
        return res


    def unlink(self, cr, uid, ids, context={}):
        base_obj = self.pool.get('clouder.base')
        for service in self.browse(cr, uid, ids, context=context):
            base_obj.unlink(cr, uid, [b.id for b in service.base_ids], context=context)
        return super(ClouderService, self).unlink(cr, uid, ids, context=context)

    def install_formation(self, cr, uid, ids, context={}):
        self.write(cr, uid, ids, {'sub_service_name': 'formation'}, context=context)
        self.install_subservice(cr, uid, ids, context=context)

    def install_test(self, cr, uid, ids, context={}):
        self.write(cr, uid, ids, {'sub_service_name': 'test'}, context=context)
        self.install_subservice(cr, uid, ids, context=context)

    def install_subservice(self, cr, uid, ids, context={}):
        base_obj = self.pool.get('clouder.base')
        for service in self.browse(cr, uid, ids, context=context):
            if not service.sub_service_name or service.sub_service_name == service.name:
                continue
            service_ids = self.search(cr, uid, [('name','=',service.sub_service_name),('container_id','=',service.container_id.id)],context=context)
            self.unlink(cr, uid, service_ids,context=context)
            options = []
            type_ids = self.pool.get('clouder.application.type.option').search(cr, uid, [('apptype_id','=',service.container_id.application_id.type_id.id),('name','=','port')], context=context)
            if type_ids:
                if service.sub_service_name == 'formation':
                    options =[(0,0,{'name': type_ids[0], 'value': 'port-formation'})]
                if service.sub_service_name == 'test':
                    options = [(0,0,{'name': type_ids[0], 'value': 'port-test'})]
            links = []
            for link in service.link_ids:
                links.append((0,0,{
                    'name': link.name.id,
                    'target': link.target and link.target.id or False
                }))
            service_vals = {
                'name': service.sub_service_name,
                'container_id': service.container_id.id,
                'application_version_id': service.application_version_id.id,
                'parent_id': service.id,
                'option_ids': options,
                'link_ids': links
            }
            service_id = self.create(cr, uid, service_vals, context=context)
            for base in service.base_ids:
                subbase_name = service.sub_service_name + '-' + base.name
                context['save_comment'] = 'Duplicate base into ' + subbase_name
                base_obj._reset_base(cr, uid, [base.id], subbase_name, service_id=service_id, context=context)
        self.write(cr, uid, ids, {'sub_service_name': False}, context=context)


    def deploy_to_parent(self, cr, uid, ids, context={}):
        for service in  self.browse(cr, uid, ids, context=context):
            if not service.parent_id:
                continue
            vals = {}
            if not service.parent_id.custom_version:
                vals['application_version_id'] = service.application_version_id.id
            else:
                context['files_from_service'] = service.name
                vals['custom_version'] = True
            self.write(cr, uid, [service.parent_id.id], vals, context=context)

    def deploy_post_service(self, cr, uid, vals, context=None):
        return


    def deploy(self, cr, uid, vals, context=None):
        container_obj = self.pool.get('clouder.container')
        context.update({'clouder-self': self, 'clouder-cr': cr, 'clouder-uid': uid})

        self.purge(cr, uid, vals, context=context)

        execute.log('Creating database user', context=context)

        #SI postgres, create user
        if vals['database_type'] != 'mysql':
            ssh, sftp = execute.connect(vals['database_fullname'], username='postgres', context=context)
            execute.execute(ssh, ['psql', '-c', '"CREATE USER ' + vals['service_db_user'] + ' WITH PASSWORD \'' + vals['service_db_password'] + '\' CREATEDB;"'], context)
            ssh.close()
            sftp.close()

            ssh, sftp = execute.connect(vals['container_fullname'], username=vals['apptype_system_user'], context=context)
            execute.execute(ssh, ['sed', '-i', '"/:*:' + vals['service_db_user'] + ':/d" ~/.pgpass'], context)
            execute.execute(ssh, ['echo "' + vals['database_server'] + ':5432:*:' + vals['service_db_user'] + ':' + vals['service_db_password'] + '" >> ~/.pgpass'], context)
            execute.execute(ssh, ['chmod', '700', '~/.pgpass'], context)
            ssh.close()
            sftp.close()

        else:
            ssh, sftp = execute.connect(vals['database_fullname'], context=context)
            execute.execute(ssh, ["mysql -u root -p'" + vals['database_root_password'] + "' -se \"create user '" + vals['service_db_user'] + "' identified by '" + vals['service_db_password'] + "';\""], context)
            ssh.close()
            sftp.close()

        execute.log('Database user created', context)

        ssh, sftp = execute.connect(vals['container_fullname'], username=vals['apptype_system_user'], context=context)
        execute.execute(ssh, ['mkdir', '-p', vals['service_full_localpath']], context)
        ssh.close()
        sftp.close()

        self.deploy_files(cr, uid, vals, context=context)
        self.deploy_post_service(cr, uid, vals, context)

        container_obj.start(cr, uid, vals, context=context)

        # ssh, sftp = connect(vals['server_domain'], vals['apptype_system_user'], context=context)
        # if sftp.stat(vals['service_fullpath']):
            # log('Service ok', context=context)
        # else:
            # log('There was an error while creating the instance', context=context)
            # context['log_state'] == 'ko'
            # ko_log(context=context)
        # ssh.close()


    def purge_pre_service(self, cr, uid, vals, context=None):
        return

    def purge(self, cr, uid, vals, context={}):
        context.update({'clouder-self': self, 'clouder-cr': cr, 'clouder-uid': uid})
        self.purge_files(cr, uid, vals, context=context)
        self.purge_pre_service(cr, uid, vals, context)

        ssh, sftp = execute.connect(vals['container_fullname'], username=vals['apptype_system_user'], context=context)
        execute.execute(ssh, ['rm', '-rf', vals['service_full_localpath']], context)
        ssh.close()
        sftp.close()

        if vals['database_type'] != 'mysql':
            ssh, sftp = execute.connect(vals['database_fullname'], username='postgres', context=context)
            execute.execute(ssh, ['psql', '-c', '"DROP USER ' + vals['service_db_user'] + ';"'], context)
            ssh.close()
            sftp.close()

            ssh, sftp = execute.connect(vals['container_fullname'], username=vals['apptype_system_user'], context=context)
            execute.execute(ssh, ['sed', '-i', '"/:*:' + vals['service_db_user'] + ':/d" ~/.pgpass'], context)
            ssh.close()
            sftp.close()

        else:
            ssh, sftp = execute.connect(vals['database_fullname'], context=context)
            execute.execute(ssh, ["mysql -u root -p'" + vals['database_root_password'] + "' -se \"drop user " + vals['service_db_user'] + ";\""], context)
            ssh.close()
            sftp.close()

        return


    def check_files(self, cr, uid, vals, context={}):
        context.update({'clouder-self': self, 'clouder-cr': cr, 'clouder-uid': uid})
        service_ids = self.search(cr, uid, [('application_version_id', '=', vals['app_version_id']),('container_id.server_id','=',vals['server_id'])], context=context)
        if vals['service_id'] in service_ids:
            service_ids.remove(vals['service_id'])
        if not service_ids:
            ssh, sftp = execute.connect(vals['server_domain'], vals['server_ssh_port'], 'root', context)
            execute.execute(ssh, ['rm', '-rf', vals['app_version_full_hostpath']], context)
            ssh.close()
            sftp.close()


    def deploy_files(self, cr, uid, vals, context={}):
        context.update({'clouder-self': self, 'clouder-cr': cr, 'clouder-uid': uid})
        base_obj = self.pool.get('clouder.base')
        self.purge_files(cr, uid, vals, context=context)
        ssh, sftp = execute.connect(vals['server_domain'], vals['server_ssh_port'], 'root', context)

        if not execute.exist(sftp, vals['app_version_full_hostpath']):
            ssh_archive, sftp_archive = execute.connect(vals['archive_fullname'], context=context)
            tmp = '/tmp/' + vals['app_version_fullname'] + '.tar.gz'
            execute.log('sftp get ' + vals['app_version_full_archivepath_targz'] + ' ' + tmp, context)
            sftp_archive.get(vals['app_version_full_archivepath_targz'], tmp)
            ssh_archive.close()
            sftp_archive.close()
            execute.execute(ssh, ['mkdir', '-p', vals['app_version_full_hostpath']], context)
            execute.log('sftp put ' + tmp + ' ' + vals['app_version_full_hostpath'] + '.tar.gz', context)
            sftp.put(tmp, vals['app_version_full_hostpath'] + '.tar.gz')
            execute.execute(ssh, ['tar', '-xf', vals['app_version_full_hostpath'] + '.tar.gz', '-C', vals['app_version_full_hostpath']], context)
            execute.execute(ssh, ['rm', vals['app_full_hostpath'] + '/' + vals['app_version_name'] + '.tar.gz'], context)

        ssh.close()
        sftp.close()

        ssh, sftp = execute.connect(vals['container_fullname'], username=vals['apptype_system_user'], context=context)
        if 'files_from_service' in context:
            execute.execute(ssh, ['cp', '-R', vals['apptype_localpath_services'] + '/' + context['files_from_service'] + '/files', vals['service_full_localpath_files']], context)
        elif vals['service_custom_version'] or not vals['apptype_symlink']:
            execute.execute(ssh, ['cp', '-R', vals['app_version_full_localpath'], vals['service_full_localpath_files']], context)

        else:
            execute.execute(ssh, ['ln', '-s', vals['app_version_full_localpath'], vals['service_full_localpath_files']], context)
        service = self.browse(cr, uid, vals['service_id'], context=context)
        for base in service.base_ids:
            base_obj.save(cr, uid, [base.id], context=context)
            base_vals = base_obj.get_vals(cr, uid, base.id, context=context)
            base_obj.update_base(cr, uid, base_vals, context=context)

        ssh.close()
        sftp.close()

    def purge_files(self, cr, uid, vals, context={}):
        context.update({'clouder-self': self, 'clouder-cr': cr, 'clouder-uid': uid})
        ssh, sftp = execute.connect(vals['container_fullname'], username=vals['apptype_system_user'], context=context)
        execute.execute(ssh, ['rm', '-rf', vals['service_full_localpath_files']], context)
        ssh.close()
        sftp.close()

        self.check_files(cr, uid, vals, context=context)


class ClouderServiceOption(models.Model):
    _name = 'clouder.service.option'

    service_id = fields.Many2one('clouder.service', 'Service', ondelete="cascade", required=True)
    name = fields.Many2one('clouder.application.type.option', 'Option', required=True)
    value = fields.Text('Value')


    _sql_constraints = [
        ('name_uniq', 'unique(service_id,name)', 'Option name must be unique per service!'),
    ]


class ClouderServiceLink(models.Model):
    _name = 'clouder.service.link'

    service_id = fields.Many2one('clouder.service', 'Service', ondelete="cascade", required=True)
    name = fields.Many2one('clouder.application', 'Application', required=True)
    target = fields.Many2one('clouder.container', 'Target')


    _sql_constraints = [
        ('name_uniq', 'unique(service_id,name)', 'Links must be unique per service!'),
    ]


    def get_vals(self, cr, uid, id, context={}):
        vals = {}

        link = self.browse(cr, uid, id, context=context)

        vals.update(self.pool.get('clouder.service').get_vals(cr, uid, link.service_id.id, context=context))
        if link.target:
            target_vals = self.pool.get('clouder.container').get_vals(cr, uid, link.target.id, context=context)
            vals.update({
                'link_target_container_id': target_vals['container_id'],
                'link_target_container_name': target_vals['container_name'],
                'link_target_container_fullname': target_vals['container_fullname'],
                'link_target_app_id': target_vals['app_id'],
                'link_target_app_code': target_vals['app_code'],
            })


        return vals

    def reload(self, cr, uid, ids, context=None):
        for link_id in ids:
            vals = self.get_vals(cr, uid, link_id, context=context)
            self.deploy(cr, uid, vals, context=context)
        return

    def deploy_link(self, cr, uid, vals, context={}):
        return

    def deploy(self, cr, uid, vals, context={}):
        context.update({'clouder-self': self, 'clouder-cr': cr, 'clouder-uid': uid})
        self.purge(cr, uid, vals, context=context)
        if not 'link_target_container_id' in vals:
            execute.log('The target isnt configured in the link, skipping deploy link', context)
            return
        if vals['link_target_app_code'] not in vals['service_links']:
            execute.log('The target isnt in the application link for service, skipping deploy link', context)
            return
        if not vals['service_links'][vals['link_target_app_code']]['service']:
            execute.log('This application isnt for service, skipping deploy link', context)
            return
        self.deploy_link(cr, uid, vals, context=context)

    def purge_link(self, cr, uid, vals, context={}):
        return

    def purge(self, cr, uid, vals, context={}):
        context.update({'clouder-self': self, 'clouder-cr': cr, 'clouder-uid': uid})
        if not 'link_target_container_id' in vals:
            execute.log('The target isnt configured in the link, skipping deploy link', context)
            return
        if vals['link_target_app_code'] not in vals['service_links']:
            execute.log('The target isnt in the application link for service, skipping deploy link', context)
            return
        if not vals['service_links'][vals['link_target_app_code']]['service']:
            execute.log('This application isnt for service, skipping deploy link', context)
            return
        self.purge_link(cr, uid, vals, context=context)