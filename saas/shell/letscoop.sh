#!/bin/bash

letscoop_type=$1
website_path=/var/www/${letscoop_type}_www
domain='wikicompare.info'
if [[ $letscoop_type == 'wezer' ]]
then
domain='wezer.org'
fi
ftpuser='sd-34468'
ftppass='#g00gle!'
ftpserver='dedibackup-dc3.online.net'
openerp_superpassword='#g00gle!'
openerp_password='admin'

cd $website_path

title='TEST'
build=False
test=False;
skip_analytics=False
db_type='pgsql'
pgpass_file='/var/www/.pgpass'
admin_email='yannick.buron@gmail.com'
archive_path='/var/www/wikicompare_www/download'
archive='wikicompare_release'
admin_user=$(drush vget letscoop_admin_user --format=json --exact)
admin_user=${admin_user//[\"\\]/}
admin_password=$(drush vget letscoop_admin_password --format=json --exact)
admin_password=${admin_password//[\"\\]/}
instance=$(drush vget letscoop_instance --format=json --exact)
instance=${instance//[\"\\]/}
user_name=$admin_user
user_mail=$(drush vget letscoop_email_wikiadmin --format=json --exact)
user_mail=${user_mail//[\"\\]/}
server=$(drush vget letscoop_next_server --format=json --exact)
server=${server//[\"\\]/}
database_server=$(drush vget letscoop_next_database_server --format=json --exact)
database_server=${database_server//[\"\\]/}
mysql_password=$(drush vget letscoop_mysql_password --format=json --exact)
mysql_password=${mysql_password//[\"\\]/}
piwik_password=$(drush vget letscoop_piwik_password --format=json --exact)
piwik_password=${piwik_password//[\"\\]/}
piwik_url=$(drush vget letscoop_piwik_url --format=json --exact)
piwik_url=${piwik_url//[\"\\]/}
piwik_demo_id=$(drush vget letscoop_piwik_demo_id --format=json --exact)
piwik_demo_id=${piwik_demo_id//[\"\\]/}
module_path=$(drush vget letscoop_module_path --format=json --exact)
module_path=${module_path//[\"\\]/}

shinken_server=shinken@shinken.wikicompare.info
piwik_server=www-data@analytics.wikicompare.info
dns_server=bind@dns.wikicompare.info

usage()
{
cat << EOF
usage: $0 options

This script run the test1 or test2 over a machine.

OPTIONS:
   -h      Show this message
   -t      Test type, can be ‘test1' or ‘test2'
   -r      Server address
   -p      Server root password
   -v      Verbose
EOF
}


while getopts "ht:p:a:n:c:u:s:e:r:d:bkz" OPTION;
do
     case $OPTION in
         h)
             usage
             exit 1
             ;;
         t)
             title=$OPTARG
             ;;
         a)
             admin_user=$OPTARG
             ;;
         p)
             admin_password=$OPTARG
             ;;
         n)
             instance=$OPTARG
             ;;
         c)
             archive_path=$OPTARG
             ;;
         u)
             user_name=$OPTARG
             ;;
         s)
             user_password=$OPTARG
             ;;
         e)
             user_mail=$OPTARG
             ;;
         r)
             server=$OPTARG
             ;;
         d)
             database_server=$OPTARG
             ;;
         k)
             skip_analytics=True
             ;;
         b)
             build=True
             archive='wikicompare_preprod'
             ;;
         z)
             test=True
             ;;
         ?)
             usage
             exit
             ;;
     esac
done

#echo $title $admin_user $admin_password $instance $archive_path $archive_build_path $user_name $user_password $user_mail $server $make_file $piwik_url







prepare-server()
{
apt-get install php-pear
pear channel-discover pear.drush.org
pear install drush/drush

apt-get install nagios-nrpe-server
apt-get install nagios-plugins
#Modifier /etc/nagios/nrpe.cfg
#allowed_hosts = Mettre ici l'adresse IP de votre serveur Nagios
chkconfig --add nrpe
/etc/init.d/nagios-nrpe-server start

scp /usr/local/shinken/libexec/check_mem.pl /usr/lib/nagios/plugins/check_mem.pl

cat >>/etc/nagios/nrpe.cfg << EOF
command[check_load]=/usr/lib/nagios/plugins/check_load -w 15,10,5 -c 30,25,20
command[check_mem]=/usr/lib/nagios/plugins/check_mem.pl -fC -w 20 -c 10
command[check_disk]=/usr/lib/nagios/plugins/check_disk -w 20% -c 10% -p /
EOF

#On main server
cat >/usr/local/shinken/etc/hosts/server1.cfg << EOF
  define host{
      use             wikicompare-linux-server
      host_name       server1
      address         server1.wikicompare.info
  }


EOF

touch /var/www/.pgpass
chown www-data /var/www/.pgpass
chmod 600 /var/www/.pgpass

#As posgres
createuser www-data --createdb --createrole --no-superuser -W
$password

cat >> /var/www/.pgpass <<EOF
#localhost:5432:*:www-data:$password
EOF


#Postgres server conf
/etc/postgresql/9.1/main/pg_hba.conf
host    all             all             $IPs_servers/24        md5
/etc/postgresql/9.1/main/postgres.conf
listen_addresses = '$IPs_servers' 

}



prepare-main-server()
{

cd /var/www/
wget http://builds.piwik.org/latest.zip
unzip latest.zip
rm latest.zip
chown -R www-data piwik

cat >/etc/apache2/sites-available/analytics << EOF
<VirtualHost *:80>
        ServerAdmin webmaster@localhost
        ServerName analytics.wikicompare.info
        DocumentRoot /var/www/piwik/

        <Directory />
                Options FollowSymLinks
                AllowOverride None
        </Directory>
        <Directory /var/www/piwik>

                Options Indexes FollowSymLinks MultiViews
                AllowOverride All
                Order allow,deny
                allow from all

                RewriteEngine on
                RewriteBase /
                RewriteCond %{REQUEST_FILENAME} !-f
                RewriteCond %{REQUEST_FILENAME} !-d
                RewriteRule ^(.*)$ index.php?q=\$1 [L,QSA]
        </Directory>

        ScriptAlias /cgi-bin/ /usr/lib/cgi-bin/
        <Directory "/usr/lib/cgi-bin">
                AllowOverride None
                Options +ExecCGI -MultiViews +SymLinksIfOwnerMatch
                Order allow,deny
                Allow from all
        </Directory>

        ErrorLog /var/log/apache2/error.log

        # Possible values include: debug, info, notice, warn, error, crit,
        # alert, emerg.
        LogLevel warn

        CustomLog /var/log/apache2/access.log combined

    Alias /doc/ "/usr/share/doc/"
    <Directory "/usr/share/doc/">
        Options Indexes MultiViews FollowSymLinks
        AllowOverride None
        Order deny,allow
        Deny from all
        Allow from 127.0.0.0/255.0.0.0 ::1/128
    </Directory>

</VirtualHost>
EOF


a2ensite analytics
/etc/init.d/apache2 reload


#Lancer l'installation de piwik
#Activer la visibilité des tableaux de bord pour les anonymous



#http://documentation.online.net/fr/serveur-dedie/tutoriel/bind
apt-get install bind9
cat >>/etc/bind/named.conf << EOF
zone "wikicompare.info" {
        type master;
        allow-transfer {213.186.33.199;};
        file "/etc/bind/db.wikicompare.info";
        notify yes;
};
EOF

cat >/etc/bind/db.wikicompare.info << EOF
$TTL 3h
@       IN      SOA     ns.wikicompare.info. hostmaster.wikicompare.info. (
                                20130793001
                                8H
                                2H
                                1W
                                1D )
@       IN      NS      ns.wikicompare.info.
ns              IN      A       88.190.33.202
www             IN      A       88.190.33.202
mail            IN      A       88.190.33.202
analytics       IN      A       88.190.33.202
EOF
/etc/init.d/bind9 reload 





#Install shinken
curl -L http://install.shinken-monitoring.org | /bin/bash


cat >>/usr/local/shinken/etc/contactgroups.cfg << EOF

define contactgroup{
    contactgroup_name   wikicompare-admins
    alias               wikicompare-admins
    members             yannick
}
EOF

cat >>/usr/local/shinken/etc/contacts.cfg << EOF


define contact{
    use             generic-contact
    contact_name    yannick
    email           yannick.buron@gmail.com
    pager           0670745226
    password        #g00gle!
    is_admin        1
}
EOF



cat >/usr/local/shinken/etc/hosts/wikicompare.cfg << EOF

define host{
   name                         wikicompare-linux-server
   use                          generic-host
   check_command                check_host_alive
   register                     0
   contact_groups               wikicompare-admins

}

define host{
        use                     wikicompare-linux-server
        host_name               localhost
        address                 localhost
        }


EOF


apt-get install nagios-nrpe-plugin

cat >/usr/local/shinken/etc/services/wikicompare.cfg << EOF

define timeperiod{
        timeperiod_name                 period_backup
        alias                           Backup
        sunday                          08:00-23:00
        monday                          08:00-23:00
        tuesday                         08:00-23:00
        wednesday                       08:00-23:00
        thursday                        08:00-23:00
        friday                          08:00-23:00
        saturday                        08:00-23:00
}


define command {
   command_name   wikicompare_check_nrpe
   command_line   /usr/lib/nagios/plugins/check_nrpe -H $HOSTADDRESS$ -c $ARG1$  -a $ARG2$
}

define command {
   command_name   wikicompare_check_ssh
   command_line   $USER1$/check_ssh -H $HOSTADDRESS$
}

define command {
   command_name   wikicompare_check_http
   command_line   $USER1$/check_http -H $ARG1$
}

define command {
   command_name   wikicompare_check_backup
   command_line   /opt/openerp/openerp-infra/saas/saas/shell/control_backup.sh $ARG1$ $ARG2$ $ARG3$ $ARG4$ $ARG5$
}


define service{
  name                          wikicompare-linux-service
  use                           generic-service
  register                      0
  aggregation                   system
}

define service{
   service_description    HTTP Website
   use            wikicompare-linux-service
   register       0
   host_name      wikicompare-linux-server
   check_command  wikicompare_check_http!www.wikicompare.info
}

define service{
   service_description    Load
   use            wikicompare-linux-service
   register       0
   host_name      wikicompare-linux-server
   check_command  wikicompare_check_nrpe!check_load
}

define service{
   service_description    Memory
   use            wikicompare-linux-service
   register       0
   host_name      wikicompare-linux-server
   check_command  wikicompare_check_nrpe!check_mem
}

define service{
   service_description    Disk
   use            wikicompare-linux-service
   register       0
   host_name      wikicompare-linux-server
   check_command  wikicompare_check_nrpe!check_disk
}

define service{
   service_description    SSH
   use            wikicompare-linux-service
   register       0
   host_name      wikicompare-linux-server
   check_command  wikicompare_check_ssh
}

define service{
   service_description    HTTP Analytics
   use            wikicompare-linux-service
   register       0
   host_name      wikicompare-linux-server
   check_command  wikicompare_check_http!analytics.wikicompare.info
}

define service{
   service_description    Backup WEBSITE
   use            wikicompare-linux-service
   register       0
   host_name      wikicompare-linux-server
   check_interval 60
   retry_interval 15
   check_period period_backup
   check_command  wikicompare_check_backup!www!wikicompare_www
}

define service{
   service_description    Backup ANALYTICS
   use            wikicompare-linux-service
   register       0
   host_name      wikicompare-linux-server
   check_interval 60
   retry_interval 15
   check_period period_backup
   check_command  wikicompare_check_backup!analytics!wikicompare_analytics
}

EOF


cat >/etc/sudoers << EOF
www-data ALL = NOPASSWD: /etc/init.d/apache2 reload
www-data ALL = NOPASSWD: /etc/init.d/bind9 reload
www-data ALL = NOPASSWD: /etc/init.d/shinken reload
www-data ALL = NOPASSWD: /usr/sbin/a2ensite
www-data ALL = NOPASSWD: /usr/sbin/a2dissite
www-data ALL=(postgres) NOPASSWD: /usr/bin/psql

#We need to make a crontab because www-data can't restart shinken, even with sudo
cat >/etc/crontab << EOF
0 1 * * * root $module_path/wikicompare.sh save
EOF

usermod -a -G bind www-data
usermod -a -G shinken www-data

chmod -R 774 /etc/apache2/sites-available
chown -R root:www-data /etc/apache2/sites-available

chmod 774 /etc/bind/db.wikicompare.info
sudo chmod 775 /etc/bind


#psql --username www-data --host=localhost --dbname=wikicompare_build
#as postgres
createuser www-data -P --no-superuser --no-createrole --no-createdb


#Shinken doit avoir accès à la bdd du site wiki_www via son pgpass pour faire les check de backup

#AS www-data
ssh-keygen -t rsa #sans passphrase
mkdir -p SHINKENHOME/.ssh
cat .ssh/id_rsa.pub | cat >> SHINKENHOME/.ssh/authorized_keys

usermod -d /home/shinken shinken
chsh shinken /bin/sh
#Remove welcome message, to not polluate log in this script
touch /home/shinken/.hushlogin

}




n=1                                                                                       
while [ $# -gt 0 ]; do                                                                    
        if [ $n -lt $OPTIND ]; then  
		# remove (shift) option arguments
		# until they are all gone                                                     
                let n=$n+1                                                                
                shift                                                                     
        else                                                                              
                break;                                                                    
        fi                                                                                
done  

wikicompare_name=${3/-/_}

case $2 in
   deploy)
       if [[ -z "$3" ]]
       then 
         cat 'You need to specify the name of the wikicompare.'
         exit
       fi    
       deploy $wikicompare_name
       exit
       ;;
   upgrade)
       if [[ -z "$4" ]]
       then 
         cat 'You need to specify the server name.'
         exit
       fi 
       upgrade $instance $4
       exit
       ;;       
   purge)
       if [[ -z "$3" ]]
       then 
         cat 'You need to specify the name of the wikicompare.'
         exit
       fi  
       purge $wikicompare_name $instance
       ;;
   save)
       save $wikicompare_name
       exit
       ;;
   control_backup)
       if [[ -z "$3" ]]
       then
         cat 'You need to specify the name of the wikicompare.'
         exit
       fi
       control_backup $wikicompare_name $4
       exit
       ;;
   build)
       if [[ -z "$3" ]]
       then
         cat 'You need to specify the instance to rebuild.'
         exit
       fi
       build $3
       exit
       ;;
   populate)
       if [[ ! -s "$archive_path/$archive/VERSION.txt" ]]
       then
         version=$(cat $archive_path/$archive/VERSION.txt)
         rm -rf $archive_path/old_releases/$version
         mkdir $archive_path/old_releases/$version
         cp -r $archive_path/$archive/* $archive_path/old_releases/$version/
       fi
       rm -rf $archive_path/$archive/*
       cp -r $archive_path/wikicompare_preprod/* $archive_path/$archive

       echo 'Upgrading ' $instance '...'
       upgrade $instance $server

       echo 'Refresh demo...'
       title='Demo'
       purge demo $instance
       deploy demo

       echo 'Installing demo data...'
       cd /var/www/$instance/sites/demo.wikicompare.info
       drush user-create wikiadmin --password="g00gle" --mail="wikicompare@yopmail.com"
       drush user-add-role wikicompare_admin wikiadmin
       drush -y en wikicompare_generate_demo
       drush $module_path/wikicompare.script --user=wikiadmin deploy_demo

       version=$(cat $archive_path/wikicompare_preprod/VERSION.txt)
       cd $website_path
       drush vset --yes --exact wikicompare_release_version $version
       echo 'populate finished'
       exit
       ;;
   prepare-server)
       ;;
   prepare-main-server)
       ;;
   ?)
       usage
       exit
       ;;
esac



