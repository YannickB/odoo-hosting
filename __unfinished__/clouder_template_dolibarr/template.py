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

from openerp import models, api, modules
import requests
import logging
# from bs4 import BeautifulSoup


class ClouderContainer(models.Model):
    """
    Add methods to manage the dolibarr specificities.
    """

    _inherit = 'clouder.container'

    @api.multi
    def deploy_post(self):
        super(ClouderContainer, self).deploy_post()

        if self.application_id.type_id.name == 'dolibarr':
            self.execute([
                'wget', '-q', 'http://www.dolibarr.org/files/dolibarr.tgz',
                'dolibarr.tgz'], path='/var/www/', username='www-data')
            self.execute(['tar', '-xzf', 'dolibarr.tgz'],
                         path='/var/www', username='www-data')
            self.execute(['rm', '-rf', './*.tgz'],
                         path='/var/www', username='www-data')
            self.execute(['mv', 'dolibarr-*/', 'dolibarr/'],
                         path='/var/www', username='www-data')
            self.execute(['touch', 'htdocs/conf/conf.php'],
                         path='/var/www/dolibarr', username='www-data')
            self.execute(['mkdir', 'documents'],
                         path='/var/www/dolibarr', username='www-data')


class ClouderBase(models.Model):
    """
    Add methods to manage the shinken specificities.
    """

    _inherit = 'clouder.base'

    @api.multi
    def deploy_build(self):
        """
        Configure nginx.
        """
        res = super(ClouderBase, self).deploy_build()
        if self.application_id.type_id.name == 'dolibarr':

            config_file = '/etc/nginx/sites-available/' + self.fullname
            self.container_id.send(
                modules.get_module_path('clouder_template_dolibarr') +
                '/res/nginx.config', config_file)
            self.container_id.execute(['sed', '-i',
                                       '"s/BASE/' + self.name + '/g"',
                                       config_file])
            self.container_id.execute([
                'sed', '-i',
                '"s/DOMAIN/' + self.domain_id.name + '/g"',
                config_file])
            self.container_id.execute([
                'ln', '-s',
                '/etc/nginx/sites-available/' + self.fullname,
                '/etc/nginx/sites-enabled/' + self.fullname])
            self.container_id.execute(['/etc/init.d/nginx', 'reload'])

        return res

    @api.multi
    def purge_post(self):
        """
        Purge from nginx configuration.
        """
        super(ClouderBase, self).purge_post()
        if self.application_id.type_id.name == 'dolibarr':
            self.container_id.execute([
                'rm', '-rf', '/etc/nginx/sites-enabled/' + self.fullname])
            self.container_id.execute([
                'rm', '-rf', '/etc/nginx/sites-available/' + self.fullname])
            self.container_id.execute(['/etc/init.d/nginx', 'reload'])
#
#     @api.multi
#     def deploy_post(self):
#         """
#         Update odoo configuration.
#         """
#         res = super(ClouderBase, self).deploy_post()
#         if self.application_id.type_id.name == 'mautic':
#             base_url = \
#                 "http://" + str(self.name) + "." + str(self.domain_id.name)
#             installer_url = "/index.php/installer/step/"
#             mysql_pswd = "5DJqJcT26FgMCqRa"
#             logging.info("-----------------")
#             logging.info(base_url + " " + installer_url + " " + mysql_pswd)
#             logging.info("-----------------")
#
#             # self.link_ids
#
#             port = str(80)
#
#             # logging.info(self.link_ids)
#
#             # logging.info("test connect to " +
#             #  baseUrl + ":" + port + installerUrl +
#             # " using db password " + mysql_pswd)
#
#             headers = dict()
#             headers["User-Agent"] = \
#                 "Mozilla/5.0 (Windows NT 10.0; WOW64; rv:47.0)" \
#                 " Gecko/20100101 Firefox/47.0"
#             headers["Accept"] = \
#                 "text/html,application/xhtml+xml," \
#                 "application/xml;q=0.9,*/*;q=0.8"
#             headers["Accept-Language"] = "
# fr,fr-FR;q=0.8,en-US;q=0.5,en;q=0.3"
#             headers["Connection"] = "keep-alive"
#             headers["Content-Type"] = "application/x-www-form-urlencoded"
#
#             # --- page 1 ---
#             # if mautic.status_code == 200:
#
#             # try:
#
#             mautic = requests.get(
#                 baseUrl + ":" + port + installerUrl + "1", headers=headers)
#
#             # except
#
#             """
#             pageParser = BeautifulSoup(mautic.text, 'html.parser')
#             form =
# pageParser.find_all(id=re.compile("install_doctrine_step_"))
#
#             arr = get_form(form)
#
#             arr["install_doctrine_step[name]"] = "mautic"
#             arr["install_doctrine_step[table_prefix]"] = "mautic"
#             arr["install_doctrine_step[user]"] = "root"
#             arr["install_doctrine_step[password]"] = mysql_pswd
#             arr["install_doctrine_step[host]"] = "mysql"
#
#             for i in arr:
#                 if arr[i] == "None":
#                     arr[i] = ""
#
#             #mautic = requests.post(baseUrl
# + ":" + port + installerUrl + "1",
#             data=arr, headers=headers)
#
#             # mautic = requests.post(baseUrl +
#             installerUrl + "1:" + port, data=arr)
#
#             # --- page 2 ---
#
#             #mautic = requests.get(baseUrl + ":" + port + installerUrl + "2",
#              headers=headers)
#
#             pageParser = BeautifulSoup(mautic.text, 'html.parser')
#             form =  pageParser.find_all(id=re.compile("install_user_step_"))
#
#             arr = get_form(form)
#             arr["install_user_step[firstname]"] = self.admin_name
#             arr["install_user_step[lastname]"] = self.admin_name
#             arr["install_user_step[email]"] = self.admin_email
#             arr["install_user_step[password]"] =
# self.container_id.db_password
#             arr["install_user_step[username]"] = "admin"
#
#             #logging.info("usernames will be " + self.admin_name + " and root
#             pswd is " + self.container_id.db_password + "
#             and admin email is " + self.admin_email)
#
#
#             #mautic = requests.post(baseUrl + installerUrl + "2",
#             data=arr, headers=headers)
#             # if mautic.headers.get("Location"):
#             # --- page 3 ---
#
#             #mautic = requests.get(baseUrl + installerUrl +
#             "3", headers=headers)
#
#             pageParser = BeautifulSoup(mautic.text, 'html.parser')
#             form = pageParser.find_all(id="install_email_step_")
#
#             arr = get_form(form)
#
#             #mautic = requests.post(baseUrl + installerUrl + "3",
#             data=arr, headers=headers)
#
#             #mautic = requests.get(baseUrl)
#
#
#     def get_form(form):
#         arr = dict()
#         for data in form:
#             if data.name == "input":
#                 if data.get("type") == "radio"
#                 and data.get("checked") == "checked":
#                     data_name = str(data.get("name"))
#                     data_value = str(data.get("value"))
#                 else:
#                     data_name = str(data.get("name"))
#                     data_value = str(data.get("value"))
#             elif data.name == "select":
#                 select = BeautifulSoup(data.prettify())
#                 data_name = str(data.get("name"))
#                 data_value = str(select.find('option',
#                 selected=True).get("value"))
#             else:
#                 continue
#             arr[data_name] = data_value
#         return arr
# """
