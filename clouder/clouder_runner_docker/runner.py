# -*- coding: utf-8 -*-
# Copyright 2015 Clouder SASU
# License LGPL-3.0 or later (http://gnu.org/licenses/lgpl.html).

from datetime import datetime
import logging
import os.path
import time
import yaml

try:
    from odoo import models, api, modules
except ImportError:
    from openerp import models, api, modules

_logger = logging.getLogger(__name__)


class ClouderImage(models.Model):
    """
    Add methods to manage the docker build specificity.
    """

    _inherit = 'clouder.image'

    def build_image(
            self, model, node, runner=False, expose_ports=None, salt=True):

        if not expose_ports:
            expose_ports = []

        res = super(ClouderImage, self).build_image(
            model, node, runner=runner, expose_ports=expose_ports, salt=salt)

        if not runner or runner.application_id.type_id.name == 'docker':

            path = '%s-%s' % (
                model.name, datetime.now().strftime('%Y%m%d.%H%M%S'),
            )
            if model._name == 'clouder.service':
                name = path
            else:
                name = model.fullpath

            if salt:
                build_dir = os.path.join(
                    '/srv', 'salt', 'services', 'build_%s' % model.name,
                )
                node = model.salt_master
            else:
                build_dir = self.env['clouder.model']._get_directory_tmp(name)

            node.execute(['rm', '-rf', build_dir])
            node.execute(['mkdir', '-p', build_dir])

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
                    node.send_dir(
                        sources_path, os.path.join(build_dir, 'sources'),
                    )

            docker_file = os.path.join(build_dir, 'Dockerfile')
            node.execute([
                'echo "%s" >> "%s"' % (
                    self.computed_dockerfile.replace('"', r'\"'),
                    docker_file,
                ),
            ])

            if expose_ports:
                node.execute([
                    'echo "EXPOSE %s" >> "%s"' % (
                        ' '.join(expose_ports), docker_file,
                    ),
                ])

            if not salt:
                node.execute([
                    'docker', 'build', '--pull', '-t', name, build_dir,
                ])
                node.execute(['rm', '-rf', build_dir])

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
            node = self.registry_id.node_id
            name = self.image_id.build_image(self, node)
            node.execute(
                ['docker', 'push', name])

            node.execute(['docker', 'rmi', self.name])
        return res

    @api.multi
    def purge(self):
        """
        Delete an image from the private registry.
        """

        res = super(ClouderImageVersion, self).purge()

        if self.registry_id.application_id.type_id.name == 'registry':

            img_address = self.registry_id and 'localhost:' + \
                self.registry_id.ports['http']['local_port'] +\
                '/v1/repositories/' + self.image_id.name + \
                '/tags/' + self.name
            self.registry_id.execute(
                ['curl', '-o curl.txt -X', 'DELETE', img_address])

        return res


class ClouderNode(models.Model):
    """
    Add methods to manage the docker node specificities.
    """

    _inherit = 'clouder.node'

    @api.multi
    def configure_exec(self):
        super(ClouderNode, self).configure_exec()
        # Activate swarm mode if master
        if self.runner == 'swarm':
            # If master, create swarm
            if self.master_id == self:
                self.execute(
                    ['docker', 'swarm', 'init',
                     '--advertise-addr', self.private_ip])
            # If not master, join swarm
            else:
                token = self.master_id.execute([
                    'docker', 'swarm', 'join-token', '-q', 'worker'])
                token = token.replace('\n', '')
                self.execute([
                    'docker', 'swarm', 'join',
                    '--token', token, self.master_id.private_ip + ':2377'])


class ClouderService(models.Model):
    """
    Add methods to manage the docker service specificities.
    """

    _inherit = 'clouder.service'

    @api.multi
    def hook_deploy_source(self):

        res = super(ClouderService, self).hook_deploy_source()
        if res:
            return res
        else:
            if self.node_id == self.image_version_id.registry_id.node_id:
                return self.image_version_id.fullpath_localhost
            else:
                # folder = '/etc/docker/certs.d/' +\
                #          self.image_version_id.registry_address
                # certfile = folder + '/ca.crt'
                # tmp_file = '/tmp/' + self.fullname
                # self.node_id.execute(['rm', certfile])
                # self.image_version_id.registry_id.get(
                #     '/etc/ssl/certs/docker-registry.crt', tmp_file)
                # self.node_id.execute(['mkdir', '-p', folder])
                # self.node_id.send(tmp_file, certfile)
                # self.node_id.execute_local(['rm', tmp_file])
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
        res = self.get_service_compose_res()

        # Build compose dictionary
        compose = {'version': '2', 'services': {}}
        for service_dict in res:
            service = service_dict['self']
            image = service.image_id.build_image(
                service, service.node_id,
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
        self.node_id.execute(['rm', '-rf', build_dir])
        self.node_id.execute(['mkdir', '-p', build_dir])
        self.node_id.execute(
            ['echo "%s" > %s/docker-compose.yml' % (compose, build_dir)])
        return build_dir

    @api.multi
    def hook_deploy_compose(self):
        """
        Deploy the service in the node.
        """

        super(ClouderService, self).hook_deploy_compose()

        if not self.node_id.runner_id or \
                self.node_id.runner_id.application_id.type_id.name \
                == 'docker':

            if False:  # not self.application_id.check_tags(['no-salt']):
                self.log('TODO')
            else:
                # Create build directory and deploy
                build_dir = self.refresh_compose_file()
                self.node_id.execute(
                    ['docker-compose', '-p', self.name, 'up', '-d'],
                    path=build_dir)
        return

    @api.multi
    def hook_deploy_one(self):
        """
        Deploy the service in the node.
        """

        super(ClouderService, self).hook_deploy_one()

        if not self.node_id.runner_id or \
                self.node_id.runner_id.application_id.type_id.name \
                == 'docker':

            res = self.get_service_res()

            if self.executor == 'salt' and \
                    self.application_id.check_tags(['no-salt']):

                self.deploy_salt()
                self.salt_master.execute([
                    'rm', '-rf', '/var/cache/salt/master/file_lists/roots/'])
                self.salt_master.execute([
                    'salt', self.node_id.fulldomain, 'state.apply',
                    'service_deploy',
                    "pillar=\"{'service_name': '" + self.name +
                    "', 'image': '" + self.name + '-' +
                    datetime.now().strftime('%Y%m%d.%H%M%S') +
                    "', 'build': True}\""])

            elif self.node_id.provider_id and \
                    self.node_id.provider_id.type == 'service':
                self.log('TODO')

            else:

                if self.runner == 'engine':

                    # Build run command
                    cmd = ['docker', 'run', '-d', '-t', '--restart=always']
                    cmd += ('-p %s' % port for port in res['ports'])
                    cmd += ('-v %s' % volume for volume in res['volumes'])
                    cmd += ('-v %s' % volume for volume in res['volumes_from'])
                    cmd += ('--link %s:%s' % (link['name'], link['code'])
                            for link in res['links'])
                    cmd += ('-e "%s=%s"' % (key, environment)
                            for key, environment
                            in res['environment'].iteritems())
                    # Get special arguments depending of the application
                    cmd = self.hook_deploy_special_args(cmd)
                    cmd += ['--name', self.name]

                    if not self.image_version_id:
                        # Build image and get his name
                        cmd.append(
                            self.image_id.build_image(
                                self, self.node_id,
                                expose_ports=res['expose_ports'], salt=False))
                    else:
                        # Get image name from private repository
                        cmd.append(self.hook_deploy_source())

                    # Get special command depending of the application
                    cmd.append(self.hook_deploy_special_cmd())

                    # Run service
                    self.node_id.execute(cmd)

                elif self.runner == 'swarm':

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

                    cmd += ('-p %s' % port for port in res['ports'])
                    cmd += ('--mount %s' % volume for volume in res['volumes'])

                    # Get volumes from data service
                    cmd += ('--mount %s' % volume
                            for volume in res['volumes_from'])
                    cmd += ('-e "%s=%s"' % (key, environment)
                            for key, environment
                            in res['environment'].iteritems())
                    cmd += ['--network', network]
                    # Get network from application link to this service
                    cmd += (['--network', link] for link in res['links'])
                    # Get special arguments depending of the application
                    cmd = self.hook_deploy_special_args(cmd)
                    cmd += ['--name', self.name]
                    # Set number of replicas
                    cmd += ['--replicas', str(self.scale)]

                    if not self.image_version_id:
                        # Build image and get his name
                        cmd.append(
                            self.image_id.build_image(
                                self, self.master_id,
                                expose_ports=res['expose_ports'], salt=False))
                    else:
                        # Get image name from private repository
                        cmd.append(self.hook_deploy_source())

                    # Get special command depending of the application
                    cmd.append(self.hook_deploy_special_cmd())

                    # Run service
                    self.master_id.execute(cmd)

                    # Keep here until service is deployed
                    self.wait_for_start()
        return

    @api.multi
    def hook_purge_compose(self):
        """
        Remove service compose.
        """
        res = super(ClouderService, self).hook_purge_one()

        if not self.node_id.runner_id or \
                self.node_id.runner_id.application_id.type_id.name\
                == 'docker':

            if False:  # not self.application_id.check_tags(['no-salt']):
                self.log('TODO')
            else:
                # Ensure build directory is up-to-date and purge
                build_dir = self.refresh_compose_file()
                self.node_id.execute(
                    ['docker-compose', 'down', '-v'], path=build_dir)
                self.node_id.execute(['rm', '-rf', build_dir])

        return res

    @api.multi
    def hook_purge_one(self):
        """
        Remove the service.
        """
        res = super(ClouderService, self).hook_purge_one()

        if not self.node_id.runner_id or \
                self.node_id.runner_id.application_id.type_id.name\
                == 'docker':

            if self.executor == 'salt' and \
                    self.application_id.check_tags(['no-salt']):
                self.salt_master.execute([
                    'salt', self.node_id.fulldomain,
                    'state.apply', 'service_purge',
                    "pillar=\"{'service_name': '" + self.name + "'}\""])

            elif self.node_id.provider_id and \
                    self.node_id.provider_id.type == 'service':
                self.log('TODO')

            else:

                if self.runner == 'engine':
                    self.node_id.execute(['docker', 'rm', '-v', self.name])

                elif self.runner == 'swarm':
                    # Remove service
                    self.master_id.execute(
                        ['docker', 'service', 'rm', self.name])
                    # If last service using this network, delete it
                    if not self.search([
                            ('environment_id', '=', self.environment_id.id),
                            ('id', '!=', self.id)]):
                        self.node_id.execute(
                            ['docker', 'network', 'rm',
                             self.environment_id.prefix + '-network'])
                # Remove volume linked to this service
                for volume in self.volume_ids:
                    self.node_id.execute(
                        ['docker', 'volume', 'rm',
                         self.name + '-' + volume.name])

        return res

    @api.multi
    def get_pod(self):
        return self.node_id.execute([
            'docker ps --format={{.Names}}',  '|',
            'grep', self.name + '.',  '|',
            'head -n1', '|', "awk '{print $1;}'"])

    def get_default_iteration_try(self):
        return 60

    def get_default_time_sleep(self):
        return 2

    @api.multi
    def wait_for_stop(self):

        # Keep here until service is deployed
        res = 'Start'
        i = 1
        total = self.get_default_iteration_try()
        while res and i <= total:
            self.log('Stop %s' % (self.name))
            self.log('Try %s/%s' % (i, total))
            res = self.get_pod()
            if res:
                time.sleep(self.get_default_time_sleep())
                i += 1

    @api.multi
    def wait_for_start(self):

        # Keep here until service is deployed
        res = ''
        i = 1
        total = self.get_default_iteration_try()
        while not res and i <= total:
            self.log('Start %s' % (self.name))
            self.log('Try %s/%s' % (i, total))
            res = self.get_pod()
            if not res:
                time.sleep(self.get_default_time_sleep())
                i += 1

    @api.multi
    def hook_stop(self):
        """
        Stop the service.
        """

        res = super(ClouderService, self).hook_stop()

        if not self.node_id.runner_id or \
                self.node_id.runner_id.application_id.type_id.name\
                == 'docker':
            if self.executor == 'salt' and \
                    self.application_id.check_tags(['no-salt']):
                self.salt_master.execute([
                    'salt', self.node_id.fulldomain, 'state.apply',
                    'service_stop',
                    "pillar=\"{'service_name': '" + self.name + "'}\""])

            elif self.node_id.provider_id and \
                    self.node_id.provider_id.type == 'service':
                self.log('TODO')

            else:
                if self.runner == 'engine':
                    self.node_id.execute(['docker', 'stop', self.name])
                elif self.runner == 'swarm':
                    self.master_id.execute(
                        ['docker', 'service', 'scale',
                         self.name + '=0'])
                    self.wait_for_stop()

        return res

    @api.multi
    def hook_start(self):
        """
        Restart the service.
        """

        res = super(ClouderService, self).hook_start()

        if not self.node_id.runner_id or \
                self.node_id.runner_id.application_id.type_id.name\
                == 'docker':

            if self.executor == 'salt' and \
                    self.application_id.check_tags(['no-salt']):
                self.salt_master.execute([
                    'salt', self.node_id.fulldomain,
                    'state.apply', 'service_start',
                    "pillar=\"{'service_name': '" + self.name + "'}\""])

            elif self.node_id.provider_id and \
                    self.node_id.provider_id.type == 'service':
                self.log('TODO')

            else:
                if self.runner == 'engine':
                    self.node_id.execute(['docker', 'start', self.name])
                elif self.runner == 'swarm':
                    self.master_id.execute(
                        ['docker', 'service', 'scale',
                         self.name + '=' + str(self.scale)])
                    self.wait_for_start()

            time.sleep(3)

        return res
