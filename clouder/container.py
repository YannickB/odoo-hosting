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
from openerp import modules

import time
from datetime import datetime, timedelta
import execute

import logging
_logger = logging.getLogger(__name__)

class ClouderServer(models.Model):
    _name = 'clouder.server'
    _inherit = ['clouder.model']

    name = fields.Char('Domain name', size=64, required=True)
    ip = fields.Char('IP', size=64, required=True)
    ssh_port = fields.Char('SSH port', size=12, required=True)
    mysql_passwd = fields.Char('MySQL Passwd', size=64)
    private_key = fields.Text('SSH Private Key', required=True)
    public_key = fields.Text('SSH Public Key', required=True)
    start_port = fields.Integer('Start Port', required=True)
    end_port = fields.Integer('End Port', required=True)

    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'Name must be unique!'),
    ]

    @api.multi
    def get_vals(self):

        vals ={}

        vals.update(self.env.ref('clouder.clouder_settings').get_vals())

        vals.update({
            'server_id': self.id,
            'server_domain': self.name,
            'server_ip': self.ip,
            'server_ssh_port': int(self.ssh_port),
            'server_mysql_passwd': self.mysql_passwd,
            'server_shinken_configfile': '/usr/local/shinken/etc/hosts/' + self.name + '.cfg',
            'server_private_key': self.private_key,
            'server_public_key': self.public_key,
            'server_start_port': self.start_port,
            'server_end_port': self.end_port,
        })
        return vals

    def _create_key(self, cr, uid, context=None):
        vals = self.pool.get('clouder.config.settings').get_vals(cr, int(uid), context=context)
        execute.execute_local(['mkdir', '/tmp/key_' + uid], context)
        execute.execute_local(['ssh-keygen', '-t', 'rsa', '-C', vals['config_email_sysadmin'], '-f', '/tmp/key_' + uid + '/key', '-N', ''], context)
        return True

    def _destroy_key(self, cr, uid, context=None):
        execute.execute_local(['rm', '-rf', '/tmp/key_' + uid], context)
        return True

    def _default_private_key(self, cr, uid, context=None):
        context = {'clouder-self': self, 'clouder-cr': cr, 'clouder-uid': uid}
        uid = str(uid)

        destroy = True
        if not execute.local_dir_exist('/tmp/key_' + uid):
            self._create_key(cr, uid, context=context)
            destroy = False

        key = execute.execute_local(['cat', '/tmp/key_' + uid + '/key'], context)

        if destroy:
            self._destroy_key(cr, uid, context=context)
        return key

    def _default_public_key(self, cr, uid, context=None):
        context = {'clouder-self': self, 'clouder-cr': cr, 'clouder-uid': uid}
        uid = str(uid)

        destroy = True
        if not execute.local_dir_exist('/tmp/key_' + uid):
            self._create_key(cr, uid, context=context)
            destroy = False

        key = execute.execute_local(['cat', '/tmp/key_' + uid + '/key.pub'], context)

        if destroy:
            self._destroy_key(cr, uid, context=context)
        return key


    _defaults = {
      'private_key': _default_private_key,
      'public_key': _default_public_key,
    }


    def start_containers(self, cr, uid, ids, context={}):
        container_obj = self.pool.get('clouder.container')
        for server in self.browse(cr, uid, ids, context=context):
            container_ids = container_obj.search(cr, uid, [('server_id', '=', server.id)], context=context)
            for container in container_obj.browse(cr, uid, container_ids, context=context):
                vals = container_obj.get_vals(cr, uid, container.id, context=context)
                container_obj.start(cr, uid, vals, context=context)

    def stop_containers(self, cr, uid, ids, context={}):
        container_obj = self.pool.get('clouder.container')
        for server in self.browse(cr, uid, ids, context=context):
            container_ids = container_obj.search(cr, uid, [('server_id', '=', server.id)], context=context)
            for container in container_obj.browse(cr, uid, container_ids, context=context):
                vals = container_obj.get_vals(cr, uid, container.id, context=context)
                container_obj.stop(cr, uid, vals, context=context)

    def deploy(self, cr, uid, vals, context={}):
        context.update({'clouder-self': self, 'clouder-cr': cr, 'clouder-uid': uid})
        self.purge(cr, uid, vals, context=context)
        key_file = vals['config_home_directory'] + '/.ssh/keys/' + vals['server_domain']
        execute.execute_write_file(key_file, vals['server_private_key'], context)
        execute.execute_local(['chmod', '700', key_file], context)
        execute.execute_write_file(vals['config_home_directory'] + '/.ssh/config', 'Host ' + vals['server_domain'], context)
        execute.execute_write_file(vals['config_home_directory'] + '/.ssh/config', '\n  HostName ' + vals['server_domain'], context)
        execute.execute_write_file(vals['config_home_directory'] + '/.ssh/config', '\n  Port ' + str(vals['server_ssh_port']), context)
        execute.execute_write_file(vals['config_home_directory'] + '/.ssh/config', '\n  User root', context)
        execute.execute_write_file(vals['config_home_directory'] + '/.ssh/config', '\n  IdentityFile ' + vals['config_home_directory'] + '/.ssh/keys/' + vals['server_domain'], context)
        execute.execute_write_file(vals['config_home_directory'] + '/.ssh/config', '\n#END ' + vals['server_domain'] + '\n', context)

#        _logger.info('test %s', vals['shinken_server_domain'])
#        if 'shinken_server_domain' in vals:
#            ssh, sftp = execute.connect(vals['shinken_fullname'], context=context)
#            sftp.put(modules.get_module_path('clouder_shinken') + '/res/server-shinken.config', vals['server_shinken_configfile'])
#            execute.execute(ssh, ['sed', '-i', '"s/NAME/' + vals['server_domain'] + '/g"', vals['server_shinken_configfile']], context)
#            execute.execute(ssh, ['/etc/init.d/shinken', 'reload'], context)
#            ssh.close()
#            sftp.close()

    def purge(self, cr, uid, vals, context={}):
        context.update({'clouder-self': self, 'clouder-cr': cr, 'clouder-uid': uid})

        execute.execute_local([modules.get_module_path('clouder') + '/res/sed.sh', vals['server_domain'], vals['config_home_directory'] + '/.ssh/config'], context)
        execute.execute_local(['rm', '-rf', vals['config_home_directory'] + '/.ssh/keys/' + vals['server_domain']], context)

#        if 'shinken_server_domain' in vals:
#            ssh, sftp = execute.connect(vals['shinken_fullname'], context=context)
#            execute.execute(ssh, ['rm', vals['server_shinken_configfile']], context)
#            execute.execute(ssh, ['/etc/init.d/shinken', 'reload'], context)
#            ssh.close()
#            sftp.close()

class ClouderContainer(models.Model):
    _name = 'clouder.container'
    _inherit = ['clouder.model']

    def _get_ports(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for container in self.browse(cr, uid, ids, context=context):
            res[container.id] = ''
            first = True
            for port in container.port_ids:
                if not first:
                    res[container.id] += ', '
                if port.hostport:
                    res[container.id] += port.name + ' : ' + port.hostport
                first = False
        return res

    name = fields.Char('Name', size=64, required=True)
    application_id = fields.Many2one('clouder.application', 'Application', required=True)
    image_id = fields.Many2one('clouder.image', 'Image', required=True)
    server_id = fields.Many2one('clouder.server', 'Server', required=True)
    image_version_id = fields.Many2one('clouder.image.version', 'Image version', required=True)
    save_repository_id = fields.Many2one('clouder.save.repository', 'Save repository')
    time_between_save = fields.Integer('Minutes between each save')
    saverepo_change = fields.Integer('Days before saverepo change')
    saverepo_expiration = fields.Integer('Days before saverepo expiration')
    save_expiration = fields.Integer('Days before save expiration')
    date_next_save = fields.Datetime('Next save planned')
    save_comment = fields.Text('Save Comment')
    nosave = fields.Boolean('No Save?')
    privileged = fields.Boolean('Privileged?')
    port_ids = fields.One2many('clouder.container.port', 'container_id', 'Ports')
    volume_ids = fields.One2many('clouder.container.volume', 'container_id', 'Volumes')
    option_ids = fields.One2many('clouder.container.option', 'container_id', 'Options')
    link_ids = fields.One2many('clouder.container.link', 'container_id', 'Links')
    service_ids = fields.One2many('clouder.service', 'container_id', 'Services')
    ports = fields.Text('Ports', compute='_get_ports')
    backup_server_ids = fields.Many2many('clouder.container', 'clouder_container_backup_rel', 'container_id', 'backup_id', 'Backup containers')

    _sql_constraints = [
        ('name_uniq', 'unique(server_id,name)', 'Name must be unique per server!'),
    ]

    def _check_backup(self, cr, uid, ids, context=None):
        for c in self.browse(cr, uid, ids, context=context):
            if not c.backup_server_ids and c.application_id.type_id.name not in ['backup','backup_upload','archive','registry']:
                return False
        return True

    def _check_image(self, cr, uid, ids, context=None):
        for c in self.browse(cr, uid, ids, context=context):
            if c.image_id.id != c.image_version_id.image_id.id:
                return False
        return True

    _constraints = [
        (_check_backup, "You need to specify at least one backup container." , ['application_id']),
        (_check_image, "The image of image version must be the same than the image of container." , ['image_id','image_version_id']),
    ]

    def onchange_application_id(self, cr, uid, ids, application_id=False, context=None):
        result = {}
        if application_id:
            application = self.pool.get('clouder.application').browse(cr, uid, application_id, context=context)
            result = {'value': {
                    'server_id': application.next_server_id.id,
                    'image_id': application.default_image_id.id,
                    'privileged': application.default_image_id.privileged,
                    'image_version_id': application.default_image_id.version_ids and application.default_image_id.version_ids[0].id,
                    }
                }
        return result

    @api.multi
    def get_vals(self):
        repo_obj = self.env['clouder.save.repository']
        vals = {}

        now = datetime.now()
        if not self.save_repository_id:
            repo_ids = repo_obj.search([('container_name','=',self.name),('container_server','=',self.server_id.name)])
            if repo_ids:
                self.write({'save_repository_id': repo_ids[0]})

        if not self.save_repository_id or datetime.strptime(self.save_repository_id.date_change, "%Y-%m-%d") < now or False:
            repo_vals ={
                'name': now.strftime("%Y-%m-%d") + '_' + self.name + '_' + self.server_id.name,
                'type': 'container',
                'date_change': (now + timedelta(days=self.saverepo_change or self.application_id.container_saverepo_change)).strftime("%Y-%m-%d"),
                'date_expiration': (now + timedelta(days=self.saverepo_expiration or self.application_id.container_saverepo_expiration)).strftime("%Y-%m-%d"),
                'container_name': self.name,
                'container_server': self.server_id.name,
            }
            repo_id = repo_obj.create(repo_vals)
            self.write({'save_repository_id': repo_id})

        vals.update(self.image_version_id.get_vals())
        vals.update(self.application_id.get_vals())
        vals.update(self.save_repository_id.id.get_vals())
        vals.update(self.server_id.get_vals())


        # links = {}
        # for link in  container.linked_container_ids:
        #     links[link.id] = {'id': link.id, 'apptype': link.application_id.type_id.name, 'name': link.name}

        ports = {}
        ssh_port = 22
        for port in self.port_ids:
            ports[port.name] = {'id': port.id, 'name': port.name, 'localport': port.localport, 'hostport': port.hostport, 'expose': port.expose, 'udp': port.udp}
            if port.name == 'ssh':
                ssh_port = port.hostport

        volumes = {}
        volumes_save = ''
        first = True
        for volume in self.volume_ids:
            volumes[volume.id] = {'id': volume.id, 'name': volume.name, 'hostpath': volume.hostpath, 'user': volume.user,'readonly': volume.readonly,'nosave': volume.nosave}
            if not volume.nosave:
                volumes_save += (not first and ',' or '') + volume.name
                first = False

        options = {}
        for option in self.application_id.type_id.option_ids:
            if option.type == 'container':
                options[option.name] = {'id': option.id, 'name': option.name, 'value': option.default}
        for option in self.option_ids:
            options[option.name.name] = {'id': option.id, 'name': option.name.name, 'value': option.value}

        links = {}
        if 'app_links' in vals:
            for app_code, link in vals['app_links'].iteritems():
                if link['container'] or link['make_link']:
                    links[app_code] = link
                    links[app_code]['target'] = False
        for link in self.link_ids:
            if link.name.code in links and link.target:
                link_vals = link.get_vals()
                links[link.name.code]['target'] = {
                    'link_id': link_vals['container_id'],
                    'link_name': link_vals['container_name'],
                    'link_fullname': link_vals['container_fullname'],
                    'link_ssh_port': link_vals['container_ssh_port'],
                    'link_server_id': link_vals['server_id'],
                    'link_server_domain': link_vals['server_domain'],
                    'link_server_ip': link_vals['server_ip'],
                }
        for app_code, link in links.iteritems():
            if link['required'] and not link['target']:
                raise except_orm(_('Data error!'),
                    _("You need to specify a link to " + link['name'] + " for the container " + container.name))
            if not link['target']:
                del links[app_code]

        backup_servers = []
        for backup in self.backup_server_ids:
            backup_vals = backup.get_vals()
            backup_servers.append({
                'container_id': backup_vals['container_id'],
                'container_fullname': backup_vals['container_fullname'],
                'server_id': backup_vals['server_id'],
                'server_ssh_port': backup_vals['server_ssh_port'],
                'server_domain': backup_vals['server_domain'],
                'server_ip': backup_vals['server_ip'],
                'backup_method': backup_vals['app_options']['backup_method']['value']
            })


        root_password = False
        for key, option in options.iteritems():
            if option['name'] == 'root_password':
                root_password = option['value']

        unique_name = self.name + '_' + vals['server_domain']
        vals.update({
            'container_id': self.id,
            'container_name': self.name,
            'container_fullname': unique_name,
            'container_ports': ports,
            'container_volumes': volumes,
            'container_volumes_save': volumes_save,
            'container_ssh_port': ssh_port,
            'container_options': options,
            'container_links': links,
            'container_backup_servers': backup_servers,
            'container_no_save': self.nosave,
            'container_privileged': self.privileged,
            'container_shinken_configfile': '/usr/local/shinken/etc/services/' + unique_name + '.cfg',
            'container_root_password': root_password
        })

        return vals

    def create_vals(self, cr, uid, vals, context={}):
        return vals

    def create(self, cr, uid, vals, context={}):
        if ('port_ids' not in vals or not vals['port_ids']) and 'image_version_id' in vals:
            vals['port_ids'] = []
            for port in self.pool.get('clouder.image.version').browse(cr, uid, vals['image_version_id'], context=context).image_id.port_ids:
                if port.expose != 'none':
                    vals['port_ids'].append((0,0,{'name':port.name,'localport':port.localport,'expose':port.expose,'udp':port.udp}))
        if ('volume_ids' not in vals or not vals['volume_ids']) and 'image_version_id' in vals:
            vals['volume_ids'] = []
            for volume in self.pool.get('clouder.image.version').browse(cr, uid, vals['image_version_id'], context=context).image_id.volume_ids:
                vals['volume_ids'].append((0,0,{'name':volume.name,'hostpath':volume.hostpath,'user':volume.user,'readonly':volume.readonly,'nosave':volume.nosave}))
        if 'application_id' in vals:
            application = self.pool.get('clouder.application').browse(cr, uid, vals['application_id'], context=context)
            context['apptype_name'] = application.type_id.name

            if 'backup_server_ids' not in vals or not vals['backup_server_ids'] or not vals['backup_server_ids'][0][2]:
                vals['backup_server_ids'] = [(6,0,[b.id for b in application.container_backup_ids])]
            if 'time_between_save' not in vals or not vals['time_between_save']:
                vals['time_between_save'] = application.container_time_between_save
            if 'saverepo_change' not in vals or not vals['saverepo_change']:
                vals['saverepo_change'] = application.container_saverepo_change
            if 'saverepo_expiration' not in vals or not vals['saverepo_expiration']:
                vals['saverepo_expiration'] = application.container_saverepo_expiration
            if 'save_expiration' not in vals or not vals['save_expiration']:
                vals['save_expiration'] = application.container_save_expiration

            links = {}
            for link in  application.link_ids:
                if link.container or link.make_link:
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
                        _("You need to specify a link to " + link['name'] + " for the container " + vals['name']))
                vals['link_ids'].append((0,0,{'name': application_id, 'target': link['target']}))
        vals = self.create_vals(cr, uid, vals, context=context)
        return super(ClouderContainer, self).create(cr, uid, vals, context=context)

    def write(self, cr, uid, ids, vals, context={}):
        version_obj = self.pool.get('clouder.image.version')
        save_obj = self.pool.get('clouder.save.save')
        flag = False
        if 'image_version_id' in vals or 'port_ids' in vals or 'volume_ids' in vals:
            flag = True
            for container in self.browse(cr, uid, ids, context=context):
                context = self.create_log(cr, uid, container.id, 'upgrade version', context)
                if 'image_version_id' in vals:
                    new_version = version_obj.browse(cr, uid, vals['image_version_id'], context=context)
                    context['save_comment'] = 'Before upgrade from ' + container.image_version_id.name + ' to ' + new_version.name
                else:
                    context['save_comment'] = 'Change on port or volumes'
        res = super(ClouderContainer, self).write(cr, uid, ids, vals, context=context)
        if flag:
            for container in self.browse(cr, uid, ids, context=context):
                self.reinstall(cr, uid, [container.id], context=context)
                self.end_log(cr, uid, container.id, context=context)
        if 'nosave' in vals:
            self.deploy_links(cr, uid, ids, context=context)
        return res

    def unlink(self, cr, uid, ids, context={}):
        service_obj = self.pool.get('clouder.service')
        for container in self.browse(cr, uid, ids, context=context):
            service_obj.unlink(cr, uid, [s.id for s in container.service_ids], context=context)
        context['save_comment'] = 'Before unlink'
        self.save(cr, uid, ids, context=context)
        return super(ClouderContainer, self).unlink(cr, uid, ids, context=context)

    def button_stop(self, cr, uid, ids, context={}):
        for container in self.browse(cr, uid, ids, context=context):
            vals = self.get_vals(cr, uid, container.id, context=context)
            self.stop(cr, uid, vals, context=context)

    def button_start(self, cr, uid, ids, context={}):
        for container in self.browse(cr, uid, ids, context=context):
            vals = self.get_vals(cr, uid, container.id, context=context)
            self.start(cr, uid, vals, context=context)

    def reinstall(self, cr, uid, ids, context={}):
        save_obj = self.pool.get('clouder.save.save')
        for container in self.browse(cr, uid, ids, context=context):
            if not 'save_comment' in context:
                context['save_comment'] = 'Before reinstall'
            context['forcesave'] = True
            save_id = self.save(cr, uid, [container.id], context=context)[container.id]
            del context['forcesave']
            context['nosave'] = True
            super(ClouderContainer, self).reinstall(cr, uid, [container.id], context=context)



    def save(self, cr, uid, ids, context={}):
        context.update({'clouder-self': self, 'clouder-cr': cr, 'clouder-uid': uid})
        save_obj = self.pool.get('clouder.save.save')
        res = {}
        now = datetime.now()
        for container in self.browse(cr, uid, ids, context=context):
            if 'nosave' in context or (container.nosave and not 'forcesave' in context):
                execute.log('This base container not be saved or the backup isnt configured in conf, skipping save container', context)
                continue
            context = self.create_log(cr, uid, container.id, 'save', context)
            vals = self.get_vals(cr, uid, container.id, context=context)
            for backup_server in vals['container_backup_servers']:
                links = {}
                for app_code, link in vals['container_links'].iteritems():
                    links[app_code] = {
                        'name': link['app_id'],
                        'name_name': link['name'],
                        'target': link['target'] and link['target']['link_id'] or False
                    }
                save_vals = {
                    'name': vals['now_bup'] + '_' + vals['container_fullname'],
                    'backup_server_id': backup_server['container_id'],
                    'repo_id': vals['saverepo_id'],
                    'date_expiration': (now + timedelta(days=container.save_expiration or container.application_id.container_save_expiration)).strftime("%Y-%m-%d"),
                    'comment': 'save_comment' in context and context['save_comment'] or container.save_comment or 'Manual',
                    'now_bup': vals['now_bup'],
                    'container_id': vals['container_id'],
                    'container_volumes_comma': vals['container_volumes_save'],
                    'container_app': vals['app_code'],
                    'container_img': vals['image_name'],
                    'container_img_version': vals['image_version_name'],
                    'container_ports': str(vals['container_ports']),
                    'container_volumes': str(vals['container_volumes']),
                    'container_options': str(vals['container_options']),
                    'container_links': str(links),
                }
                res[container.id] = save_obj.create(cr, uid, save_vals, context=context)
            next = (datetime.now() + timedelta(minutes=container.time_between_save or container.application_id.container_time_between_save)).strftime("%Y-%m-%d %H:%M:%S")
            self.write(cr, uid, [container.id], {'save_comment': False, 'date_next_save': next}, context=context)
            self.end_log(cr, uid, container.id, context=context)
        return res


    def reset_key(self, cr, uid, ids, context={}):
        for container in self.browse(cr, uid, ids, context=context):
            vals = self.get_vals(cr, uid, container.id, context=context)
            self.deploy_key(cr, uid, vals, context=context)


    def deploy_post(self, cr, uid, vals, context=None):
        return

    def deploy(self, cr, uid, vals, context={}):
        context.update({'clouder-self': self, 'clouder-cr': cr, 'clouder-uid': uid})
        self.purge(cr, uid, vals, context=context)

        ssh, sftp = execute.connect(vals['server_domain'], vals['server_ssh_port'], 'root', context)

        cmd = ['sudo','docker', 'run', '-d']
        nextport = vals['server_start_port']
        for key, port in vals['container_ports'].iteritems():
            if not port['hostport']:
                while not port['hostport'] and nextport != vals['server_end_port']:
                    port_ids = self.pool.get('clouder.container.port').search(cr, uid, [('hostport','=',nextport),('container_id.server_id','=',vals['server_id'])], context=context)
                    if not port_ids and not execute.execute(ssh, ['netstat', '-an', '|', 'grep', str(nextport)], context):
                        self.pool.get('clouder.container.port').write(cr, uid, [port['id']], {'hostport': nextport}, context=context)
                        port['hostport'] = nextport
                        if port['name'] == 'ssh':
                            vals['container_ssh_port'] = nextport
                    nextport += 1
                    _logger.info('nextport %s', nextport)
            udp = ''
            if port['udp']:
                udp = '/udp'
            # cmd.extend(['-p', vals['server_ip'] + ':' + str(port['hostport']) + ':' + port['localport'] + udp])
            cmd.extend(['-p', str(port['hostport']) + ':' + port['localport'] + udp])
        for key, volume in vals['container_volumes'].iteritems():
            if volume['hostpath']:
                arg =  volume['hostpath'] + ':' + volume['name']
                if volume['readonly']:
                    arg += ':ro'
                cmd.extend(['-v', arg])
        for key, link in vals['container_links'].iteritems():
            if link['make_link'] and link['target']['link_server_id'] == vals['server_id']:
                cmd.extend(['--link', link['target']['link_name'] + ':' + link['code']])
        if vals['container_privileged']:
            cmd.extend(['--privileged'])
        cmd.extend(['-v', '/opt/keys/' + vals['container_fullname'] + ':/opt/keys', '--name', vals['container_name']])

        if vals['image_name'] == 'img_registry':
            cmd.extend([vals['image_version_fullname']])
        elif vals['server_id'] == vals['registry_server_id']:
            cmd.extend([vals['image_version_fullpath_localhost']])
        else:
            cmd.extend([vals['image_version_fullpath']])

        #Deploy key now, otherwise the container will be angry to not find the key. We can't before because vals['container_ssh_port'] may not be set
        self.deploy_key(cr, uid, vals, context=context)

        #Run container
        execute.execute(ssh, cmd, context)

        time.sleep(3)

        self.deploy_post(cr, uid, vals, context)

        self.start(cr, uid, vals, context=context)

        ssh.close()
        sftp.close()

        for key, links in vals['container_links'].iteritems():
            if links['name'] == 'postfix':
                ssh, sftp = execute.connect(vals['container_fullname'], context=context)
                execute.execute(ssh, ['echo "root=' + vals['config_email_sysadmin'] + '" > /etc/ssmtp/ssmtp.conf'], context)
                execute.execute(ssh, ['echo "mailhub=postfix:25" >> /etc/ssmtp/ssmtp.conf'], context)
                execute.execute(ssh, ['echo "rewriteDomain=' + vals['container_fullname'] + '" >> /etc/ssmtp/ssmtp.conf'], context)
                execute.execute(ssh, ['echo "hostname=' + vals['container_fullname'] + '" >> /etc/ssmtp/ssmtp.conf'], context)
                execute.execute(ssh, ['echo "FromLineOverride=YES" >> /etc/ssmtp/ssmtp.conf'], context)
                ssh.close()
                sftp.close()

        #For shinken
        self.save(cr, uid, [vals['container_id']], context=context)

        return

    def purge(self, cr, uid, vals, context={}):
        context.update({'clouder-self': self, 'clouder-cr': cr, 'clouder-uid': uid})

        self.purge_key(cr, uid, vals, context=context)

        ssh, sftp = execute.connect(vals['server_domain'], vals['server_ssh_port'], 'root', context)
        execute.execute(ssh, ['sudo','docker', 'stop', vals['container_name']], context)
        execute.execute(ssh, ['sudo','docker', 'rm', vals['container_name']], context)
        execute.execute(ssh, ['rm', '-rf', '/opt/keys/' + vals['container_fullname']], context)
        ssh.close()
        sftp.close()


        return

    def stop(self, cr, uid, vals, context={}):
        context.update({'clouder-self': self, 'clouder-cr': cr, 'clouder-uid': uid})
        ssh, sftp = execute.connect(vals['server_domain'], vals['server_ssh_port'], 'root', context)
        execute.execute(ssh, ['docker', 'stop', vals['container_name']], context)
        ssh.close()
        sftp.close()

    def start(self, cr, uid, vals, context={}):
        context.update({'clouder-self': self, 'clouder-cr': cr, 'clouder-uid': uid})
        self.stop(cr, uid, vals, context=context)
        ssh, sftp = execute.connect(vals['server_domain'], vals['server_ssh_port'], 'root', context)
        execute.execute(ssh, ['docker', 'start', vals['container_name']], context)
        ssh.close()
        sftp.close()
        time.sleep(3)


    def deploy_key(self, cr, uid, vals, context={}):
        context.update({'clouder-self': self, 'clouder-cr': cr, 'clouder-uid': uid})
        # restart_required = False
        # try:
        #     ssh_container, sftp_container = execute.connect(vals['container_fullname'], context=context)
        # except:
        #     restart_required = True
        #     pass

        self.purge_key(cr, uid, vals, context=context)
        execute.execute_local(['ssh-keygen', '-t', 'rsa', '-C', 'yannick.buron@gmail.com', '-f', vals['config_home_directory'] + '/.ssh/keys/' + vals['container_fullname'], '-N', ''], context)
        execute.execute_write_file(vals['config_home_directory'] + '/.ssh/config', 'Host ' + vals['container_fullname'], context)
        execute.execute_write_file(vals['config_home_directory'] + '/.ssh/config', '\n  HostName ' + vals['server_domain'], context)
        execute.execute_write_file(vals['config_home_directory'] + '/.ssh/config', '\n  Port ' + str(vals['container_ssh_port']), context)
        execute.execute_write_file(vals['config_home_directory'] + '/.ssh/config', '\n  User root', context)
        execute.execute_write_file(vals['config_home_directory'] + '/.ssh/config', '\n  IdentityFile ~/.ssh/keys/' + vals['container_fullname'], context)
        execute.execute_write_file(vals['config_home_directory'] + '/.ssh/config', '\n#END ' + vals['container_fullname'] + '\n', context)
        ssh, sftp = execute.connect(vals['server_domain'], vals['server_ssh_port'], 'root', context)
        execute.execute(ssh, ['mkdir', '/opt/keys/' + vals['container_fullname']], context)
        sftp.put(vals['config_home_directory'] + '/.ssh/keys/' + vals['container_fullname'] + '.pub', '/opt/keys/' + vals['container_fullname'] + '/authorized_keys')
        ssh.close()
        sftp.close()

        # _logger.info('restart required %s', restart_required)
        # if not restart_required:
        #     execute.execute(ssh_container, ['supervisorctl', 'restart', 'sshd'], context)
        #     ssh_container.close()
        #     sftp_container.close()
        # else:
        #     self.start(cr, uid, vals, context=context)


        if vals['apptype_name'] == 'backup':
            shinken_ids = self.search(cr, uid, [('application_id.type_id.name', '=','shinken')], context=context)
            if not shinken_ids:
                execute.log('The shinken isnt configured in conf, skipping deploying backup keys in shinken', context)
                return
            for shinken in self.browse(cr, uid, shinken_ids, context=context):
                shinken_vals = self.get_vals(cr, uid, shinken.id, context=context)
                ssh, sftp = execute.connect(shinken_vals['container_fullname'], username='shinken', context=context)
                execute.execute(ssh, ['rm', '-rf', '/home/shinken/.ssh/keys/' + vals['container_fullname'] + '*'], context)
                execute.send(sftp, vals['config_home_directory'] + '/.ssh/keys/' + vals['container_fullname'] + '.pub', '/home/shinken/.ssh/keys/' + vals['container_fullname'] + '.pub', context)
                execute.send(sftp, vals['config_home_directory'] + '/.ssh/keys/' + vals['container_fullname'], '/home/shinken/.ssh/keys/' + vals['container_fullname'], context)
                execute.execute(ssh, ['chmod', '-R', '700', '/home/shinken/.ssh'], context)
                execute.execute(ssh, ['sed', '-i', "'/Host " + vals['container_fullname'] + "/,/END " + vals['container_fullname'] + "/d'", '/home/shinken/.ssh/config'], context)
                execute.execute(ssh, ['echo "Host ' + vals['container_fullname'] + '" >> /home/shinken/.ssh/config'], context)
                execute.execute(ssh, ['echo "    Hostname ' + vals['server_domain'] + '" >> /home/shinken/.ssh/config'], context)
                execute.execute(ssh, ['echo "    Port ' + str(vals['container_ssh_port']) + '" >> /home/shinken/.ssh/config'], context)
                execute.execute(ssh, ['echo "    User backup" >> /home/shinken/.ssh/config'], context)
                execute.execute(ssh, ['echo "    IdentityFile  ~/.ssh/keys/' + vals['container_fullname'] + '" >> /home/shinken/.ssh/config'], context)
                execute.execute(ssh, ['echo "#END ' + vals['container_fullname'] +'" >> ~/.ssh/config'], context)


    def purge_key(self, cr, uid, vals, context={}):
        execute.execute_local([modules.get_module_path('clouder') + '/res/sed.sh', vals['container_fullname'], vals['config_home_directory'] + '/.ssh/config'], context)
        execute.execute_local(['rm', '-rf', vals['config_home_directory'] + '/.ssh/keys/' + vals['container_fullname']], context)
        execute.execute_local(['rm', '-rf', vals['config_home_directory'] + '/.ssh/keys/' + vals['container_fullname'] + '.pub'], context)
        ssh, sftp = execute.connect(vals['server_domain'], vals['server_ssh_port'], 'root', context)
        execute.execute(ssh, ['rm', '-rf', '/opt/keys/' + vals['container_fullname'] + '/authorized_keys'], context)
        ssh.close()
        sftp.close()


class ClouderContainerPort(models.Model):
    _name = 'clouder.container.port'

    container_id = fields.Many2one('clouder.container', 'Container', ondelete="cascade", required=True)
    name = fields.Char('Name', size=64, required=True)
    localport = fields.Char('Local port', size=12, required=True)
    hostport = fields.Char('Host port', size=12)
    expose = fields.Selection([('internet','Internet'),('local','Local')],'Expose?', required=True)
    udp = fields.Boolean('UDP?')

    _defaults = {
        'expose': 'local'
    }

    _sql_constraints = [
        ('name_uniq', 'unique(container_id,name)', 'Port name must be unique per container!'),
    ]

class ClouderContainerVolume(models.Model):
    _name = 'clouder.container.volume'

    container_id = fields.Many2one('clouder.container', 'Container', ondelete="cascade", required=True)
    name = fields.Char('Path', size=128, required=True)
    hostpath = fields.Char('Host path', size=128)
    user = fields.Char('System User', size=64)
    readonly = fields.Boolean('Readonly?')
    nosave = fields.Boolean('No save?')


    _sql_constraints = [
        ('name_uniq', 'unique(container_id,name)', 'Volume name must be unique per container!'),
    ]

class ClouderContainerOption(models.Model):
    _name = 'clouder.container.option'

    container_id = fields.Many2one('clouder.container', 'Container', ondelete="cascade", required=True)
    name = fields.Many2one('clouder.application.type.option', 'Option', required=True)
    value = fields.Text('Value')

    _sql_constraints = [
        ('name_uniq', 'unique(container_id,name)', 'Option name must be unique per container!'),
    ]


class ClouderContainerLink(models.Model):
    _name = 'clouder.container.link'

    container_id = fields.Many2one('clouder.container', 'Container', ondelete="cascade", required=True)
    name = fields.Many2one('clouder.application', 'Application', required=True)
    target = fields.Many2one('clouder.container', 'Target')


    _sql_constraints = [
        ('name_uniq', 'unique(container_id,name)', 'Links must be unique per container!'),
    ]


    @api.multi
    def get_vals(self):
        vals = {}

        vals.update(self.container_id.get_vals())
        if self.target:
            target_vals = self.target_id.get_vals()
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
        _logger.info('link %s, apptype %s', vals['link_target_app_code'], vals['apptype_name'])
        if vals['link_target_app_code'] == 'backup-upl' and vals['apptype_name'] == 'backup':

            directory = '/opt/upload/' + vals['container_fullname']
            ssh_link, sftp_link = execute.connect(vals['link_target_container_fullname'], context=context)
            execute.execute(ssh_link, ['mkdir', '-p', directory], context)
            ssh_link.close()
            sftp_link.close()

            ssh, sftp = execute.connect(vals['container_fullname'], username='backup', context=context)
            execute.send(sftp, vals['config_home_directory'] + '/.ssh/config', '/home/backup/.ssh/config', context)
            execute.send(sftp, vals['config_home_directory'] + '/.ssh/keys/' + vals['link_target_container_fullname'] + '.pub', '/home/backup/.ssh/keys/' + vals['link_target_container_fullname'] + '.pub', context)
            execute.send(sftp, vals['config_home_directory'] + '/.ssh/keys/' + vals['link_target_container_fullname'], '/home/backup/.ssh/keys/' + vals['link_target_container_fullname'], context)
            execute.execute(ssh, ['chmod', '-R', '700', '/home/backup/.ssh'], context)
            execute.execute(ssh, ['rsync', '-ra', '/opt/backup/', vals['link_target_container_fullname'] + ':' + directory], context)
            execute.execute(ssh, ['rm', '/home/backup/.ssh/keys/*'], context)
            ssh.close()
            sftp.close()
        return

    def deploy(self, cr, uid, vals, context={}):
        context.update({'clouder-self': self, 'clouder-cr': cr, 'clouder-uid': uid})
        self.purge(cr, uid, vals, context=context)
        if not 'link_target_container_id' in vals:
            execute.log('The target isnt configured in the link, skipping deploy link', context)
            return
        if vals['link_target_app_code'] not in vals['container_links']:
            execute.log('The target isnt in the application link for container, skipping deploy link', context)
            return
        if not vals['container_links'][vals['link_target_app_code']]['container']:
            execute.log('This application isnt for container, skipping deploy link', context)
            return
        self.deploy_link(cr, uid, vals, context=context)

    def purge_link(self, cr, uid, vals, context={}):
        if vals['link_target_app_code'] == 'backup_upload' and vals['apptype_name'] == 'backup':
            directory = '/opt/upload/' + vals['container_fullname']
            ssh = execute.connect(vals['link_target_container_fullname'], context=context)
            execute.execute(ssh, ['rm', '-rf', directory], context)
            ssh.close()
        return

    def purge(self, cr, uid, vals, context={}):
        context.update({'clouder-self': self, 'clouder-cr': cr, 'clouder-uid': uid})
        if not 'link_target_container_id' in vals:
            execute.log('The target isnt configured in the link, skipping deploy link', context)
            return
        if vals['link_target_app_code'] not in vals['container_links']:
            execute.log('The target isnt in the application link for container, skipping deploy link', context)
            return
        if not vals['container_links'][vals['link_target_app_code']]['container']:
            execute.log('This application isnt for container, skipping deploy link', context)
            return
        self.purge_link(cr, uid, vals, context=context)
