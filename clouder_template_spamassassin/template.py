# -*- coding: utf-8 -*-
##############################################################################
#
# Author: Yannick Buron
# Copyright 2015, TODAY Clouder SASU
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License with Attribution
# clause as published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License with
# Attribution clause along with this program. If not, see
# <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp import models, api
from openerp import modules


class ClouderContainerLink(models.Model):
    """
    Add methods to manage the spamassassin specificities.
    """

    _inherit = 'clouder.container.link'

    @api.multi
    def deploy_link(self):
        """
        Deploy the configuration file to watch the container.
        """
        super(ClouderContainerLink, self).deploy_link()
        if self.name.name.code == 'spamassassin' \
                and self.container_id.application_id.type_id.name == 'postfix':

            self.container_id.execute([
                "echo '#spamassassin-flag'"
                ">> /etc/postfix/master.cf"])
            self.container_id.execute([
                "echo 'smtp      inet  n       -       -       -       -       "
                "smtpd -o content_filter=spamassassin' "
                ">> /etc/postfix/master.cf"])
            self.container_id.execute([
                "echo 'spamassassin unix -     n       n       -       -       "
                "pipe user=nobody argv=/usr/bin/spamc -d " + self.target.server_id.ip + " -p " + self.target.ports['spamd']['hostport'] + " -f -e /usr/sbin/sendmail "
                "-oi -f \${sender} \${recipient}' "
                ">> /etc/postfix/master.cf"])
            self.container_id.execute([
                "echo '#spamassassin-endflag'"
                ">> /etc/postfix/master.cf"])

            self.container_id.execute(
                ['/etc/init.d/postfix', 'reload'])

    @api.multi
    def purge_link(self):
        """
        Remove the configuration file.
        """
        super(ClouderContainerLink, self).purge_link()
        if self.name.name.code == 'spamassassin' \
                and self.container_id.application_id.type_id.name == 'postfix':

            self.container_id.execute([
                'sed', '-i',
                '"/#spamassassin-flag/,/#spamassassin-endflag/d"',
                '/etc/postfix/master.cf'])
            self.container_id.execute(
                ['/etc/init.d/postfix', 'reload'])
