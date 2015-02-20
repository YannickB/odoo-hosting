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

from datetime import datetime
import execute
import ast

import logging
_logger = logging.getLogger(__name__)


class ClouderSaveRepository(models.Model):
    _name = 'clouder.save.repository'
    
    name = fields.Char('Name', size=128, required=True)
    type = fields.Selection([('container','Container'),('base','Base')], 'Name', required=True)
    date_change = fields.Date('Change Date')
    date_expiration = fields.Date('Expiration Date')
    container_name = fields.Char('Container Name', size=64)
    container_server = fields.Char('Container Server', size=128)
    base_name = fields.Char('Base Name', size=64)
    base_domain = fields.Char('Base Domain', size=128)
    save_ids = fields.One2many('clouder.save.save', 'repo_id', 'Saves')


    _order = 'create_date desc'

    @api.multi
    def get_vals(self):

        vals = {}

        vals.update(self.env.ref('clouder.clouder_settings').get_vals())

        vals.update({
            'saverepo_id': self.id,
            'saverepo_name': self.name,
            'saverepo_type': self.type,
            'saverepo_date_change': self.date_change,
            'saverepo_date_expiration': self.date_expiration,
            'saverepo_container_name': self.container_name,
            'saverepo_container_server': self.container_server,
            'saverepo_base_name': self.base_name,
            'saverepo_base_domain': self.base_domain,
        })

        return vals

class ClouderSaveSave(models.Model):
    _name = 'clouder.save.save'
    _inherit = ['clouder.model']

    name = fields.Char('Name', size=256, required=True)
    type = fields.Selection([('container','Container'),('base','Base')], 'Type', related='repo_id.type', readonly=True)
    backup_server_id = fields.Many2one('clouder.container', 'Backup Server', required=True)
    repo_id = fields.Many2one('clouder.save.repository', 'Repository', ondelete='cascade', required=True)
    date_expiration = fields.Date('Expiration Date')
    comment = fields.Text('Comment')
    now_bup = fields.Char('Now bup', size=64)
    container_id = fields.Many2one('clouder.container', 'Container')
    container_volumes_comma = fields.Text('Container Volumes comma')
    container_app = fields.Char('Application', size=64)
    container_img = fields.Char('Image', size=64)
    container_img_version = fields.Char('Image Version', size=64)
    container_ports = fields.Text('Ports')
    container_volumes = fields.Text('Volumes')
    container_volumes_comma = fields.Text('Volumes comma')
    container_options = fields.Text('Container Options')
    container_links = fields.Text('Container Links')
    service_id = fields.Many2one('clouder.service', 'Service')
    service_name = fields.Char('Service Name', size=64)
    service_database_id = fields.Many2one('clouder.container', 'Database Container')
    service_options = fields.Text('Service Options')
    service_links = fields.Text('Service Links')
    base_id = fields.Many2one('clouder.base', 'Base')
    base_title = fields.Char('Title', size=64)
    base_app_version = fields.Char('Application Version', size=64)
    base_proxy_id = fields.Many2one('clouder.container', 'Proxy Container')
    base_mail_id = fields.Many2one('clouder.container', 'Mail Container')
    base_container_name = fields.Char('Container', size=64)
    base_container_server = fields.Char('Server', size=64)
    base_admin_passwd = fields.Char('Admin passwd', size=64)
    base_poweruser_name = fields.Char('Poweruser name', size=64)
    base_poweruser_password = fields.Char('Poweruser Password', size=64)
    base_poweruser_email = fields.Char('Poweruser email', size=64)
    base_build = fields.Char('Build', size=64)
    base_test = fields.Boolean('Test?')
    base_lang = fields.Char('Lang', size=64)
    base_nosave = fields.Boolean('No save?')
    base_options = fields.Text('Base Options')
    base_links = fields.Text('Base Links')
    container_name = fields.Char('Container Name', related='repo_id.container_name', size=64, readonly=True)
    container_server = fields.Char('Container Server', related='repo_id.container_server', type='char', size=64, readonly=True)
    container_restore_to_name = fields.Char('Restore to (Name)', size=64)
    container_restore_to_server_id = fields.Many2one('clouder.server', 'Restore to (Server)')
    base_name = fields.Char('Base Name', related='repo_id.base_name', type='char', size=64, readonly=True)
    base_domain = fields.Char('Base Domain', related='repo_id.base_domain', type='char', size=64, readonly=True)
    base_restore_to_name = fields.Char('Restore to (Name)', size=64)
    base_restore_to_domain_id = fields.Many2one('clouder.domain', 'Restore to (Domain)')
    create_date = fields.Datetime('Create Date')


    _order = 'create_date desc'

    @api.multi
    def get_vals(self):
        vals = {}

        if self.base_id:
            vals.update(self.base_id.get_vals())
        elif self.service_id:
            vals.update(self.service_id.get_vals())
        elif self.container_id:
            vals.update(self.container_id.get_vals())

        vals.update(self.repo_id.get_vals())

        backup_server_vals = self.backup_server_id.get_vals()
        vals.update({
            'backup_id': backup_server_vals['container_id'],
            'backup_fullname': backup_server_vals['container_fullname'],
            'backup_server_id': backup_server_vals['server_id'],
            'backup_server_ssh_port': backup_server_vals['server_ssh_port'],
            'backup_server_domain': backup_server_vals['server_domain'],
            'backup_server_ip': backup_server_vals['server_ip'],
            'backup_method': backup_server_vals['app_options']['backup_method']['value']
        })

        vals.update({
            'save_id': self.id,
            'save_name': self.name,
            'saverepo_date_expiration': self.date_expiration,
            'save_comment': self.comment,
            'save_now_bup': self.now_bup,
            'save_now_epoch': (datetime.strptime(self.now_bup, "%Y-%m-%d-%H%M%S") - datetime(1970,1,1)).total_seconds(),
            'save_base_id': self.base_id.id,
            'save_container_volumes': self.container_volumes_comma,
            'save_container_restore_to_name': self.container_restore_to_name or self.base_container_name or vals['saverepo_container_name'],
            'save_container_restore_to_server': self.container_restore_to_server_id.name or self.base_container_server or vals['saverepo_container_server'],
            'save_base_restore_to_name': self.base_restore_to_name or vals['saverepo_base_name'],
            'save_base_restore_to_domain': self.base_restore_to_domain_id.name or vals['saverepo_base_domain'],
            'save_base_dumpfile': vals['saverepo_type'] == 'base' and self.container_app + '_' + self.base_name.replace('-','_') + '_' + self.base_domain.replace('-','_').replace('.','_') + '.dump'
        })
        return vals

    def unlink(self, cr, uid, ids, context={}):
        for save in self.browse(cr, uid, ids, context=context):
            vals = self.get_vals(cr, uid, save.id, context=context)
            self.purge(cr, uid, vals, context=context)
        return super(ClouderSaveSave, self).unlink(cr, uid, ids, context=context)

    def purge(self, cr, uid, vals, context={}):
        context.update({'clouder-self': self, 'clouder-cr': cr, 'clouder-uid': uid})
        ssh, sftp = execute.connect(vals['backup_fullname'], context=context)
        execute.execute(ssh, ['rm', '-rf', '/opt/backup/simple/' + vals['saverepo_name'] + '/'+ vals['save_name']], context)
        if self.search(cr, uid, [('repo_id','=',vals['saverepo_id'])], context=context) == [vals['save_id']]:
            execute.execute(ssh, ['rm', '-rf', '/opt/backup/simple/' + vals['saverepo_name']], context)
            execute.execute(ssh, ['git', '--git-dir=/opt/backup/bup', 'branch', '-D', vals['saverepo_name']], context)
        ssh.close()
        sftp.close()
        return

    def restore_base(self, cr, uid, vals, context=None):
        return

    def restore(self, cr, uid, ids, context={}):
        context.update({'clouder-self': self, 'clouder-cr': cr, 'clouder-uid': uid})
        container_obj = self.pool.get('clouder.container')
        base_obj = self.pool.get('clouder.base')
        server_obj = self.pool.get('clouder.server')
        domain_obj = self.pool.get('clouder.domain')
        application_obj = self.pool.get('clouder.application')
        application_version_obj = self.pool.get('clouder.application.version')
        image_obj = self.pool.get('clouder.image')
        image_version_obj = self.pool.get('clouder.image.version')
        service_obj = self.pool.get('clouder.service')
        for save in self.browse(cr, uid, ids, context=context):
            context = self.create_log(cr, uid, save.id, 'restore', context)
            vals = self.get_vals(cr, uid, save.id, context=context)

            app_ids = application_obj.search(cr, uid, [('code','=',save.container_app)], context=context)
            if not app_ids:
                raise except_orm(_('Error!'),_("Couldn't find application " + save.container_app + ", aborting restoration."))
            img_ids = image_obj.search(cr, uid, [('name','=',save.container_img)], context=context)
            if not img_ids:
                raise except_orm(_('Error!'),_("Couldn't find image " + save.container_img + ", aborting restoration."))
            img_version_ids = image_version_obj.search(cr, uid, [('name','=',save.container_img_version)], context=context)
            # upgrade = True
            if not img_version_ids:
                execute.log("Warning, couldn't find the image version, using latest", context)
                #We do not want to force the upgrade if we had to use latest
                # upgrade = False
                versions = image_obj.browse(cr, uid, img_ids[0], context=context).version_ids
                if not versions: 
                    raise except_orm(_('Error!'),_("Couldn't find versions for image " + save.container_img + ", aborting restoration."))
                img_version_ids = [versions[0].id]

            if save.container_restore_to_name or not save.container_id:
                container_ids = container_obj.search(cr, uid, [('name','=',vals['save_container_restore_to_name']),('server_id.name','=',vals['save_container_restore_to_server'])], context=context)

                if not container_ids:
                    execute.log("Can't find any corresponding container, creating a new one", context)
                    server_ids = server_obj.search(cr, uid, [('name','=',vals['save_container_restore_to_server'])], context=context)
                    if not server_ids:
                        raise except_orm(_('Error!'),_("Couldn't find server " + vals['save_container_restore_to_server'] + ", aborting restoration."))
 
                    ports = []
                    for port, port_vals in ast.literal_eval(save.container_ports).iteritems():
                        del port_vals['id']
                        del port_vals['hostport']
                        ports.append((0,0,port_vals))
                    volumes = []
                    for volume, volume_vals in ast.literal_eval(save.container_volumes).iteritems():
                        del volume_vals['id']
                        volumes.append((0,0,volume_vals))
                    options = []
                    for option, option_vals in ast.literal_eval(save.container_options).iteritems():
                        del option_vals['id']
                        options.append((0,0,option_vals))
                    links = []
                    for link, link_vals in ast.literal_eval(save.container_links).iteritems():
                        if not link_vals['name']:
                            link_app_ids = self.pool.get('clouder.application').search(cr, uid, [('code','=',link_vals['name_name'])], context=context)
                            if link_app_ids:
                                link_vals['name'] = link_app_ids[0]
                            else:
                                continue
                        del link_vals['name_name']
                        links.append((0,0,link_vals))
                    container_vals = {
                        'name': vals['save_container_restore_to_name'],
                        'server_id': server_ids[0],
                        'application_id': app_ids[0],
                        'image_id': img_ids[0],
                        'image_version_id': img_version_ids[0],
                        'port_ids': ports,
                        'volume_ids': volumes,
                        'option_ids': options,
                        'link_ids': links
                    }
                    container_id = container_obj.create(cr, uid, container_vals, context=context)

                else:
                    execute.log("A corresponding container was found", context)
                    container_id = container_ids[0]
            else:
                execute.log("A container_id was linked in the save", context)
                container_id = save.container_id.id

            if vals['saverepo_type'] == 'container':
                vals = self.get_vals(cr, uid, save.id, context=context)
                vals_container = container_obj.get_vals(cr, uid, container_id, context=context)
                if vals_container['image_version_id'] != img_version_ids[0]:
                # if upgrade:
                    container_obj.write(cr, uid, [container_id], {'image_version_id': img_version_ids[0]}, context=context)
                    del context['forcesave']
                    context['nosave'] = True

                context['save_comment'] = 'Before restore ' + save.name
                container_obj.save(cr, uid, [container_id], context=context)

                # vals = self.get_vals(cr, uid, save.id, context=context)
                # vals_container = container_obj.get_vals(cr, uid, container_id, context=context)
                context.update({'clouder-self': self, 'clouder-cr': cr, 'clouder-uid': uid})
                ssh, sftp = execute.connect(vals_container['container_fullname'], context=context)
                execute.execute(ssh, ['supervisorctl', 'stop', 'all'], context)
                execute.execute(ssh, ['supervisorctl', 'start', 'sshd'], context)
                self.restore_action(cr, uid, vals, context=context)
                # ssh, sftp = execute.connect(vals['saverepo_container_server'], 22, 'root', context)
                # execute.execute(ssh, ['docker', 'run', '-t', '--rm', '--volumes-from', vals['saverepo_container_name'], '-v', '/opt/keys/bup:/root/.ssh', 'img_bup:latest', '/opt/restore', 'container', vals['saverepo_name'], vals['save_now_bup'], vals['save_container_volumes']], context)
                # ssh.close()
                # sftp.close()


                for key, volume in vals_container['container_volumes'].iteritems():
                    if volume['user']:
                        execute.execute(ssh, ['chown', '-R', volume['user'] + ':' + volume['user'], volume['name']], context)
                # execute.execute(ssh, ['supervisorctl', 'start', 'all'], context)
                ssh.close()
                sftp.close()
                container_obj.start(cr, uid, vals_container, context=context)

                container_obj.deploy_links(cr, uid, [container_id], context=context)
                self.end_log(cr, uid, save.id, context=context)
                res = container_id


            else:
                # upgrade = False
                app_version_ids = application_version_obj.search(cr, uid, [('name','=',save.base_app_version),('application_id','=', app_ids[0])], context=context)
                if not app_version_ids:
                    execute.log("Warning, couldn't find the application version, using latest", context)
                    #We do not want to force the upgrade if we had to use latest
                    # upgrade = False
                    versions = application_obj.browse(cr, uid, app_version_ids[0], context=context).version_ids
                    if not versions: 
                        raise except_orm(_('Error!'),_("Couldn't find versions for application " + save.container_app + ", aborting restoration."))
                    app_version_ids = [versions[0].id]
                if not save.service_id or save.service_id.container_id.id != container_id:
                    service_ids = service_obj.search(cr, uid, [('name','=',save.service_name),('container_id.id','=',container_id)], context=context)

                    if not service_ids:
                        execute.log("Can't find any corresponding service, creating a new one", context)
                        options = []
                        for option, option_vals in ast.literal_eval(save.service_options).iteritems():
                            del option_vals['id']
                            options.append((0,0,option_vals))
                        links = []
                        for link, link_vals in ast.literal_eval(save.service_links).iteritems():
                            if not link_vals['name']:
                                link_app_ids = self.pool.get('clouder.application').search(cr, uid, [('code','=',link_vals['name_name'])], context=context)
                                if link_app_ids:
                                    link_vals['name'] = link_app_ids[0]
                                else:
                                    continue
                            del link_vals['name_name']
                            links.append((0,0,link_vals))
                        service_vals = {
                            'name': save.service_name,
                            'container_id': container_id,
                            'database_container_id': save.service_database_id.id,
                            'application_version_id': app_version_ids[0],
#                            'option_ids': options,
                            'link_ids': links
                        }
                        service_id = service_obj.create(cr, uid, service_vals, context=context)

                    else:
                        execute.log("A corresponding service was found", context)
                        service_id = service_ids[0]
                else:
                    execute.log("A service_id was linked in the save", context)
                    service_id = save.service_id.id

                if save.base_restore_to_name or not save.base_id:
                    base_ids = base_obj.search(cr, uid, [('name','=',vals['save_base_restore_to_name']),('domain_id.name','=',vals['save_base_restore_to_domain'])], context=context)

                    if not base_ids:
                        execute.log("Can't find any corresponding base, creating a new one", context)
                        domain_ids = domain_obj.search(cr, uid, [('name','=',vals['save_base_restore_to_domain'])], context=context)
                        if not domain_ids:
                            raise except_orm(_('Error!'),_("Couldn't find domain " + vals['save_base_restore_to_domain'] + ", aborting restoration."))
                        options = []
                        for option, option_vals in ast.literal_eval(save.base_options).iteritems():
                            del option_vals['id']
                            options.append((0,0,option_vals))
                        links = []
                        for link, link_vals in ast.literal_eval(save.base_links).iteritems():
                            if not link_vals['name']:
                                link_app_ids = self.pool.get('clouder.application').search(cr, uid, [('code','=',link_vals['name_name'])], context=context)
                                if link_app_ids:
                                    link_vals['name'] = link_app_ids[0]
                                else:
                                    continue
                            del link_vals['name_name']
                            links.append((0,0,link_vals))
                        base_vals = {
                            'name': vals['save_base_restore_to_name'],
                            'service_id': service_id,
                            'application_id': app_ids[0],
                            'domain_id': domain_ids[0],
                            'title': save.base_title,
                            'proxy_id': save.base_proxy_id.id,
                            'mail_id': save.base_mail_id.id,
                            'admin_passwd': save.base_admin_passwd,
                            'poweruser_name': save.base_poweruser_name,
                            'poweruser_passwd': save.base_poweruser_password,
                            'poweruser_email': save.base_poweruser_email,
                            'build': save.base_build,
                            'test': save.base_test,
                            'lang': save.base_lang,
                            'nosave': save.base_nosave,
#                            'option_ids': options,
                            'link_ids': links,
                        }
                        context['base_restoration'] = True
                        base_id = base_obj.create(cr, uid, base_vals, context=context)

                    else:
                        execute.log("A corresponding base was found", context)
                        base_id = base_ids[0]
                else:
                    execute.log("A base_id was linked in the save", context)
                    base_id = save.base_id.id

                vals = self.get_vals(cr, uid, save.id, context=context)
                base_vals = base_obj.get_vals(cr, uid, base_id, context=context)
                if base_vals['app_version_id'] != app_version_ids[0]:
                # if upgrade:
                    base_obj.write(cr, uid, [base_id], {'application_version_id': app_version_ids[0]}, context=context)

                context['save_comment'] = 'Before restore ' + save.name
                base_obj.save(cr, uid, [base_id], context=context)



                self.restore_action(cr, uid, vals, context=context)

                base_obj.purge_db(cr, uid, base_vals, context=context)
                ssh, sftp = execute.connect(base_vals['container_fullname'], username=base_vals['apptype_system_user'], context=context)
                for key, database in base_vals['base_databases'].iteritems():
                    if vals['database_type'] != 'mysql':
                        execute.execute(ssh, ['createdb', '-h', base_vals['database_server'], '-U', base_vals['service_db_user'], base_vals['base_unique_name_']], context)
                        execute.execute(ssh, ['cat', '/base-backup/' + vals['saverepo_name'] + '/' + vals['save_base_dumpfile'], '|', 'psql', '-q', '-h', base_vals['database_server'], '-U', base_vals['service_db_user'], base_vals['base_unique_name_']], context)
                    else:
                        ssh_mysql, sftp_mysql = execute.connect(base_vals['database_fullname'], context=context)
                        execute.execute(ssh_mysql, ["mysql -u root -p'" + base_vals['database_root_password'] + "' -se \"create database " + database + ";\""], context)
                        execute.execute(ssh_mysql, ["mysql -u root -p'" + base_vals['database_root_password'] + "' -se \"grant all on " + database + ".* to '" + base_vals['service_db_user'] + "';\""], context)
                        ssh_mysql.close()
                        sftp_mysql.close()
                        execute.execute(ssh, ['mysql', '-h', base_vals['database_server'], '-u', base_vals['service_db_user'], '-p' + base_vals['service_db_password'], database, '<', '/base-backup/' + vals['saverepo_name'] + '/' +  database + '.dump'], context)

                self.restore_base(cr, uid, base_vals, context=context)

                base_obj.deploy_links(cr, uid, [base_id], context=context)

                execute.execute(ssh, ['rm', '-rf', '/base-backup/' + vals['saverepo_name']], context)
                ssh.close()
                sftp.close()

                self.end_log(cr, uid, save.id, context=context)
                res = base_id
            self.write(cr, uid, [save.id], {'container_restore_to_name': False, 'container_restore_to_server_id': False, 'base_restore_to_name': False, 'base_restore_to_domain_id': False}, context=context)

        return res

    def restore_action(self, cr, uid, vals, context={}):
        context.update({'clouder-self': self, 'clouder-cr': cr, 'clouder-uid': uid})
        #
        # context.update({'clouder-self': self, 'clouder-cr': cr, 'clouder-uid': uid})
        # ssh, sftp = execute.connect(vals['save_container_restore_to_server'], 22, 'root', context)
        # execute.execute(ssh, ['docker', 'run', '-t', '--rm', '--volumes-from', vals['save_container_restore_to_name'], '-v', '/opt/keys/bup:/root/.ssh', 'img_bup:latest', '/opt/restore', 'base', vals['saverepo_name'], vals['save_now_bup']], context)
        # ssh.close()
        # sftp.close()
        #

        directory = '/tmp/restore-' + vals['saverepo_name']
        ssh, sftp = execute.connect(vals['backup_fullname'], username='backup', context=context)
        execute.send(sftp, vals['config_home_directory'] + '/.ssh/config', '/home/backup/.ssh/config', context)
        execute.send(sftp, vals['config_home_directory'] + '/.ssh/keys/' + vals['container_fullname'] + '.pub', '/home/backup/.ssh/keys/' + vals['container_fullname'] + '.pub', context)
        execute.send(sftp, vals['config_home_directory'] + '/.ssh/keys/' + vals['container_fullname'], '/home/backup/.ssh/keys/' + vals['container_fullname'], context)
        execute.execute(ssh, ['chmod', '-R', '700', '/home/backup/.ssh'], context)
        execute.execute(ssh, ['rm', '-rf', directory + '*'], context)
        execute.execute(ssh, ['mkdir', '-p', directory], context)
        if vals['backup_method'] == 'simple':
            execute.execute(ssh, ['cp', '-R', '/opt/backup/simple/' + vals['saverepo_name'] + '/' + vals['save_name'] + '/*', directory], context)
        if vals['backup_method'] == 'bup':
            execute.execute(ssh, ['export BUP_DIR=/opt/backup/bup;', 'bup restore -C ' + directory + ' ' +  vals['saverepo_name'] + '/' + vals['save_now_bup']], context)
            execute.execute(ssh, ['mv', directory + '/' + vals['save_now_bup'] + '/*', directory], context)
            execute.execute(ssh, ['rm -rf', directory + '/' + vals['save_now_bup']], context)
        execute.execute(ssh, ['rsync', '-ra', directory + '/', vals['container_fullname'] + ':' + directory], context)
        execute.execute(ssh, ['rm', '-rf', directory + '*'], context)
        execute.execute(ssh, ['rm', '/home/backup/.ssh/keys/*'], context)
        ssh.close()
        sftp.close()


        ssh, sftp = execute.connect(vals['container_fullname'], context=context)

        if vals['saverepo_type'] == 'container':
            for volume in vals['save_container_volumes'].split(','):
                execute.execute(ssh, ['rm', '-rf', volume + '/*'], context)
        else:
            execute.execute(ssh, ['rm', '-rf', '/base-backup/' + vals['saverepo_name']], context)


        execute.execute(ssh, ['rm', '-rf', directory + '/backup-date'], context)
        if vals['saverepo_type'] == 'container':
            execute.execute(ssh, ['cp', '-R', directory + '/*', '/'], context)
        else:
            execute.execute(ssh, ['cp', '-R', directory, '/base-backup/' + vals['saverepo_name']], context)
            execute.execute(ssh, ['chmod', '-R', '777', '/base-backup/' + vals['saverepo_name']], context)
        execute.execute(ssh, ['rm', '-rf', directory + '*'], context)
        ssh.close()
        sftp.close()

    def deploy_base(self, cr, uid, vals, context=None):
        return

    def deploy(self, cr, uid, vals, context={}):
        context.update({'clouder-self': self, 'clouder-cr': cr, 'clouder-uid': uid})
        execute.log('Saving ' + vals['save_name'], context)
        execute.log('Comment: ' + vals['save_comment'], context)

        if vals['saverepo_type'] == 'base':
            base_vals = self.pool.get('clouder.base').get_vals(cr, uid, vals['save_base_id'], context=context)
            ssh, sftp = execute.connect(base_vals['container_fullname'], username=base_vals['apptype_system_user'], context=context)
            execute.execute(ssh, ['mkdir', '-p', '/base-backup/' + vals['saverepo_name']], context)
            for key, database in base_vals['base_databases'].iteritems():
                if vals['database_type'] != 'mysql':
                    execute.execute(ssh, ['pg_dump', '-O', '-h', base_vals['database_server'], '-U', base_vals['service_db_user'], database, '>', '/base-backup/' + vals['saverepo_name'] + '/' + database + '.dump'], context)
                else:
                    execute.execute(ssh, ['mysqldump', '-h', base_vals['database_server'], '-u', base_vals['service_db_user'], '-p' + base_vals['service_db_password'], database, '>', '/base-backup/' + vals['saverepo_name'] + '/' +  database + '.dump'], context)
            self.deploy_base(cr, uid, base_vals, context=context)
            execute.execute(ssh, ['chmod', '-R', '777', '/base-backup/' + vals['saverepo_name']], context)
            ssh.close()
            sftp.close()

        #
        # ssh, sftp = execute.connect(vals['save_container_restore_to_server'], 22, 'root', context)
        # execute.execute(ssh, ['docker', 'run', '-t', '--rm', '--volumes-from', vals['save_container_restore_to_name'], '-v', '/opt/keys/bup:/root/.ssh', 'img_bup:latest', '/opt/save', vals['saverepo_type'], vals['saverepo_name'], str(int(vals['save_now_epoch'])), vals['save_container_volumes'] or ''], context)
        # ssh.close()
        # sftp.close()

        directory = '/tmp/' + vals['saverepo_name']
        ssh, sftp = execute.connect(vals['container_fullname'], context=context)
        execute.execute(ssh, ['rm', '-rf', directory + '*'], context)
        execute.execute(ssh, ['mkdir', directory], context)
        if vals['saverepo_type'] == 'container':
            for volume in vals['save_container_volumes'].split(','):
                execute.execute(ssh, ['cp', '-R', '--parents', volume, directory], context)
        else:
            execute.execute(ssh, ['cp', '-R', '/base-backup/' + vals['saverepo_name'] + '/*', directory], context)

        execute.execute(ssh, ['echo "' + vals['now_date'] + '" > ' + directory + '/backup-date'], context)
        execute.execute(ssh, ['chmod', '-R', '777', directory + '*'], context)
        ssh.close()
        sftp.close()

        ssh, sftp = execute.connect(vals['backup_fullname'], username='backup', context=context)
        if vals['saverepo_type'] == 'container':
            name = vals['container_fullname']
        else:
            name = vals['base_unique_name_']
        execute.execute(ssh, ['rm', '-rf', '/opt/backup/list/' + name], context)
        execute.execute(ssh, ['mkdir', '-p', '/opt/backup/list/' + name], context)
        execute.execute(ssh, ['echo "' + vals['saverepo_name'] + '" > /opt/backup/list/' + name + '/repo'], context)


        execute.send(sftp, vals['config_home_directory'] + '/.ssh/config', '/home/backup/.ssh/config', context)
        execute.send(sftp, vals['config_home_directory'] + '/.ssh/keys/' + vals['container_fullname'] + '.pub', '/home/backup/.ssh/keys/' + vals['container_fullname'] + '.pub', context)
        execute.send(sftp, vals['config_home_directory'] + '/.ssh/keys/' + vals['container_fullname'], '/home/backup/.ssh/keys/' + vals['container_fullname'], context)
        execute.execute(ssh, ['chmod', '-R', '700', '/home/backup/.ssh'], context)

        execute.execute(ssh, ['rm', '-rf', directory], context)
        execute.execute(ssh, ['mkdir', directory], context)
        execute.execute(ssh, ['rsync', '-ra', vals['container_fullname'] + ':' + directory + '/', directory], context)

        if vals['backup_method'] == 'simple':
            execute.execute(ssh, ['mkdir', '-p', '/opt/backup/simple/' + vals['saverepo_name'] + '/' + vals['save_name']], context)
            execute.execute(ssh, ['cp', '-R', directory + '/*', '/opt/backup/simple/' + vals['saverepo_name'] + '/' + vals['save_name']], context)
            execute.execute(ssh, ['rm', '/opt/backup/simple/' + vals['saverepo_name'] + '/latest'], context)
            execute.execute(ssh, ['ln', '-s', '/opt/backup/simple/' + vals['saverepo_name'] + '/' + vals['save_name'], '/opt/backup/simple/' + vals['saverepo_name'] + '/latest'], context)
        if vals['backup_method'] == 'bup':
            execute.execute(ssh, ['export BUP_DIR=/opt/backup/bup;', 'bup index ' + directory], context)
            execute.execute(ssh, ['export BUP_DIR=/opt/backup/bup;', 'bup save -n ' + vals['saverepo_name'] + ' -d ' + str(int(vals['save_now_epoch'])) + ' --strip ' + directory], context)
        execute.execute(ssh, ['rm', '-rf', directory + '*'], context)
        execute.execute(ssh, ['rm', '/home/backup/.ssh/keys/*'], context)
        ssh.close()
        sftp.close()


        ssh, sftp = execute.connect(vals['container_fullname'], context=context)
        execute.execute(ssh, ['rm', '-rf', directory + '*'], context)
        ssh.close()
        sftp.close()

        if vals['saverepo_type'] == 'base':
            base_vals = self.pool.get('clouder.base').get_vals(cr, uid, vals['save_base_id'], context=context)
            ssh, sftp = execute.connect(base_vals['container_fullname'], username=base_vals['apptype_system_user'], context=context)
            execute.execute(ssh, ['rm', '-rf', '/base-backup/' + vals['saverepo_name']], context)
            ssh.close()
            sftp.close()


        return

