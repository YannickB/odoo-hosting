Clouder
-------

<b>This project isn't maintained anymore. We believe the core need to be rewritten from scratch to be more compatible with the microservices principles, unfortunately Clouder was centralizing too many things instead of just being so sort of control interface</b>

Some developments are being made in a new project, which take into account both the learning we get with Clouder and the microservices principles, but you should not expect to see anything working soon.
Meanwhile, the code of Clouder will stay here for reference, still open-sourced, and available if anyone want to become the new maintainers.

[![Join the chat at https://gitter.im/clouder-community/clouder](https://badges.gitter.im/clouder-community/clouder.svg)](https://gitter.im/clouder-community/clouder?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge)

Clouder is a platform which aim to standardize good practices for hosting open-source software. Whether you are launching a hosting offer, are the sysadmin of a company, or just want to host software for you and your friends, Clouder will allow you to easily deploy and maintain a professionnal infrastructure with very basic technical knowledge.

More specifically, it is an orchestrator which is based on container technology (currently only supports Docker), each application will be installed inside a container and Clouder will establish links between them. It is based on Odoo, an open-source software application which is very efficient at managing this kind of workflow and process.

In the project you'll find the core module, clouder, which installs the clouder concepts in Odoo, and the template modules (like clouder_template_odoo) which installs data and functions specific to each application you want to host. Once you are familiar with Clouder, installing an application is as easy as filling in a form! (Which means you can automatate it with a form on your website).
And the best is, you don't need to research extensively if you want to provide hosting for a new app, just install the template module made by others and you're set.


Community
---------

You can find more information, support forum and mailing-list on https://goclouder.net/, you can find the documentation at http://doc.goclouder.net/.

If you need help for using or contributing to Clouder, you can easily contact us on our public chatroom : https://gitter.im/clouder-community/clouder

Development (including documentation) is done here on github, contributions are welcome; please read the CLA guidelines https://github.com/clouder-community/clouder/blob/8.0/doc/cla/sign-cla.md if you want to make a pull request. 
CLA is asked only to avoid possible legal issues in the future, like the OCA projects you keep your copyright but provide an irrevocable licence to the project maintener. If this happen in the future, you only give us the right to relicence under a licence recognized by the Open Source Initiative.

Clouder shall actually be considered in Beta, use it at your own risk and strong admin system skills are recommended. It shall only be used for development/testing/demo environment right now.

