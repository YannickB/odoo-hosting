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


class ClouderContainer(models.Model):
    """
    Add methods to manage the postfix specificities.
    """

    _inherit = 'clouder.container'

    @api.multi
    def deploy_post(self):
        """
        Add a ssmtp file if the container is linked to a postfix, and the
        configure the postfix.
        """
        super(ClouderContainer, self).deploy_post()

        for link in self.link_ids:
            if link.name.name.code == 'postfix' and link.target:
                self.execute(['echo "root=' + self.email_sysadmin +
                             '" > /etc/ssmtp/ssmtp.conf'])
                self.execute(['echo "mailhub=postfix:25" '
                             '>> /etc/ssmtp/ssmtp.conf'])
                self.execute(['echo "rewriteDomain=' + self.fullname +
                              '" >> /etc/ssmtp/ssmtp.conf'])
                self.execute(['echo "hostname=' + self.fullname +
                             '" >> /etc/ssmtp/ssmtp.conf'])
                self.execute(['echo "FromLineOverride=YES" >> '
                             '/etc/ssmtp/ssmtp.conf'])
        if self.application_id.type_id.name == 'postfix':
            self.execute([
                'echo "relayhost = ' + self.options['smtp_relayhost']['value']
                + '" >> /etc/postfix/main.cf'])
            self.execute([
                'echo "smtp_sasl_auth_enable = yes" >> /etc/postfix/main.cf'])
            self.execute([
                'echo "smtp_sasl_password_maps = '
                'hash:/etc/postfix/sasl_passwd" >> /etc/postfix/main.cf'])
            self.execute([
                'echo "smtp_sasl_security_options = noanonymous" '
                '>> /etc/postfix/main.cf'])
            self.execute(['echo "smtp_use_tls = yes" >> /etc/postfix/main.cf'])
            self.execute([
                'echo "mynetworks = 127.0.0.0/8 172.17.0.0/16" '
                '>> /etc/postfix/main.cf'])
            self.execute([
                'echo ' + self.options['smtp_relayhost']['value'] + ' ' +
                (self.options['smtp_username']['value'] or '') + ':' +
                (self.options['smtp_apikey']['value'] or '') +
                '" > /etc/postfix/sasl_passwd'])
            self.execute(['postmap /etc/postfix/sasl_passwd'])

            self.send(modules.get_module_path('clouder_template_postfix') +
                      '/res/openerp_mailgate.py',
                      '/bin/openerp_mailgate.py')

            self.execute(['chmod', '+x', '/bin/openerp_mailgate.py'])