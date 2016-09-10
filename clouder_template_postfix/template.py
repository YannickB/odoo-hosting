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
            if link.name.code == 'postfix' and link.target:
                self.execute(['echo "root=' + self.email_sysadmin +
                             '" > /etc/ssmtp/ssmtp.conf'], username='root')
                self.execute(['echo "mailhub=postfix:25" '
                             '>> /etc/ssmtp/ssmtp.conf'], username='root')
                self.execute(['echo "rewriteDomain=' + self.fullname +
                              '" >> /etc/ssmtp/ssmtp.conf'], username='root')
                self.execute(['echo "hostname=' + self.fullname +
                             '" >> /etc/ssmtp/ssmtp.conf'], username='root')
                self.execute(['echo "FromLineOverride=YES" >> '
                             '/etc/ssmtp/ssmtp.conf'], username='root')
        if self.application_id.type_id.name == 'postfix' and self.application_id.check_tags(['exec']):

            # Adding boolean flag to see if all SMTP options are set
            smtp_options = False
            if self.options['smtp_relayhost']['value'] and \
                self.options['smtp_username']['value'] and \
                self.options['smtp_key']['value']:
                smtp_options = True

            if smtp_options:
                self.execute([
                    'sed', '-i',
                    '"/relayhost =/d" ' + '/etc/postfix/main.cf']),
                self.execute([
                    'echo "relayhost = ' + self.options['smtp_relayhost']['value']
                    + '" >> /etc/postfix/main.cf'])

            self.execute([
                'sed', '-i',
                '"/myorigin =/d" ' + '/etc/postfix/main.cf']),
            self.execute([
                'echo "myorigin = ' + self.server_id.name + 
                '" >> /etc/postfix/main.cf'])

            self.execute([
                'sed', '-i',
                '"/mynetworks =/d" ' + '/etc/postfix/main.cf']),
            self.execute([
                'echo "mynetworks = 127.0.0.0/8 172.17.0.0/16" '
                '>> /etc/postfix/main.cf'])
            self.execute([
                'echo "header_size_limit = 4096000" '
                '>> /etc/postfix/main.cf'])

            if smtp_options:
                self.execute([
                    'echo "smtp_sasl_auth_enable = yes" >> /etc/postfix/main.cf'])
                self.execute([
                    'echo "smtp_sasl_security_options = noanonymous" '
                    '>> /etc/postfix/main.cf'])
                self.execute(['echo "smtp_use_tls = yes" >> /etc/postfix/main.cf'])
                self.execute([
                    'echo "smtp_tls_security_level = encrypt" '
                    '>> /etc/postfix/main.cf'])
                self.execute([
                    'echo "smtp_sasl_password_maps = ' + 'static:' +
                    (self.options['smtp_username']['value'] or '') + ':' +
                    (self.options['smtp_key']['value'] or '') +
                    '" >> /etc/postfix/main.cf'])

            self.send(modules.get_module_path('clouder_template_postfix') +
                      '/res/openerp_mailgate.py',
                      '/bin/openerp_mailgate.py')

            self.execute(['chmod', '+x', '/bin/openerp_mailgate.py'])


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
        if self.name.type_id.name == 'spamassassin' \
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
        if self.name.type_id.name == 'spamassassin' \
                and self.container_id.application_id.type_id.name == 'postfix':

            self.container_id.execute([
                'sed', '-i',
                '"/#spamassassin-flag/,/#spamassassin-endflag/d"',
                '/etc/postfix/master.cf'])
            self.container_id.execute(
                ['/etc/init.d/postfix', 'reload'])


class ClouderBaseLink(models.Model):
    """
    Add methods to manage the shinken specificities.
    """

    _inherit = 'clouder.base.link'

    @api.multi
    def deploy_bind_postfix_config(self, dns_link, key, name):
        dns_link.purge_bind_config(name)
        dns_link.deploy_bind_config(name)
        base = self.base_id
        dns = dns_link.target
        dns.execute([
            'echo "' + name + ' IN MX 1 ' +
            base.name +
            ' ; mx:' + base.fulldomain + '" >> ' +
            base.domain_id.configfile])
        smtp_relayhost = ''
        if self.target.options['smtp_relayhost']['value']:
            smtp_relayhost = ' a:' + self.target.options['smtp_relayhost']['value'] + ' '
        dns.execute([
            'echo \'' + name + ' IN TXT "v=spf1 a mx ptr mx:' + base.fulldomain + ' ip4:10.0.0.0/8 ip4:127.0.0.0/8 ip4:' + self.target.server_id.ip + smtp_relayhost + ' ~all"\' >> ' + base.domain_id.configfile])
        dns.execute([
            'echo \'' + name + ' IN SPF "v=spf1 a mx ptr mx:' + base.fulldomain + ' ip4:10.0.0.0/8 ip4:127.0.0.0/8 ip4:' + self.target.server_id.ip + smtp_relayhost + ' ~all"\' >> ' + base.domain_id.configfile])
        dns.execute([
            'echo \'' + key.replace('(','').replace(')','').replace('"\n','').replace('"p','p').replace('\n','').replace('_domainkey','_domainkey.' + name) + '\' >> ' + base.domain_id.configfile])
        base.domain_id.refresh_serial()

    @api.multi
    def purge_bind_postfix_config(self, dns_link, name):
        dns_link.purge_bind_config(name)
        base = self.base_id
        dns = dns_link.target
        dns.execute([
            'sed', '-i',
            '"/mail._domainkey.' + name + '/d"',
        base.domain_id.configfile])
        dns.execute([
            'sed', '-i',
            '"/' + base.name + ' for ' + base.domain_id.name + '/d"',
            base.domain_id.configfile])
        dns.execute([
            'sed', '-i',
            '"/mx:' + base.fulldomain + '/d"',
            base.domain_id.configfile])
        base.domain_id.refresh_serial()


    @api.multi
    def deploy_link(self):
        """
        Deploy the configuration file to watch the base.
        """
        super(ClouderBaseLink, self).deploy_link()

        if self.name.type_id.name == 'postfix':
            dns_link = self.search([
                ('base_id', '=', self.base_id.id),
                ('name.type_id.name', '=', 'bind')])
            if dns_link and dns_link.target:
                base = self.base_id
                self.target.execute([
                    'mkdir -p /opt/opendkim/keys/' + base.fullname])
                self.target.execute([
                    'opendkim-genkey -D /opt/opendkim/keys/' + base.fullname + ' -r -d ' + base.fulldomain + ' -s mail'])
                self.target.execute([
                    'chown opendkim:opendkim /opt/opendkim/keys/' + base.fullname + '/mail.private'])
                self.target.execute([
                    'echo "' + 'mail._domainkey.' + base.fulldomain + ' ' + base.fulldomain+ ':mail:' + '/opt/opendkim/keys/'  + base.fullname + '/mail.private #' + base.fullname + '" >> /opt/opendkim/KeyTable'])

                self.target.execute([
                    'echo "' + base.fulldomain + ' mail._domainkey.' + base.fulldomain + ' #' + base.fullname + '" >> /opt/opendkim/SigningTable'])
                self.target.execute([
                    'echo "' + base.fulldomain + ' #' + base.fullname + '" >> /opt/opendkim/TrustedHosts'])

                self.target.execute(
                    ["pkill -9 -e 'opendkim'"])
                self.target.execute(
                    ['/etc/init.d/opendkim', 'start'])

                key = self.target.execute(['cat', '/opt/opendkim/keys/'  + base.fullname + '/mail.txt'])

                if self.base_id.is_root:
                    self.deploy_bind_postfix_config(dns_link, key, '@')
                self.deploy_bind_postfix_config(dns_link, key, self.base_id.name)

    @api.multi
    def purge_link(self):
        """
        Remove the configuration file.
        """
        super(ClouderBaseLink, self).purge_link()
        if self.name.type_id.name == 'postfix':
            dns_link = self.search([
                ('base_id', '=', self.base_id.id),
                ('name.type_id.name', '=', 'bind')])
            if dns_link and dns_link.target:
                base = self.base_id
                self.target.execute(['rm', '-rf', '/opt/opendkim/keys/' + base.fullname])
                self.target.execute(['sed', '-i', '"/#' + base.fullname + '/d" /opt/opendkim/KeyTable'])
                self.target.execute(['sed', '-i', '"/#' + base.fullname + '/d" /opt/opendkim/SigningTable'])
                self.target.execute(['sed', '-i', '"/#' + base.fullname + '/d" /opt/opendkim/TrustedHosts'])
                self.target.execute(
                    ["pkill -9 -e 'opendkim'"])
                self.target.execute(
                    ['/etc/init.d/opendkim', 'start'])

                if self.base_id.is_root:
                    self.purge_bind_postfix_config(dns_link, '@')
                self.purge_bind_postfix_config(dns_link, self.base_id.name)
