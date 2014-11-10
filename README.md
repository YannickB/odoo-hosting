SaaS
====

Use Odoo as an orchestrator to host any kind of application. Based on docker.

Installation :

-Install an OpenERP 7 on one physical server, and install the saas modules on it. I'll call orchestrator the system user running the OpenERP server.

-Install on the physical machine which will run the container the package docker.io (I use the deb http://get.docker.io/ubuntu docker main repo)

-Add the ssh key of orchestrator system user to the authorized_keys of the root user of the machine for containers

-On the OpenERP, add the server, generate images and start create the subcomponent container for shinken/bind/backup/proxy.

-Then, start creating your own applications and deploy them through the base menu


Help for documentation are more than welcome, you can contact me by mail if you need help for the using/installation.

Join https://launchpad.net/~odoo-vertical-hosting mailing-list for discussions regarding the project.
