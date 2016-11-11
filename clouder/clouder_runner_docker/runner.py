# -*- coding: utf-8 -*-
# Copyright 2015 Clouder SASU
# License LGPL-3.0 or later (http://gnu.org/licenses/lgpl.html).

from datetime import datetime
import logging
import os.path
import time
import yaml

from openerp import models, api, modules

_logger = logging.getLogger(__name__)


class ClouderImage(models.Model):
    """
    Add methods to manage the docker build specificity.
    """

    _inherit = 'clouder.image'

    def build_image(
            self, model, server, runner=False, expose_ports=None, salt=True):

        if not expose_ports:
            expose_ports = []

        res = super(ClouderImage, self).build_image(
            model, server, runner=runner, expose_ports=expose_ports, salt=salt)

        if not runner or runner.application_id.type_id.name == 'docker':

            path = '%s-%s' % (
                model.name, datetime.now().strftime('%Y%m%d.%H%M%S'),
            )
            if model._name == 'clouder.container':
                name = path
            else:
                name = model.fullpath

            if salt:
                build_dir = os.path.join(
                    '/srv', 'salt', 'containers', 'build_%s' % model.name,
                )
                server = model.salt_master
            else:
                build_dir = self.env['clouder.model']._get_directory_tmp(name)

            server.execute(['rm', '-rf', build_dir])
            server.execute(['mkdir', '-p', build_dir])

            if self.type_id:
                if self.type_id.name in [
                    'backup', 'salt-master', 'salt-minion'
                ]:
                    sources_path = os.path.join(
                        modules.get_module_path('clouder'), 'sources',
                    )
                else:
                    module_path = modules.get_module_path(
                        'clouder_template_%s' % self.type_id.name
                    )
                    sources_path = module_path and os.path.join(
                        module_path, 'sources'
                    )
                if sources_path and self.env['clouder.model'].local_dir_exist(
                    sources_path
                ):
                    server.send_dir(
                        sources_path, os.path.join(build_dir, 'sources'),
                    )

            docker_file = os.path.join(build_dir, 'Dockerfile')
            server.execute([
                'echo "%s" >> "%s"' % (
                    self.computed_dockerfile.replace('"', r'\\"'),
                    docker_file,
                ),
            ])

            if expose_ports:
                server.execute([
                    'echo "EXPOSE %s" >> "%s"' % (
                        ' '.join(expose_ports), docker_file,
                    ),
                ])

            if not salt:
                server.execute([
                    'docker', 'build', '--pull', '-t', name, build_dir,
                ])
                server.execute(['rm', '-rf', build_dir])

            return name
        return res


class ClouderImageVersion(models.Model):
    """
    Add methods to manage the docker build specificity.
    """

    _inherit = 'clouder.image.version'

    @api.multi
    def hook_build(self):

        res = super(ClouderImageVersion, self).hook_build()

        if self.registry_id.application_id.type_id.name == 'registry':
            server = self.registry_id.server_id
            name = self.image_id.build_image(self, server)
            server.execute(
                ['docker', 'push', name])

            server.execute(['docker', 'rmi', self.name])
        return res

    @api.multi
    def purge(self):
        """
        Delete an image from the private registry.
        """

        res = super(ClouderImageVersion, self).purge()

        if self.registry_id.application_id.type_id.name == 'registry':

            img_address = self.registry_id and 'localhost:' + \
                self.registry_id.ports['http']['localport'] +\
                '/v1/repositories/' + self.image_id.name + \
                '/tags/' + self.name
            self.registry_id.execute(
                ['curl', '-o curl.txt -X', 'DELETE', img_address])

        return res


class ClouderServer(models.Model):
    """
    Add methods to manage the docker server specificities.
    """

    _inherit = 'clouder.server'

    @api.multi
    def deploy(self):
        super(ClouderServer, self).deploy()
        # Activate swarm mode if master
        if self.runner == 'swarm' and self.master_id == self:
            self.execute(
                ['docker', 'swarm', 'init', '--advertise-addr', self.ip])


class ClouderContainer(models.Model):
    """
    Add methods to manage the docker container specificities.
    """

    _inherit = 'clouder.container'

    @api.multi
    def hook_deploy_source(self):

        res = super(ClouderContainer, self).hook_deploy_source()
        if res:
            return res
        else:
            if self.server_id == self.image_version_id.registry_id.server_id:
                return self.image_version_id.fullpath_localhost
            else:
                # folder = '/etc/docker/certs.d/' +\
                #          self.image_version_id.registry_address
                # certfile = folder + '/ca.crt'
                # tmp_file = '/tmp/' + self.fullname
                # self.server_id.execute(['rm', certfile])
                # self.image_version_id.registry_id.get(
                #     '/etc/ssl/certs/docker-registry.crt', tmp_file)
                # self.server_id.execute(['mkdir', '-p', folder])
                # self.server_id.send(tmp_file, certfile)
                # self.server_id.execute_local(['rm', tmp_file])
                return self.image_version_id.fullpath

    @api.multi
    def hook_deploy_special_args(self, cmd):
        return cmd

    @api.multi
    def hook_deploy_special_cmd(self):
        return ''

    @api.multi
    def refresh_compose_file(self):
        """
        Refresh compose directory
        """
        res = self.get_container_compose_res()

        # Build compose dictionary
        compose = {'version': '2', 'services': {}}
        for service_dict in res:
            service = service_dict['self']
            image = service.image_id.build_image(
                service, service.server_id,
                expose_ports=service_dict['expose_ports'], salt=False)
            compose['services'][service_dict['compose_name']] = {
                'image': image,
                'ports': service_dict['ports'],
                'volumes': service_dict['volumes'],
                'volumes_from': service_dict['volumes_from'],
                'links': service_dict['links']
            }
        # Convert to yaml format
        compose = yaml.safe_dump(compose, default_flow_style=False)

        # Create directory and write compose file
        build_dir = self.env['clouder.model']._get_directory_tmp(
            'clouder-compose/' + self.name)
        self.server_id.execute(['rm', '-rf', build_dir])
        self.server_id.execute(['mkdir', '-p', build_dir])
        self.server_id.execute(
            ['echo "' + compose + '" > ' +
             build_dir + '/' + 'docker-compose.yml'])
        return build_dir

    @api.multi
    def hook_deploy_compose(self):
        """
        Deploy the container in the server.
        """

        super(ClouderContainer, self).hook_deploy_compose()

        if not self.server_id.runner_id or \
                self.server_id.runner_id.application_id.type_id.name \
                == 'docker':

            if False:  # not self.application_id.check_tags(['no-salt']):
                print 'TODO'
            else:
                # Create build directory and deploy
                build_dir = self.refresh_compose_file()
                self.server_id.execute(
                    ['docker-compose', '-p', self.name, 'up', '-d'],
                    path=build_dir)
        return

    @api.multi
    def hook_deploy_one(self):
        """
        Deploy the container in the server.
        """

        super(ClouderContainer, self).hook_deploy_one()

        if not self.server_id.runner_id or \
                self.server_id.runner_id.application_id.type_id.name \
                == 'docker':

            res = self.get_container_res()

            if self.executor == 'salt' and \
                    self.application_id.check_tags(['no-salt']):

                self.deploy_salt()
                self.salt_master.execute([
                    'rm', '-rf', '/var/cache/salt/master/file_lists/roots/'])
                self.salt_master.execute([
                    'salt', self.server_id.fulldomain, 'state.apply',
                    'container_deploy',
                    "pillar=\"{'container_name': '" + self.name +
                    "', 'image': '" + self.name + '-' +
                    datetime.now().strftime('%Y%m%d.%H%M%S') +
                    "', 'build': True}\""])

            else:

                if self.runner == 'engine':

                    # Build run command
                    cmd = ['docker', 'run', '-d', '-t', '--restart=always']

                    for port in res['ports']:
                        cmd.extend(['-p', port])
                    for volume in res['volumes']:
                        cmd.extend(['-v', volume])
                    for volume in res['volumes_from']:
                        cmd.extend(['--volumes-from', volume])
                    for link in res['links']:
                        cmd.extend(
                            ['--link', link['name'] + ':' + link['code']])
                    for key, environment in res['environment'].iteritems():
                        cmd.extend(
                            ['-e', '"' + key + '"="' + environment + '"'])
                    # Get special arguments depending of the application
                    cmd = self.hook_deploy_special_args(cmd)
                    cmd.extend(['--name', self.name])

                    if not self.image_version_id:
                        # Build image and get his name
                        cmd.extend([
                            self.image_id.build_image(
                                self, self.server_id,
                                expose_ports=res['expose_ports'], salt=False)])
                    else:
                        # Get image name from private repository
                        cmd.extend([self.hook_deploy_source()])

                    # Get special command depending of the application
                    cmd.extend([self.hook_deploy_special_cmd()])

                    # Run container
                    self.server_id.execute(cmd)

                if self.runner == 'swarm':

                    # Check if network exist, create otherwise
                    network = self.environment_id.prefix + '-network'
                    exist = self.master_id.execute([
                        'docker', 'network', 'ls',
                        '|', 'grep', network])
                    if not exist:
                        self.master_id.execute([
                            'docker', 'network', 'create', '--driver',
                            'overlay', network])

                    # Build service create command
                    cmd = ['docker', 'service', 'create']

                    for port in res['ports']:
                        cmd.extend(['-p', port])
                    for volume in res['volumes']:
                        cmd.extend(['--mount', volume])
                    # Get volumes from data container
                    for volume in res['volumes_from']:
                        cmd.extend(['--mount', volume])
                    for key, environment in res['environment'].iteritems():
                        cmd.extend(
                            ['-e', '"' + key + '"="' + environment + '"'])
                    cmd.extend(['--network', network])
                    # Get network from application link to this container
                    for link in res['links']:
                        cmd.extend(['--network', link])
                    # Get special arguments depending of the application
                    cmd = self.hook_deploy_special_args(cmd)
                    cmd.extend(['--name', self.name])
                    # Set number of replicas
                    cmd.extend(['--replicas', str(self.scale)])

                    if not self.image_version_id:
                        # Build image and get his name
                        cmd.extend([
                            self.image_id.build_image(
                                self, self.master_id,
                                expose_ports=res['expose_ports'], salt=False)])
                    else:
                        # Get image name from private repository
                        cmd.extend([self.hook_deploy_source()])

                    # Get special command depending of the application
                    cmd.extend([self.hook_deploy_special_cmd()])

                    # Run service
                    self.master_id.execute(cmd)
        return

    @api.multi
    def hook_purge_compose(self):
        """
        Remove container compose.
        """
        res = super(ClouderContainer, self).hook_purge_one()

        if not self.server_id.runner_id or \
                self.server_id.runner_id.application_id.type_id.name\
                == 'docker':

            if False:  # not self.application_id.check_tags(['no-salt']):
                print 'TODO'
            else:
                # Ensure build directory is up-to-date and purge
                build_dir = self.refresh_compose_file()
                self.server_id.execute(
                    ['docker-compose', 'down', '-v'], path=build_dir)
                self.server_id.execute(['rm', '-rf', build_dir])

        return res

    @api.multi
    def hook_purge_one(self):
        """
        Remove the container.
        """
        res = super(ClouderContainer, self).hook_purge_one()

        if not self.server_id.runner_id or \
                self.server_id.runner_id.application_id.type_id.name\
                == 'docker':

            if self.executor == 'salt' and \
                    self.application_id.check_tags(['no-salt']):
                self.salt_master.execute([
                    'salt', self.server_id.fulldomain,
                    'state.apply', 'container_purge',
                    "pillar=\"{'container_name': '" + self.name + "'}\""])
            else:

                if self.runner == 'engine':
                    self.server_id.execute(['docker', 'rm', '-v', self.name])

                if self.runner == 'swarm':
                    # Remove service
                    self.master_id.execute(
                        ['docker', 'service', 'rm', self.name])
                    # Remove volume linked to this service
                    for volume in self.volume_ids:
                        self.master_id.execute(
                            ['docker', 'volume', 'rm',
                             self.name + '-' + volume.name])
                    # If last container using this network, delete it
                    if not self.search([
                            ('environment_id', '=', self.environment_id.id),
                            ('id', '!=', self.id)]):
                        self.server_id.execute(
                            ['docker', 'network', 'rm',
                             self.environment_id.prefix + '-network'])

        return res

    @api.multi
    def stop_exec(self):
        """
        Stop the container.
        """

        res = super(ClouderContainer, self).stop_exec()

        if self.childs and 'exec' in self.childs:
            self.childs['exec'].stop_exec()
            return res

        if not self.server_id.runner_id or \
                self.server_id.runner_id.application_id.type_id.name\
                == 'docker':
            if not self.application_id.check_tags(['no-salt']):
                self.salt_master.execute([
                    'salt', self.server_id.fulldomain, 'state.apply',
                    'container_stop',
                    "pillar=\"{'container_name': '" + self.name + "'}\""])
            else:
                if self.runner == 'engine':
                    self.server_id.execute(['docker', 'stop', self.name])
                if self.runner == 'swarm':
                    self.master_id.execute(
                        ['docker', 'service', 'scale',
                         self.name + '=0'])

        return res

    @api.multi
    def start_exec(self):
        """
        Restart the container.
        """

        res = super(ClouderContainer, self).start_exec()

        if self.childs and 'exec' in self.childs:
            self.childs['exec'].start_exec()
            return res

        if not self.server_id.runner_id or \
                self.server_id.runner_id.application_id.type_id.name\
                == 'docker':

            if not self.application_id.check_tags(['no-salt']):
                self.salt_master.execute([
                    'salt', self.server_id.fulldomain,
                    'state.apply', 'container_start',
                    "pillar=\"{'container_name': '" + self.name + "'}\""])
            else:
                if self.runner == 'engine':
                    self.server_id.execute(['docker', 'start', self.name])
                if self.runner == 'swarm':
                    self.master_id.execute(
                        ['docker', 'service', 'scale',
                         self.name + '=' + str(self.scale)])

            time.sleep(3)

        return res
