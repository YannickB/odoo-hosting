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
        })

        return vals

    def unlink(self, cr, uid, ids, context={}):
        for repo in self.browse(cr, uid, ids, context=context):
            vals = self.get_vals(cr, uid, repo.id, context=context)
            self.purge(cr, uid, vals, context=context)
        return super(saas_save_repository, self).unlink(cr, uid, ids, context=context)

    def purge(self, cr, uid, vals, context={}):
        context.update({'saas-self': self, 'saas-cr': cr, 'saas-uid': uid})
        ssh, sftp = execute.connect(vals['bup_fullname'], context=context)
        execute.execute(ssh, ['git', '--git-dir=/home/bup/.bup', 'branch', '-D', vals['saverepo_name']], context)
        ssh.close()
        sftp.close()


        return

class saas_save_save(osv.osv):
    _name = 'saas.save.save'
    _inherit = ['saas.log.model']

    _columns = {
        'name': fields.char('Name', size=64, required=True),
        'type': fields.related('repo_id','type', type='char', size=64, string='Type', readonly=True),
        'repo_id': fields.many2one('saas.save.repository', 'Repository', ondelete='cascade', required=True),
        'comment': fields.text('Comment'),
        'now_bup': fields.char('Now bup', size=64),
        'container_id': fields.many2one('saas.container', 'Container'),
        'container_volumes_comma': fields.text('Container Volumes comma'),
        'container_app': fields.char('Container Application', size=64),
        'container_img': fields.char('Container Image', size=64),
        'container_img_version': fields.char('Container Image Version', size=64),
        'container_ports': fields.text('Container Ports'),
        'container_volumes': fields.text('Container Volumes'),
        'container_volumes_comma': fields.text('Container Volumes comma'),
        'container_options': fields.text('Container Options'),
        'container_name': fields.related('repo_id', 'container_name', type='char', string='Container Name', size=64, readonly=True),
        'container_server': fields.related('repo_id', 'container_server', type='char', string='Container Server', size=64, readonly=True),
        'container_restore_to_name': fields.char('Restore to (Name)', size=64),
        'container_restore_to_server_id': fields.many2one('saas.server', 'Restore to (Server)'),
#        'saas_ids': fields.many2many('saas.saas', 'saas_saas_save_rel', 'save_id', 'saas_id', 'SaaS', readonly=True),
#        'instance_id': fields.many2one('saas.service', 'Instance'),
#        'application_id': fields.related('instance_id','application_id', type='many2one', relation='saas.application', string='Application'),
        'create_date': fields.datetime('Create Date'),
#        'version': fields.char('Version', size=64),
#        'restore_instance_id': fields.many2one('saas.service', 'Target instance for restore'),
#        'restore_saas_ids': fields.many2many('saas.saas', 'saas_saas_save_restore_rel', 'save_id', 'saas_id', 'SaaS to restore'),
#        'restore_prefix': fields.char('Restore prefix (optional)', size=64),
    }

    _order = 'create_date desc'

    def get_vals(self, cr, uid, id, context={}):
        vals = {}

        save = self.browse(cr, uid, id, context=context)

        vals.update(self.pool.get('saas.save.repository').get_vals(cr, uid, save.repo_id.id, context=context))

        vals.update({
            'save_id': save.id,
            'save_name': save.name,
            'save_now_bup': save.now_bup,
            'save_now_epoch': (datetime.strptime(save.now_bup, "%Y-%m-%d-%H%M%S") - datetime(1970,1,1)).total_seconds(),
            'save_container_volumes': save.container_volumes_comma,
            'save_container_restore_to_name': save.container_restore_to_name or vals['saverepo_container_name'],
            'save_container_restore_to_server': save.container_restore_to_server_id.name or vals['saverepo_container_server'],
        })
        return vals

    def create(self, cr, uid, vals, context={}):
        res = super(saas_save_save, self).create(cr, uid, vals, context=context)
        context = self.create_log(cr, uid, res, 'create', context)
        vals = self.get_vals(cr, uid, res, context=context)
        self.deploy(cr, uid, vals, context=context)
        self.end_log(cr, uid, res, context=context)
        return res

    def restore(self, cr, uid, ids, context={}):
        container_obj = self.pool.get('saas.container')
        server_obj = self.pool.get('saas.server')
        application_obj = self.pool.get('saas.application')
        image_obj = self.pool.get('saas.image')
        image_version_obj = self.pool.get('saas.image.version')
        for save in self.browse(cr, uid, ids, context=context):
            context = self.create_log(cr, uid, save.id, 'restore', context)
            vals = self.get_vals(cr, uid, save.id, context=context)

            img_ids = image_obj.search(cr, uid, [('name','=',save.container_img)], context=context)
            if not img_ids:
                raise osv.except_osv(_('Error!'),_("Couldn't find image " + save.container_img + ", aborting restoration."))
            img_version_ids = image_version_obj.search(cr, uid, [('name','=',save.container_img_version)], context=context)
            upgrade = True
            if not img_version_ids:
                execute.log("Warning, couldn't find the image version, using latest", context)
                #We do not want to force the upgrade if we had to use latest
                upgrade = False
                versions = image_obj.browse(cr, uid, img_ids[0], context=context).version_ids
                if not versions: 
                    raise osv.except_osv(_('Error!'),_("Couldn't find versions for image " + save.container_img + ", aborting restoration."))
                img_version_ids = [versions[0].id]

            if save.container_restore_to_name or not save.container_id:
                container_ids = container_obj.search(cr, uid, [('name','=',vals['save_container_restore_to_name']),('server_id.name','=',vals['save_container_restore_to_server'])], context=context)

                if not container_ids:
                    server_ids = server_obj.search(cr, uid, [('name','=',vals['save_container_restore_to_server'])], context=context)
                    if not server_ids:
                        raise osv.except_osv(_('Error!'),_("Couldn't find server " + vals['save_container_restore_to_server'] + ", aborting restoration."))
                    app_ids = application_obj.search(cr, uid, [('code','=',save.container_app)], context=context)
                    if not app_ids:
                        raise osv.except_osv(_('Error!'),_("Couldn't find application " + save.container_app + ", aborting restoration."))
 
                    ports = []
                    for port, port_vals in ast.literal_eval(save.container_ports).iteritems():
                        del port_vals['id']
                        ports.append((0,0,port_vals))
                    volumes = []
                    for volume, volume_vals in ast.literal_eval(save.container_volumes).iteritems():
                        del volume_vals['id']
                        volumes.append((0,0,volume_vals))
                    options = []
                    for option, option_vals in ast.literal_eval(save.container_options).iteritems():
                        del option_vals['id']
                        options.append((0,0,option_vals))
                    container_vals = {
                        'name': vals['save_container_restore_to_name'],
                        'server_id': server_ids[0],
                        'application_id': app_ids[0],
                        'image_id': img_ids[0],
                        'image_version_id': img_version_ids[0],
                        'port_ids': ports,
                        'volume_ids': volumes,
                        'option_ids': options,
                    }
                    container_id = container_obj.create(cr, uid, container_vals, context=context)

                else:
                    container_id = container_ids[0]
            else:
                container_id = save.container_id.id

            if upgrade:
                container_obj.write(cr, uid, [container_id], {'image_version_ids': img_version_ids[0]}, context=context)

            context['container_save_comment'] = 'Before restore ' + save.name
            container_obj.save(cr, uid, [container_id], context=context)

            vals = self.get_vals(cr, uid, save.id, context=context)
            vals_container = container_obj.get_vals(cr, uid, container_id, context=context)
            container_obj.stop(cr, uid, vals_container, context)
            context.update({'saas-self': self, 'saas-cr': cr, 'saas-uid': uid})
            ssh, sftp = execute.connect(vals['saverepo_container_server'], 22, 'root', context)
            execute.execute(ssh, ['docker', 'run', '-t', '--rm', '--volumes-from', vals['saverepo_container_name'], '-v', '/opt/keys/bup:/root/.ssh', 'img_bup:latest', '/opt/restore', vals['saverepo_name'], vals['save_now_bup'], vals['save_container_volumes']], context)
            ssh.close()
            sftp.close()
            container_obj.start(cr, uid, vals_container, context)
            self.write(cr, uid, [save.id], {'container_restore_to_name': False, 'container_restore_to_server_id': False}, context=context)
            self.end_log(cr, uid, save.id, context=context)
        return True

    def deploy(self, cr, uid, vals, context={}):
        context.update({'saas-self': self, 'saas-cr': cr, 'saas-uid': uid})
        ssh, sftp = execute.connect(vals['saverepo_container_server'], 22, 'root', context)
        execute.execute(ssh, ['docker', 'run', '-t', '--rm', '--volumes-from', vals['saverepo_container_name'], '-v', '/opt/keys/bup:/root/.ssh', 'img_bup:latest', '/opt/save', vals['saverepo_name'], str(int(vals['save_now_epoch'])), vals['save_container_volumes']], context)
        ssh.close()
        sftp.close()


        return

