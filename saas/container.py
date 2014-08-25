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

STARTPORT = 48000
ENDPORT = 50000

class saas_server(osv.osv):
    _name = 'saas.server'
    _inherit = ['saas.model']

    _columns = {
        'name': fields.char('Domain name', size=64, required=True),
        'ip': fields.char('IP', size=64, required=True),
        'ssh_port': fields.char('SSH port', size=12, required=True),
        'mysql_passwd': fields.char('MySQL Passwd', size=64),
    }

    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'Name must be unique!'),
    ]

    def get_vals(self, cr, uid, id, type='', context={}):

        server = self.browse(cr, uid, id, context=context)
        vals ={}

        if 'from_config' not in context:
            config = self.pool.get('ir.model.data').get_object(cr, uid, 'saas', 'saas_settings') 
            vals.update(self.pool.get('saas.config.settings').get_vals(cr, uid, context=context))

        vals.update({
            type + 'server_id': server.id,
            type + 'server_domain': server.name,
            type + 'server_ip': server.ip,
            type + 'server_ssh_port': int(server.ssh_port),
            type + 'server_mysql_passwd': server.mysql_passwd,
            type + 'server_shinken_configfile': '/usr/local/shinken/etc/hosts/' + server.name + '.cfg'
        })
        return vals


    def start_containers(self, cr, uid, ids, context={}):
        container_obj = self.pool.get('saas.container')
        for server in self.browse(cr, uid, ids, context=context):
            container_ids = container_obj.search(cr, uid, [('server_id', '=', server.id)], context=context)
            for container in container_obj.browse(cr, uid, container_ids, context=context):
                vals = container_obj.get_vals(cr, uid, container.id, context=context)
                container_obj.start(cr, uid, vals, context=context)

    def stop_containers(self, cr, uid, ids, context={}):
        container_obj = self.pool.get('saas.container')
        for server in self.browse(cr, uid, ids, context=context):
            container_ids = container_obj.search(cr, uid, [('server_id', '=', server.id)], context=context)
            for container in container_obj.browse(cr, uid, container_ids, context=context):
                vals = container_obj.get_vals(cr, uid, container.id, context=context)
                container_obj.stop(cr, uid, vals, context=context)

    def deploy(self, cr, uid, vals, context={}):
        context.update({'saas-self': self, 'saas-cr': cr, 'saas-uid': uid})
        _logger.info('test %s', vals['shinken_server_domain'])
        if 'shinken_server_domain' in vals:
            ssh, sftp = execute.connect(vals['shinken_fullname'], context=context)
            sftp.put(vals['config_conductor_path'] + '/saas/saas_shinken/res/server-shinken.config', vals['server_shinken_configfile'])
            execute.execute(ssh, ['sed', '-i', '"s/NAME/' + vals['server_domain'] + '/g"', vals['server_shinken_configfile']], context)
            execute.execute(ssh, ['/etc/init.d/shinken', 'reload'], context)
            ssh.close()
            sftp.close()

    def purge(self, cr, uid, vals, context={}):
        context.update({'saas-self': self, 'saas-cr': cr, 'saas-uid': uid})
        if 'shinken_server_domain' in vals:
            ssh, sftp = execute.connect(vals['shinken_fullname'], context=context)
            execute.execute(ssh, ['rm', vals['server_shinken_configfile']], context)
            execute.execute(ssh, ['/etc/init.d/shinken', 'reload'], context)
            ssh.close()
            sftp.close()

class saas_container(osv.osv):
    _name = 'saas.container'
    _inherit = ['saas.model']

    def _get_ports(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for container in self.browse(cr, uid, ids, context=context):
            res[container.id] = ''
            first = True
            for port in container.port_ids:
                if not first:
                    res[container.id] += ', '
                res[container.id] += port.name + ' : ' + port.hostport
                first = False
        return res

    _columns = {
        'name': fields.char('Name', size=64, required=True),
        'application_id': fields.many2one('saas.application', 'Application', required=True),
        'image_id': fields.many2one('saas.image', 'Image', required=True),
        'server_id': fields.many2one('saas.server', 'Server', required=True),
        'image_version_id': fields.many2one('saas.image.version', 'Image version', required=True),
        'save_repository_id': fields.many2one('saas.save.repository', 'Save repository'),
        'time_between_save': fields.integer('Minutes between each save'),
        'saverepo_change': fields.integer('Days before saverepo change'),
        'saverepo_expiration': fields.integer('Days before saverepo expiration'),
        'date_next_save': fields.datetime('Next save planned'),
        'save_comment': fields.text('Save Comment'),
        'nosave': fields.boolean('No Save?'),
        'linked_container_ids': fields.many2many('saas.container', 'saas_container_linked_rel', 'from_id', 'to_id', 'Linked container', domain="[('server_id','=',server_id)]"),
        'port_ids': fields.one2many('saas.container.port', 'container_id', 'Ports'),
        'volume_ids': fields.one2many('saas.container.volume', 'container_id', 'Volumes'),
        'option_ids': fields.one2many('saas.container.option', 'container_id', 'Options'),
        'service_ids': fields.one2many('saas.service', 'container_id', 'Services'),
        'ports': fields.function(_get_ports, type='text', string='Ports'),
    }

    _sql_constraints = [
        ('name_uniq', 'unique(server_id,name)', 'Name must be unique per server!'),
    ]

    def _check_image(self, cr, uid, ids, context=None):
        for c in self.browse(cr, uid, ids, context=context):
            if c.image_id.id != c.image_version_id.image_id.id:
                return False
        return True

    def _check_links(self, cr, uid, ids, context=None):
        for c in self.browse(cr, uid, ids, context=context):
            links = {}
            for l in c.linked_container_ids:
                apptype = l.application_id.type_id.name
                if apptype in links:
                    return False
                links[apptype] = apptype
        return True

    _constraints = [
        (_check_image, "The image of image version must be the same than the image of container." , ['image_id','image_version_id']),
        (_check_links, "The image of image version must be the same than the image of container." , ['image_id','image_version_id']),
    ]

    def onchange_application_id(self, cr, uid, ids, application_id=False, context=None):
        result = {}
        if application_id:
            application = self.pool.get('saas.application').browse(cr, uid, application_id, context=context)
            result = {'value': {
                    'server_id': application.next_server_id.id,
                    'image_id': application.default_image_id.id,
                    'image_version_id': application.default_image_id.version_ids[0].id,
                    }
                }
        return result


    def get_vals(self, cr, uid, id, context={}):
        repo_obj = self.pool.get('saas.save.repository')
        vals = {}

        container = self.browse(cr, uid, id, context=context)

        now = datetime.now()
        if not container.save_repository_id:
            repo_ids = repo_obj.search(cr, uid, [('container_name','=',container.name),('container_server','=',container.server_id.name)], context=context)
            if repo_ids:
                self.write(cr, uid, [container.id], {'save_repository_id': repo_ids[0]}, context=context)
                container = self.browse(cr, uid, id, context=context)

        if not container.save_repository_id or datetime.strptime(container.save_repository_id.date_change, "%Y-%m-%d") < now or False:
            repo_vals ={
                'name': now.strftime("%Y-%m-%d") + '_' + container.name + '_' + container.server_id.name,
                'type': 'container',
                'date_change': (now + timedelta(days=container.saverepo_change or container.application_id.container_saverepo_change)).strftime("%Y-%m-%d"),
                'date_expiration': (now + timedelta(days=container.saverepo_expiration or container.application_id.container_saverepo_expiration)).strftime("%Y-%m-%d"),
                'container_name': container.name,
                'container_server': container.server_id.name,
            }
            repo_id = repo_obj.create(cr, uid, repo_vals, context=context)
            self.write(cr, uid, [container.id], {'save_repository_id': repo_id}, context=context)
            container = self.browse(cr, uid, id, context=context)

        if 'from_config' not in context:
            vals.update(self.pool.get('saas.image.version').get_vals(cr, uid, container.image_version_id.id, context=context))
            vals.update(self.pool.get('saas.application').get_vals(cr, uid, container.application_id.id, context=context))
            vals.update(self.pool.get('saas.save.repository').get_vals(cr, uid, container.save_repository_id.id, context=context))
        vals.update(self.pool.get('saas.server').get_vals(cr, uid, container.server_id.id, context=context))


        links = {}
        for link in  container.linked_container_ids:
            links[link.id] = {'id': link.id, 'apptype': link.application_id.type_id.name, 'name': link.name}

        ports = {}
        ssh_port = 22
        for port in container.port_ids:
            ports[port.name] = {'id': port.id, 'name': port.name, 'localport': port.localport, 'hostport': port.hostport, 'expose': port.expose, 'udp': port.udp}
            if port.name == 'ssh':
                ssh_port = port.hostport

        volumes = {}
        volumes_save = ''
        first = True
        for volume in container.volume_ids:
            volumes[volume.id] = {'id': volume.id, 'name': volume.name, 'hostpath': volume.hostpath, 'user': volume.user,'readonly': volume.readonly,'nosave': volume.nosave}
            if not volume.nosave:
                volumes_save += (not first and ',' or '') + volume.name
                first = False

        options = {}
        for option in container.application_id.type_id.option_ids:
            if option.type == 'container':
                options[option.name] = {'id': option.id, 'name': option.name, 'value': option.default}
        for option in container.option_ids:
            options[option.name.name] = {'id': option.id, 'name': option.name.name, 'value': option.value}

        root_password = False
        for key, option in options.iteritems():
            if option['name'] == 'root_password':
                root_password = option['value']

        unique_name = container.name + '_' + vals['server_domain']
        vals.update({
            'container_id': container.id,
            'container_name': container.name,
            'container_fullname': unique_name,
            'container_ports': ports,
            'container_volumes': volumes,
            'container_volumes_save': volumes_save,
            'container_ssh_port': ssh_port,
            'container_options': options,
            'container_links': links,
            'container_no_save': container.nosave,
            'container_shinken_configfile': '/usr/local/shinken/etc/services/' + unique_name + '.cfg',
            'container_root_password': root_password
        })

        return vals

    # def add_links(self, cr, uid, vals, context={}):
    #     return vals

    def create(self, cr, uid, vals, context={}):
        if ('port_ids' not in vals or not vals['port_ids']) and 'image_version_id' in vals:
            vals['port_ids'] = []
            for port in self.pool.get('saas.image.version').browse(cr, uid, vals['image_version_id'], context=context).image_id.port_ids:
                if port.expose != 'none':
                    vals['port_ids'].append((0,0,{'name':port.name,'localport':port.localport,'expose':port.expose,'udp':port.udp}))
        if ('volume_ids' not in vals or not vals['volume_ids']) and 'image_version_id' in vals:
            vals['volume_ids'] = []
            for volume in self.pool.get('saas.image.version').browse(cr, uid, vals['image_version_id'], context=context).image_id.volume_ids:
                vals['volume_ids'].append((0,0,{'name':volume.name,'hostpath':volume.hostpath,'user':volume.user,'readonly':volume.readonly,'nosave':volume.nosave}))
        if 'application_id' in vals and 'server_id' in vals:
            application = self.pool.get('saas.application').browse(cr, uid, vals['application_id'], context=context)
            if not 'linked_container_ids' in vals:
                vals['linked_container_ids'] = []
            if application.linked_local_containers:
                for type in application.linked_local_containers.split(','):
                    container_ids = self.search(cr, uid, [('name','=',type),('server_id','=',vals['server_id'])], context=context)
                    for container in self.browse(cr, uid, container_ids, context=context):
                        vals['linked_container_ids'].append((4,container.id))
        # vals = self.add_links(cr, uid, vals, context=context)
        return super(saas_container, self).create(cr, uid, vals, context=context)

    def write(self, cr, uid, ids, vals, context={}):
        version_obj = self.pool.get('saas.image.version')
        save_obj = self.pool.get('saas.save.save')
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
                context['forcesave'] = True
                save_id = self.save(cr, uid, [container.id], context=context)[container.id]
        res = super(saas_container, self).write(cr, uid, ids, vals, context=context)
        if flag:
            for container in self.browse(cr, uid, ids, context=context):
                self.reinstall(cr, uid, [container.id], context=context)
                self.get_vals(cr, uid, container.id, context=context)
                save_obj.restore(cr, uid, [save_id], context=context)
                self.end_log(cr, uid, container.id, context=context)
        if 'nosave' in vals:
            for container_id in ids:
                container_vals = self.get_vals(cr, uid, container_id, context=context)
                self.deploy_shinken(cr, uid, container_vals, context=context)
        return res

    def unlink(self, cr, uid, ids, context={}):
        service_obj = self.pool.get('saas.service')
        for container in self.browse(cr, uid, ids, context=context):
            service_obj.unlink(cr, uid, [s.id for s in container.service_ids], context=context)
        context['save_comment'] = 'Before unlink'
        self.save(cr, uid, ids, context=context)
        return super(saas_container, self).unlink(cr, uid, ids, context=context)

    def button_stop(self, cr, uid, ids, context={}):
        for container in self.browse(cr, uid, ids, context=context):
            vals = self.get_vals(cr, uid, container.id, context=context)
            self.stop(cr, uid, vals, context=context)

    def button_start(self, cr, uid, ids, context={}):
        for container in self.browse(cr, uid, ids, context=context):
            vals = self.get_vals(cr, uid, container.id, context=context)
            self.start(cr, uid, vals, context=context)

    def reinstall(self, cr, uid, ids, context={}):
        save_obj = self.pool.get('saas.save.save')
        for container in self.browse(cr, uid, ids, context=context):
            context['save_comment'] = 'Before reinstall'
            context['forcesave'] = True
            save_id = self.save(cr, uid, [container.id], context=context)[container.id]
            super(saas_container, self).reinstall(cr, uid, [container.id], context=context)
            save_obj.restore(cr, uid, [save_id], context=context)



    def save(self, cr, uid, ids, context={}):
        context.update({'saas-self': self, 'saas-cr': cr, 'saas-uid': uid})
        save_obj = self.pool.get('saas.save.save')

        res = {}
        for container in self.browse(cr, uid, ids, context=context):
            if 'nosave' in context or (container.nosave and not 'forcesave' in context):
                execute.log('This base container not be saved or the bup isnt configured in conf, skipping save container', context)
                continue
            context = self.create_log(cr, uid, container.id, 'save', context)
            vals = self.get_vals(cr, uid, container.id, context=context)
            if not 'bup_server_domain' in vals:
                execute.log('The bup isnt configured in conf, skipping save container', context)
                return
            save_vals = {
                'name': vals['now_bup'] + '_' + vals['container_fullname'],
                'repo_id': vals['saverepo_id'],
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

    def reset_shinken(self, cr, uid, ids, context={}):
        for container in self.browse(cr, uid, ids, context=context):
            vals = self.get_vals(cr, uid, container.id, context=context)
            self.deploy_shinken(cr, uid, vals, context=context)

    def deploy_post(self, cr, uid, vals, context=None):
        return

    def deploy(self, cr, uid, vals, context={}):
        context.update({'saas-self': self, 'saas-cr': cr, 'saas-uid': uid})
        self.purge(cr, uid, vals, context=context)

        ssh, sftp = execute.connect(vals['server_domain'], vals['server_ssh_port'], 'root', context)

        cmd = ['sudo','docker', 'run', '-d']
        nextport = STARTPORT
        for key, port in vals['container_ports'].iteritems():
            if not port['hostport']:
                while not port['hostport'] and nextport != ENDPORT:
                    port_ids = self.pool.get('saas.container.port').search(cr, uid, [('hostport','=',nextport),('container_id.server_id','=',vals['server_id'])], context=context)
                    if not port_ids and not execute.execute(ssh, ['netstat', '-an', '|', 'grep', str(nextport)], context):
                        self.pool.get('saas.container.port').write(cr, uid, [port['id']], {'hostport': nextport}, context=context)
                        port['hostport'] = nextport
                        if port['name'] == 'ssh':
                            vals['container_ssh_port'] = nextport
                    nextport += 1
                    _logger.info('nextport %s', nextport)
            _logger.info('server_id %s, hostport %s, localport %s', vals['server_ip'], port['hostport'], port['localport'])
            udp = ''
            if port['udp']:
                udp = '/udp'
            cmd.extend(['-p', vals['server_ip'] + ':' + str(port['hostport']) + ':' + port['localport'] + udp])
        for key, volume in vals['container_volumes'].iteritems():
            if volume['hostpath']:
                arg =  volume['hostpath'] + ':' + volume['name']
                if volume['readonly']:
                    arg += ':ro'
                cmd.extend(['-v', arg])
        for key, link in vals['container_links'].iteritems():
            cmd.extend(['--link', link['name'] + ':' + link['name']])
        cmd.extend(['-v', '/opt/keys/' + vals['container_fullname'] + '.pub:/opt/authorized_keys', '--name', vals['container_name'], vals['image_version_fullname']])

        #Deploy key now, otherwise the container will be angry to not find the key. We can't before because vals['container_ssh_port'] may not be set
        self.deploy_key(cr, uid, vals, context=context)

        #Run container
        execute.execute(ssh, cmd, context)

        time.sleep(3)

        self.deploy_post(cr, uid, vals, context)

        self.start(cr, uid, vals, context=context)

        time.sleep(3)

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

        self.deploy_shinken(cr, uid, vals, context=context)

        return

    def purge(self, cr, uid, vals, context={}):
        context.update({'saas-self': self, 'saas-cr': cr, 'saas-uid': uid})
        ssh, sftp = execute.connect(vals['server_domain'], vals['server_ssh_port'], 'root', context)
        execute.execute(ssh, ['sudo','docker', 'stop', vals['container_name']], context)
        execute.execute(ssh, ['sudo','docker', 'rm', vals['container_name']], context)
        ssh.close()
        sftp.close()

        self.purge_shinken(cr, uid, vals, context=context)
        self.purge_key(cr, uid, vals, context=context)
        return

    def stop(self, cr, uid, vals, context={}):
        context.update({'saas-self': self, 'saas-cr': cr, 'saas-uid': uid})
        ssh, sftp = execute.connect(vals['server_domain'], vals['server_ssh_port'], 'root', context)
        execute.execute(ssh, ['docker', 'stop', vals['container_name']], context)
        ssh.close()
        sftp.close()

    def start(self, cr, uid, vals, context={}):
        context.update({'saas-self': self, 'saas-cr': cr, 'saas-uid': uid})
        self.stop(cr, uid, vals, context=context)
        ssh, sftp = execute.connect(vals['server_domain'], vals['server_ssh_port'], 'root', context)
        execute.execute(ssh, ['docker', 'start', vals['container_name']], context)
        ssh.close()
        sftp.close()

    def deploy_shinken(self, cr, uid, vals, context={}):
        context.update({'saas-self': self, 'saas-cr': cr, 'saas-uid': uid})
        if not 'shinken_server_domain' in vals:
            execute.log('The shinken isnt configured in conf, skipping deploy container shinken', context)
            return
        self.purge_shinken(cr, uid, vals, context=context)
        ssh, sftp = execute.connect(vals['shinken_fullname'], context=context)
        file = 'container-shinken'
        if vals['container_no_save']:
            file = 'container-shinken-nosave'
        sftp.put(vals['config_conductor_path'] + '/saas/saas_shinken/res/' + file + '.config', vals['container_shinken_configfile'])
        execute.execute(ssh, ['sed', '-i', '"s/TYPE/container/g"', vals['container_shinken_configfile']], context)
        execute.execute(ssh, ['sed', '-i', '"s/UNIQUE_NAME/' + vals['container_fullname'] + '/g"', vals['container_shinken_configfile']], context)

        execute.execute(ssh, ['mkdir', '-p', '/opt/control-bup/restore/' + vals['container_fullname'] + '/latest'], context)
        execute.execute(ssh, ['echo "' + vals['now_date'] + '" > /opt/control-bup/restore/' + vals['container_fullname'] + '/latest/backup-date'], context)
        execute.execute(ssh, ['chown', '-R', 'shinken:shinken', '/opt/control-bup'], context)

        execute.execute(ssh, ['/etc/init.d/shinken', 'reload'], context)
        ssh.close()
        sftp.close()

    def purge_shinken(self, cr, uid, vals, context={}):
        context.update({'saas-self': self, 'saas-cr': cr, 'saas-uid': uid})
        if not 'shinken_server_domain' in vals:
            execute.log('The shinken isnt configured in conf, skipping purge container shinken', context)
            return
        ssh, sftp = execute.connect(vals['shinken_fullname'], context=context)
        execute.execute(ssh, ['rm', vals['container_shinken_configfile']], context)
        execute.execute(ssh, ['/etc/init.d/shinken', 'reload'], context)
        ssh.close()
        sftp.close()

    def deploy_key(self, cr, uid, vals, context={}):
        context.update({'saas-self': self, 'saas-cr': cr, 'saas-uid': uid})
        self.purge_key(cr, uid, vals, context=context)
        execute.execute_local(['ssh-keygen', '-t', 'rsa', '-C', 'yannick.buron@gmail.com', '-f', vals['config_home_directory'] + '/keys/' + vals['container_fullname'], '-N', ''], context)
        execute.execute_write_file(vals['config_home_directory'] + '/.ssh/config', 'Host ' + vals['container_fullname'], context)
        execute.execute_write_file(vals['config_home_directory'] + '/.ssh/config', '\n  HostName ' + vals['server_domain'], context)
        execute.execute_write_file(vals['config_home_directory'] + '/.ssh/config', '\n  Port ' + str(vals['container_ssh_port']), context)
        execute.execute_write_file(vals['config_home_directory'] + '/.ssh/config', '\n  User root', context)
        execute.execute_write_file(vals['config_home_directory'] + '/.ssh/config', '\n  IdentityFile ~/keys/' + vals['container_fullname'], context)
        execute.execute_write_file(vals['config_home_directory'] + '/.ssh/config', '\n#END ' + vals['container_fullname'] + '\n', context)
        ssh, sftp = execute.connect(vals['server_domain'], vals['server_ssh_port'], 'root', context)
        sftp.put(vals['config_home_directory'] + '/keys/' + vals['container_fullname'] + '.pub', '/opt/keys/' + vals['container_fullname'] + '.pub')
        ssh.close()
        sftp.close()
        if vals['container_id'] == vals['bup_id']:
            context['key_already_reset'] = True
            self.pool.get('saas.config.settings').reset_bup_key(cr, uid, [], context=context)
        self.start(cr, uid, vals, context=context)

    def purge_key(self, cr, uid, vals, context={}):
        ssh, sftp = execute.connect('localhost', 22, 'saas-conductor', context)
        execute.execute(ssh, ['sed', '-i', "'/Host " + vals['container_fullname'] + "/,/END " + vals['container_fullname'] + "/d'", vals['config_home_directory'] + '/.ssh/config'], context)
        ssh.close()
        sftp.close()
        execute.execute_local(['rm', '-rf', vals['config_home_directory'] + '/keys/' + vals['container_fullname']], context)
        execute.execute_local(['rm', '-rf', vals['config_home_directory'] + '/keys/' + vals['container_fullname'] + '.pub'], context)
        ssh, sftp = execute.connect(vals['server_domain'], vals['server_ssh_port'], 'root', context)
        execute.execute(ssh, ['rm', '-rf', '/opt/keys/' + vals['container_fullname'] + '*'], context)
        ssh.close()
        sftp.close()




class saas_container_port(osv.osv):
    _name = 'saas.container.port'

    _columns = {
        'container_id': fields.many2one('saas.container', 'Container', ondelete="cascade", required=True),
        'name': fields.char('Name', size=64, required=True),
        'localport': fields.char('Local port', size=12, required=True),
        'hostport': fields.char('Host port', size=12),
        'expose': fields.selection([('internet','Internet'),('local','Local')],'Expose?', required=True),
        'udp': fields.boolean('UDP?'),
    }

    _defaults = {
        'expose': 'local'
    }

    _sql_constraints = [
        ('name_uniq', 'unique(container_id,name)', 'Port name must be unique per container!'),
    ]

class saas_container_volume(osv.osv):
    _name = 'saas.container.volume'

    _columns = {
        'container_id': fields.many2one('saas.container', 'Container', ondelete="cascade", required=True),
        'name': fields.char('Path', size=128, required=True),
        'hostpath': fields.char('Host path', size=128),
        'user': fields.char('System User', size=64),
        'readonly': fields.boolean('Readonly?'),
        'nosave': fields.boolean('No save?'),
    }

    _sql_constraints = [
        ('name_uniq', 'unique(container_id,name)', 'Volume name must be unique per container!'),
    ]

class saas_container_option(osv.osv):
    _name = 'saas.container.option'

    _columns = {
        'container_id': fields.many2one('saas.container', 'Container', ondelete="cascade", required=True),
        'name': fields.many2one('saas.application.type.option', 'Option', required=True),
        'value': fields.text('Value'),
    }

    _sql_constraints = [
        ('name_uniq', 'unique(container_id,name)', 'Option name must be unique per container!'),
    ]
