Clouder
-------

Clouder is a platform which aim to standardize the good practices to host open-source softwares. Whether you are launching an hosting offer, are the sysadmin of a company or just want to host softwares for you and your friends, Clouder will allow you to easily deploy and maintain a professionnal infrastructure with very basic technical knowledge.

More specifically, it is an orchestrator which is based on the container technology (currently only support Docker), each application will be installed inside a container and Clouder will establish links between them. It is based on Odoo, an open-source software which is very efficient to manage this kind of workflow and process.

You'll find in the project the core module, clouder, which install the clouder concepts in Odoo, and the template modules (like clouder_template_odoo) which install data and functions specifics to each applications you want to host. Once you are familiar with Clouder, installing an application is as easy as filling a form! (Which mean you can automatate it with a form on your website).
And the best is, you don't need to make extensive research if you want to provide hosting for a new app, just install the template module made by others and you're set.


Community
---------

You can find more informations, support forum and mailing-list on https://www.goclouder.net/, you can find the documentation at http://doc.goclouder.net/.

Developpement (including documentation) is done here on github, contributions are welcome; please read the CLA guidelines https://github.com/clouder-community/clouder/blob/8.0/doc/cla/sign-cla.md if you want to make a pull request.


Getting started
---------------

(To refactor and move on functional documentation)

Installation :

-Install an OpenERP 7 on one physical server, and install the clouder modules on it. I'll call orchestrator the system user running the OpenERP server.

-Install on the physical machine which will run the container the package docker.io (I use the deb http://get.docker.io/ubuntu docker main repo)

-Add the ssh key of orchestrator system user to the authorized_keys of the root user of the machine for containers

-On the OpenERP, add the server, generate images and start create the subcomponent container for shinken/bind/backup/proxy.

-Then, start creating your own applications and deploy them through the base menu
