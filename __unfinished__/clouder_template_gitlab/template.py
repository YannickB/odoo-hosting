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
import time
import erppeek


class ClouderContainer(models.Model):
    """
    Add methods to manage the postgres specificities.
    """

    _inherit = 'clouder.container'

    @api.multi
    def deploy_post(self):
        super(ClouderContainer, self).deploy_post()

        # install gitlab into git's home
        self.execute(["cd", "/home/git"], path="/home/git/", username="git")
        self.execute(["git", "clone", "https://gitlab.com/gitlab-org/gitlab-ce.git", "-b", "8-10-stable", "gitlab"], path="/home/git/", username="git")

        self.execute(["cd", "/home/git/gitlab"], path="/home/git/gitlab", username="git")
        # Copy the example GitLab config
        self.execute(["cp", "config/gitlab.yml.example", "config/gitlab.yml"], path="/home/git/gitlab", username="git")
        # change git location because we installed it manually
        self.execute(["sed", "-i", "'s/\/usr\/bin\/git/\/usr\/local\/bin\/git/g'", "config/gitlab.yml"], path="/home/git/gitlab", username="git")
        # Copy the example secrets file
        self.execute(["cp", "config/secrets.yml.example", "config/secrets.yml"], path="/home/git/gitlab", username="git")
        self.execute(["chmod", "0600", "config/secrets.yml"], path="/home/git/gitlab", username="git")
        # Make sure GitLab can write to the log/ and tmp/ directories
        self.execute(["chown", "-R", "git", "log/"], path="/home/git/gitlab", username="git")
        self.execute(["chown", "-R", "git", "tmp/"], path="/home/git/gitlab", username="git")
        self.execute(["chmod", "-R", "u+rwX,go-w", "log/"], path="/home/git/gitlab", username="git")
        self.execute(["chmod", "-R", "u+rwX", "tmp/"], path="/home/git/gitlab", username="git")
        # Make sure GitLab can write to the tmp/pids/ and tmp/sockets/ directories
        self.execute(["chmod", "-R", "u+rwX", "tmp/pids/"], path="/home/git/gitlab", username="git")
        self.execute(["chmod", "-R", "u+rwX", "tmp/sockets/"], path="/home/git/gitlab", username="git")
        # Create the public/uploads/ directory
        self.execute(["mkdir", "public/uploads/"], path="/home/git/gitlab", username="git")
        # Make sure only the GitLab user has access to the public/uploads/ directory
        # now that files in public/uploads are served by gitlab-workhorse
        self.execute(["chmod", "0700", "public/uploads"], path="/home/git/gitlab", username="git")
        # Change the permissions of the directory where CI build traces are stored
        self.execute(["chmod", "-R", "u+rwX", "builds/"], path="/home/git/gitlab", username="git")
        # Change the permissions of the directory where CI artifacts are stored
        self.execute(["chmod", "-R", "u+rwX", "shared/artifacts/"], path="/home/git/gitlab", username="git")
        # Copy the example Unicorn config
        self.execute(["cp", "config/unicorn.rb.example", "config/unicorn.rb"], path="/home/git/gitlab", username="git")
        # Set the number of workers to the number of cores
        self.execute(["sed", "-i", "'s/worker_processes 3/worker_processes `nproc`/g'", "config/unicorn.rb"], path="/home/git/gitlab", username="git")
        # Copy the example Rack attack config
        self.execute(["cp", "config/initializers/rack_attack.rb.example", "config/initializers/rack_attack.rb"], path="/home/git/gitlab", username="git")
        # Configure Git global settings for git user
        # 'autocrlf' is needed for the web editor
        self.execute(["git", "config", "--global", "core.autocrlf", "input"], path="/home/git/gitlab", username="git")
        # Disable 'git gc --auto' because GitLab already runs 'git gc' when needed
        self.execute(["git", "config", "--global", "gc.auto", "0"], path="/home/git/gitlab", username="git")
        # Configure Redis connection settings
        self.execute(["cp", "config/resque.yml.example", "config/resque.yml"], path="/home/git/gitlab", username="git")
        # Change the Redis socket path if you are not using the default Debian / Ubuntu configuration
        self.execute(["sed", "-i", "'s/localhost:6379/.../'", "config/resque.yml"], path="/home/git/gitlab", username="git")
        # Configure GitLab DB Settings
        self.execute(["cp", "config/database.yml.postgresql", "config/database.yml"], path="/home/git/gitlab", username="git")
        # Make config/database.yml readable to git only
        self.execute(["chmod", "o-rwx", "config/database.yml"], path="/home/git/gitlab", username="git")
        # Install Gems
        self.execute(["bundle", "install", "--deployment", "--without", "development", "test", "mysql", "aws", "kerberos"], path="/home/git/gitlab", username="git")
        # Instal Gitlab shell
        # the installation task for gitlab-shell (replace `REDIS_URL` if needed):
        self.execute(["bundle", "exec", "rake", "gitlab:shell:install", "REDIS_URL=unix:/var/run/redis/redis.sock", "RAILS_ENV=production"], path="/home/git/gitlab", username="git")
        # By default, the gitlab-shell config is generated from your main GitLab config.
        # You can review (and modify) the gitlab-shell config as follows:
        # self.execute(["editor", "/home/git/gitlab-shell/config.yml"], path="/home/git/gitlab", username="git")

        # Install gitlab-workhorse
        self.execute(["cd", "/home/git"], path="/home/git/", username="git")
        self.execute(["git", "clone", "https://gitlab.com/gitlab-org/gitlab-workhorse.git"], path="/home/git/", username="git")
        self.execute(["cd", "gitlab-workhorse"], path="/home/git/", username="git")
        self.execute(["git", "checkout", "v0.7.8"], path="/home/git/", username="git")
        self.execute(["make"], path="/home/git/", username="git")

        # Initialize Database and Activate Advanced Features
        # Go to GitLab installation folder
        self.execute(["cd", "/home/git/gitlab"], path="/home/git/gitlab", username="git")
        self.execute(["bundle", "exec", "rake", "gitlab:setup", "RAILS_ENV=production", "GITLAB_ROOT_PASSWORD=yourpassword", "GITLAB_ROOT_EMAIL=your@email.com"], path="/home/git/gitlab", username="git")
        # Install Init Script
        self.execute(["cp", "lib/support/init.d/gitlab", "/etc/init.d/gitlab"], path="/home/git/gitlab", username="git")
        # Start gitlab on boot
        self.execute(["update-rc.d", "gitlab", "defaults", "21"], path="/home/git/gitlab", username="git")
        # Setup Logrotate
        self.execute(["cp", "lib/support/logrotate/gitlab", "/etc/logrotate.d/gitlab"], path="/home/git/gitlab", username="git")
        # Check Application Status
        self.execute(["bundle", "exec", "rake", "gitlab:env:info", "RAILS_ENV=production"], path="/home/git/gitlab", username="git")
        # Compile Assets
        self.execute(["bundle", "exec", "rake", "assets:precompile", "RAILS_ENV=production"], path="/home/git/gitlab", username="git")

        # Finally Start Gitlab
        self.execute(["service", "gitlab", "start"], path="/home/git/gitlab", username="git")
