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


from openerp import netsvc
from openerp import pooler
from openerp.osv import fields, osv, orm
from openerp.tools.translate import _

import time
from datetime import datetime, timedelta
import subprocess
import paramiko
import execute
import ast

import logging
_logger = logging.getLogger(__name__)


class saas_save_repository(osv.osv):
    _name = 'saas.save.repository'

    _columns = {
        'name': fields.char('Name', size=128, required=True),
        'type': fields.selection([('container','Container'),('base','Base')], 'Name', required=True),
        'date_change': fields.date('Change Date'),
        'date_expiration': fields.date('Expiration Date'),
        'container_name': fields.char('Container Name', size=64),
        'container_server': fields.char('Container Server', size=128),
        'base_name': fields.char('Base Name', size=64),
        'base_domain': fields.char('Base Domain', size=128),
        'save_ids': fields.one2many('saas.save.save', 'repo_id', 'Saves'),
    }

    _order = 'create_date desc'

    def get_vals(self, cr, uid, id, context={}):

        vals = {}

        repo = self.browse(cr, uid, id, context=context)

        config = self.pool.get('ir.model.data').get_object(cr, uid, 'saas', 'saas_settings') 
        vals.update(self.pool.get('saas.config.settings').get_vals(cr, uid, context=context))

        vals.update({
            'saverepo_id': repo.id,
            'saverepo_name': repo.name,
            'saverepo_type': repo.type,
            'saverepo_date_change': repo.date_change,
            'saverepo_date_expiration': repo.date_expiration,
            'saverepo_container_name': repo.container_name,
            'saverepo_container_server': repo.container_server,
            'saverepo_base_name': repo.base_name,
            'saverepo_base_domain': repo.base_domain,
        })

        return vals

    def unlink(self, cr, uid, ids, context={}):
        for repo in self.browse(cr, uid, ids, context=context):
            vals = self.get_vals(cr, uid, repo.id, context=context)
            self.purge(cr, uid, vals, context=context)
        res = super(saas_save_repository, self).unlink(cr, uid, ids, context=context)
        # self.pool.get('saas.config.settings').save_fsck(cr, uid, [], context=context)

    def purge(self, cr, uid, vals, context={}):
        context.update({'saas-self': self, 'saas-cr': cr, 'saas-uid': uid})
        ssh, sftp = execute.connect(vals['backup_fullname'], context=context)
        execute.execute(ssh, ['rm', '-rf', '/opt/backup/simple/' + vals['saverepo_name']], context)
        execute.execute(ssh, ['git', '--git-dir=/opt/backup/bup', 'branch', '-D', vals['saverepo_name']], context)
        ssh.close()
        sftp.close()
        return

class saas_save_save(osv.osv):
    _name = 'saas.save.save'
    _inherit = ['saas.model']

    _columns = {
        'name': fields.char('Name', size=256, required=True),
        'type': fields.related('repo_id','type', type='char', size=64, string='Type', readonly=True),
        'backup_server_id': fields.many2one('saas.container', 'Backup Server', required=True),
        'repo_id': fields.many2one('saas.save.repository', 'Repository', ondelete='cascade', required=True),
        'date_expiration': fields.date('Expiration Date'),
        'comment': fields.text('Comment'),
        'now_bup': fields.char('Now bup', size=64),
        'container_id': fields.many2one('saas.container', 'Container'),
        'container_volumes_comma': fields.text('Container Volumes comma'),
        'container_app': fields.char('Application', size=64),
        'container_img': fields.char('Image', size=64),
        'container_img_version': fields.char('Image Version', size=64),
        'container_ports': fields.text('Ports'),
        'container_volumes': fields.text('Volumes'),
        'container_volumes_comma': fields.text('Volumes comma'),
        'container_options': fields.text('Container Options'),
        'container_links': fields.text('Container Links'),
        'service_id': fields.many2one('saas.service', 'Service'),
        'service_name': fields.char('Service Name', size=64),
        'service_database_id': fields.many2one('saas.container', 'Database Container'),
        'service_options': fields.text('Service Options'),
        'service_links': fields.text('Service Links'),
        'base_id': fields.many2one('saas.base', 'Base'),
        'base_title': fields.char('Title', size=64),
        'base_app_version': fields.char('Application Version', size=64),
        'base_proxy_id': fields.many2one('saas.container', 'Proxy Container'),
        'base_mail_id': fields.many2one('saas.container', 'Mail Container'),
        'base_container_name': fields.char('Container', size=64),
        'base_container_server': fields.char('Server', size=64),
        'base_admin_passwd': fields.char('Admin passwd', size=64),
        'base_poweruser_name': fields.char('Poweruser name', size=64),
        'base_poweruser_password': fields.char('Poweruser Password', size=64),
        'base_poweruser_email': fields.char('Poweruser email', size=64),
        'base_build': fields.char('Build', size=64),
        'base_test': fields.boolean('Test?'),
        'base_lang': fields.char('Lang', size=64),
        'base_nosave': fields.boolean('No save?'),
        'base_options': fields.text('Base Options'),
        'base_links': fields.text('Base Links'),

        'container_name': fields.related('repo_id', 'container_name', type='char', string='Container Name', size=64, readonly=True),
        'container_server': fields.related('repo_id', 'container_server', type='char', string='Container Server', size=64, readonly=True),
        'container_restore_to_name': fields.char('Restore to (Name)', size=64),
        'container_restore_to_server_id': fields.many2one('saas.server', 'Restore to (Server)'),
        'base_name': fields.related('repo_id', 'base_name', type='char', string='Base Name', size=64, readonly=True),
        'base_domain': fields.related('repo_id', 'base_domain', type='char', string='Base Domain', size=64, readonly=True),
        'base_restore_to_name': fields.char('Restore to (Name)', size=64),
        'base_restore_to_domain_id': fields.many2one('saas.domain', 'Restore to (Domain)'),
        'create_date': fields.datetime('Create Date'),
    }

    _order = 'create_date desc'

    def get_vals(self, cr, uid, id, context={}):
        vals = {}

        save = self.browse(cr, uid, id, context=context)

        if save.base_id:
            vals.update(self.pool.get('saas.base').get_vals(cr, uid, save.base_id.id, context=context))
        elif save.service_id:
            vals.update(self.pool.get('saas.service').get_vals(cr, uid, save.service_id.id, context=context))
        elif save.container_id:
            vals.update(self.pool.get('saas.container').get_vals(cr, uid, save.container_id.id, context=context))

        vals.update(self.pool.get('saas.save.repository').get_vals(cr, uid, save.repo_id.id, context=context))

        backup_server_vals = self.pool.get('saas.container').get_vals(cr, uid, save.backup_server_id.id, context=context)
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
            'save_id': save.id,
            'save_name': save.name,
            'saverepo_date_expiration': save.date_expiration,
            'save_comment': save.comment,
            'save_now_bup': save.now_bup,
            'save_now_epoch': (datetime.strptime(save.now_bup, "%Y-%m-%d-%H%M%S") - datetime(1970,1,1)).total_seconds(),
            'save_base_id': save.base_id.id,
            'save_container_volumes': save.container_volumes_comma,
            'save_container_restore_to_name': save.container_restore_to_name or save.base_container_name or vals['saverepo_container_name'],
            'save_container_restore_to_server': save.container_restore_to_server_id.name or save.base_container_server or vals['saverepo_container_server'],
            'save_base_restore_to_name': save.base_restore_to_name or vals['saverepo_base_name'],
            'save_base_restore_to_domain': save.base_restore_to_domain_id.name or vals['saverepo_base_domain'],
            'save_base_dumpfile': vals['saverepo_type'] == 'base' and save.container_app + '_' + save.base_name.replace('-','_') + '_' + save.base_domain.replace('-','_').replace('.','_') + '.dump'
        })
        return vals

    def unlink(self, cr, uid, ids, context={}):
        for save in self.browse(cr, uid, ids, context=context):
            vals = self.get_vals(cr, uid, save.id, context=context)
            self.purge(cr, uid, vals, context=context)
        return super(saas_save_save, self).unlink(cr, uid, ids, context=context)

    def purge(self, cr, uid, vals, context={}):
        context.update({'saas-self': self, 'saas-cr': cr, 'saas-uid': uid})
        ssh, sftp = execute.connect(vals['backup_fullname'], context=context)
        execute.execute(ssh, ['rm', '-rf', '/opt/backup/simple/' + vals['saverepo_name'] + '/'+ vals['save_name']], context)
        ssh.close()
        sftp.close()
        return

    def restore_base(self, cr, uid, vals, context=None):
        return

    def restore(self, cr, uid, ids, context={}):
        context.update({'saas-self': self, 'saas-cr': cr, 'saas-uid': uid})
        container_obj = self.pool.get('saas.container')
        base_obj = self.pool.get('saas.base')
        server_obj = self.pool.get('saas.server')
        domain_obj = self.pool.get('saas.domain')
        application_obj = self.pool.get('saas.application')
        application_version_obj = self.pool.get('saas.application.version')
        image_obj = self.pool.get('saas.image')
        image_version_obj = self.pool.get('saas.image.version')
        service_obj = self.pool.get('saas.service')
        for save in self.browse(cr, uid, ids, context=context):
            context = self.create_log(cr, uid, save.id, 'restore', context)
            vals = self.get_vals(cr, uid, save.id, context=context)

            app_ids = application_obj.search(cr, uid, [('code','=',save.container_app)], context=context)
            if not app_ids:
                raise osv.except_osv(_('Error!'),_("Couldn't find application " + save.container_app + ", aborting restoration."))
            img_ids = image_obj.search(cr, uid, [('name','=',save.container_img)], context=context)
            if not img_ids:
                raise osv.except_osv(_('Error!'),_("Couldn't find image " + save.container_img + ", aborting restoration."))
            img_version_ids = image_version_obj.search(cr, uid, [('name','=',save.container_img_version)], context=context)
            # upgrade = True
            if not img_version_ids:
                execute.log("Warning, couldn't find the image version, using latest", context)
                #We do not want to force the upgrade if we had to use latest
                # upgrade = False
                versions = image_obj.browse(cr, uid, img_ids[0], context=context).version_ids
                if not versions: 
                    raise osv.except_osv(_('Error!'),_("Couldn't find versions for image " + save.container_img + ", aborting restoration."))
                img_version_ids = [versions[0].id]

            if save.container_restore_to_name or not save.container_id:
                container_ids = container_obj.search(cr, uid, [('name','=',vals['save_container_restore_to_name']),('server_id.name','=',vals['save_container_restore_to_server'])], context=context)

                if not container_ids:
                    execute.log("Can't find any corresponding container, creating a new one", context)
                    server_ids = server_obj.search(cr, uid, [('name','=',vals['save_container_restore_to_server'])], context=context)
                    if not server_ids:
                        raise osv.except_osv(_('Error!'),_("Couldn't find server " + vals['save_container_restore_to_server'] + ", aborting restoration."))
 
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
                            link_app_ids = self.pool.get('saas.application').search(cr, uid, [('code','=',link_vals['name_name'])], context=context)
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
                context.update({'saas-self': self, 'saas-cr': cr, 'saas-uid': uid})
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
                        raise osv.except_osv(_('Error!'),_("Couldn't find versions for application " + save.container_app + ", aborting restoration."))
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
                                link_app_ids = self.pool.get('saas.application').search(cr, uid, [('code','=',link_vals['name_name'])], context=context)
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
                            raise osv.except_osv(_('Error!'),_("Couldn't find domain " + vals['save_base_restore_to_domain'] + ", aborting restoration."))
                        options = []
                        for option, option_vals in ast.literal_eval(save.base_options).iteritems():
                            del option_vals['id']
                            options.append((0,0,option_vals))
                        links = []
                        for link, link_vals in ast.literal_eval(save.base_links).iteritems():
                            if not link_vals['name']:
                                link_app_ids = self.pool.get('saas.application').search(cr, uid, [('code','=',link_vals['name_name'])], context=context)
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
        context.update({'saas-self': self, 'saas-cr': cr, 'saas-uid': uid})
        #
        # context.update({'saas-self': self, 'saas-cr': cr, 'saas-uid': uid})
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
        context.update({'saas-self': self, 'saas-cr': cr, 'saas-uid': uid})
        execute.log('Saving ' + vals['save_name'], context)
        execute.log('Comment: ' + vals['save_comment'], context)

        if vals['saverepo_type'] == 'base':
            base_vals = self.pool.get('saas.base').get_vals(cr, uid, vals['save_base_id'], context=context)
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
            base_vals = self.pool.get('saas.base').get_vals(cr, uid, vals['save_base_id'], context=context)
            ssh, sftp = execute.connect(base_vals['container_fullname'], username=base_vals['apptype_system_user'], context=context)
            execute.execute(ssh, ['rm', '-rf', '/base-backup/' + vals['saverepo_name']], context)
            ssh.close()
            sftp.close()


        return

