# -*- coding: utf-8 -*-
# #############################################################################
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


class ClouderContainer(models.Model):
    _inherit = 'clouder.container'

    @api.multi
    def deploy_post(self):
        super(ClouderContainer, self).deploy_post()
        if self.application_id.type_id.name == 'postfix':
            ssh, sftp = self.connect(self.fullname())
            self.execute(ssh, [
                'echo "relayhost = [smtp.mandrillapp.com]" '
                '>> /etc/postfix/main.cf'])
            self.execute(ssh, [
                'echo "smtp_sasl_auth_enable = yes" >> /etc/postfix/main.cf'])
            self.execute(ssh, [
                'echo "smtp_sasl_password_maps = '
                'hash:/etc/postfix/sasl_passwd" >> /etc/postfix/main.cf'])
            self.execute(ssh, [
                'echo "smtp_sasl_security_options = noanonymous" '
                '>> /etc/postfix/main.cf'])
            self.execute(ssh,
                         ['echo "smtp_use_tls = yes" >> /etc/postfix/main.cf'])
            self.execute(ssh, [
                'echo "mynetworks = 127.0.0.0/8 172.17.0.0/16" '
                '>> /etc/postfix/main.cf'])
            self.execute(ssh, [
                'echo "[smtp.mandrillapp.com]    ' +
                self.options()['mailchimp_username']['value'] + ':' +
                self.options()['mailchimp_apikey']['value'] +
                '" > /etc/postfix/sasl_passwd'])
            self.execute(ssh, ['postmap /etc/postfix/sasl_passwd'])
            ssh.close(), sftp.close()