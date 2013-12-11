#!/bin/bash

website_path='/var/www/wikicompare_www'
ftpuser='sd-34468'
ftppass='#g00gle!'
ftpserver='dedibackup-dc3.online.net'

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
admin_user=$(drush vget wikicompare_admin_user --format=json --exact)
admin_user=${admin_user//[\"\\]/}
admin_password=$(drush vget wikicompare_admin_password --format=json --exact)
admin_password=${admin_password//[\"\\]/}
instance=$(drush vget wikicompare_instance --format=json --exact)
instance=${instance//[\"\\]/}
user_name=$admin_user
user_mail=$(drush vget wikicompare_email_wikiadmin --format=json --exact)
user_mail=${user_mail//[\"\\]/}
server=$(drush vget wikicompare_next_server --format=json --exact)
server=${server//[\"\\]/}
database_server=$(drush vget wikicompare_next_database_server --format=json --exact)
database_server=${database_server//[\"\\]/}
mysql_password=$(drush vget wikicompare_mysql_password --format=json --exact)
mysql_password=${mysql_password//[\"\\]/}
piwik_password=$(drush vget wikicompare_piwik_password --format=json --exact)
piwik_password=${piwik_password//[\"\\]/}
piwik_url=$(drush vget wikicompare_piwik_url --format=json --exact)
piwik_url=${piwik_url//[\"\\]/}
piwik_demo_id=$(drush vget wikicompare_piwik_demo_id --format=json --exact)
piwik_demo_id=${piwik_demo_id//[\"\\]/}
module_path=$(drush vget wikicompare_module_path --format=json --exact)
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

deploy()
{
echo deploying...

cd $website_path
node_id=$(drush sql-query "select title from node WHERE title = '$1' AND type = 'wikicompare' LIMIT 1")
echo $node_id
#result=$(drush /opt/drush.script $1 $3 $title $8 ${10})
if [[ $node_id != 'title' ]]
then
    echo The wikicompare $1 already exist
    exit
fi

node_id=$(drush sql-query "select nid from node WHERE title = '$server' AND type = 'wikicompare_server' LIMIT 1")
#result=$(drush /opt/drush.script $1 $3 $title $8 ${10})
echo $node_id
if [[ $node_id == 'nid' ]]
then
    echo The wikicompare server $server does not exist
    exit
fi

IP=$(drush sql-query "select wikicompare_ip_value from field_data_wikicompare_ip WHERE entity_id = ${node_id//[a-z ]/} LIMIT 1")
echo $IP
if [[ $IP == 'wikicompare_ip_value' ]]
then
    echo The wikicompare server $server has no IP.
    exit
fi

database_node_id=$(drush sql-query "select nid from node WHERE title = '$database_server' AND type = 'wikicompare_server' LIMIT 1")
#result=$(drush /opt/drush.script $1 $3 $title $8 ${10})
echo $database_node_id
if [[ $database_node_id == 'nid' ]]
then
    echo The wikicompare database server $database_server does not exist
    exit
fi

database_IP=$(drush sql-query "select wikicompare_ip_value from field_data_wikicompare_ip WHERE entity_id = ${database_node_id//[a-z ]/} LIMIT 1")
echo $database_IP
if [[ $database_IP == 'wikicompare_ip_value' ]]
then
    echo The wikicompare server $database_server has no IP.
    exit
fi

result=$(drush sql-query "SELECT n.nid, fd.wikicompare_bdd_value FROM node n INNER JOIN field_data_wikicompare_bdd fd ON n.nid=fd.entity_id INNER JOIN field_data_wikicompare_server f ON n.nid=f.entity_id WHERE n.title = '$instance' AND f.wikicompare_server_target_id = ${node_id//[a-z ]/} AND type = 'wikicompare_instance' LIMIT 1")
#result=$(drush /opt/drush.script $1 $3 $title $8 ${10})
echo $result
i=0
node_id=''
db_type=''
for row in $result
do
  if [[ $i == 2 ]]
  then
    node_id=$row
  elif [[ $i == 3 ]]
  then
    db_type=$row
  fi
  let i++
done
if [[ ! $db_type ]]
then
    echo The wikicompare instance $instance does not exist
    exit
fi
echo $db_type

bakery_master_site=$(drush vget bakery_master --format=json --exact)
bakery_master_site=${bakery_master_site//[\"\\]/}
bakery_private_key=$(drush vget bakery_key --format=json --exact)
bakery_private_key=${bakery_private_key//[\"\\]/}
bakery_cookie_domain=$(drush vget bakery_domain --format=json --exact)
bakery_cookie_domain=${bakery_cookie_domain//[\"\\]/}
IP=${IP//[^0-9.]/}
database_IP=${database_IP//[^0-9.]/}
db_name=wikicompare_$1
db_user=wkc_$1
domain_name=${1//_/-}
#IP=${IP//[a-z_\/n\/r ]/}

ssh -q www-data@$IP exit
echo $?
if [[ $? != 0 ]]
then
  echo Impossible to contact the instance server
  exit
fi

ssh -q www-data@${database_IP} exit
echo $?
if [[ $? != 0 ]]
then
  echo Impossible to contact the database server
  exit
fi

drush $module_path/wikicompare.script install $1 $admin_password $user_name $user_mail ${node_id//[a-z ]/} ${database_node_id//[a-z ]/}

echo Creating database wikicompare_$1 for user $db_user
#SI postgres, create user
echo $db_type
if [[ $db_type != 'mysql' ]]
then
ssh postgres@$database_IP << EOF
  psql
  CREATE USER $db_user WITH PASSWORD '$admin_password';
  CREATE DATABASE $db_name;
  ALTER DATABASE $db_name OWNER TO $db_user;
  \q
EOF

ssh www-data@$IP << EOF
  sed -i "/:$db_name:$db_user:/d" $pgpass_file
  sed -i "/:template1:$db_user:/d" $pgpass_file
  echo "$database_IP:5432:$db_name:$db_user:$admin_password" >> $pgpass_file
  echo "$database_IP:5432:template1:$db_user:$admin_password" >> $pgpass_file
EOF

else
ssh www-data@$database_IP << EOF
  mysql -u root -p$mysql_password -se "create database $db_name;"
  mysql -u root -p$mysql_password -se "grant all on $db_name.* to '${db_user}'@'${IP}' identified by '$admin_password';"
EOF
fi
echo Database created

version=''
if ssh www-data@$IP stat /var/www/$instance \> /dev/null 2\>\&1
then
  echo instance was installed
else
ssh www-data@$IP << EOF
  mkdir /var/www/$instance
  cd /var/www/$instance
  wget -q http://www.wikicompare.info/download/$archive/archive.tar.gz
  tar -xf archive.tar.gz -C /var/www/$instance
  rm archive.tar.gz
EOF
version=$(curl http://www.wikicompare.info/download/$archive/VERSION.txt)
echo version : $version
drush $module_path/wikicompare.script upgrade $instance $version
fi


if ssh www-data@$IP stat /var/www/$instance \> /dev/null 2\>\&1
then
  echo instance ok
else
  echo There was an error while creating the instance
  exit
fi



if [[ $build == True ]]
then
ssh www-data@$IP << EOF
cd /var/www/$instance
pwd
drush -y si --db-url=$db_type://${db_user}:$admin_password@$database_IP/$db_name --account-mail=$admin_email --account-name=$admin_user --account-pass=$admin_password --sites-subdir=$domain_name.wikicompare.info minimal
cd sites/$domain_name.wikicompare.info
pwd
drush -y en piwik admin_menu_toolbar bakery wikicompare wikicompare_profiles wikicompare_translation wikicompare_inherit_product
drush -y pm-enable wikicompare_theme
drush vset --yes --exact theme_default wikicompare_theme
drush vset --yes --exact bakery_master $bakery_master_site
drush vset --yes --exact bakery_key '$bakery_private_key'
drush vset --yes --exact bakery_domain $bakery_cookie_domain
EOF

else

if [[ $db_type != 'mysql' ]]
then
ssh www-data@$IP << EOF
pg_restore -U $db_user -h $database_IP --no-owner -Fc -d $db_name /var/www/$instance/$db_type/build.sql
EOF
else
ssh www-data@$database_IP << EOF
mysql -u $db_user -p$admin_password -h $database_IP $db_name < /var/www/$instance/$db_type/build.sql
EOF
fi

ssh www-data@$IP << EOF
mkdir /var/www/$instance/sites/$domain_name.wikicompare.info
cp -r /var/www/$instance/$db_type/sites/* /var/www/$instance/sites/$domain_name.wikicompare.info/
cd /var/www/$instance/sites/$domain_name.wikicompare.info
sed -i -e "s/'database' => 'wikicompare_[a-z0-9_]*'/'database' => 'wikicompare_$1'/g" /var/www/$instance/sites/$domain_name.wikicompare.info/settings.php
sed -i -e "s/'username' => 'wkc_[a-z0-9_]*'/'username' => 'wkc_$1'/g" /var/www/$instance/sites/$domain_name.wikicompare.info/settings.php
sed -i -e "s/'password' => '[#a-z0-9_!]*'/'password' => '$admin_password'/g" /var/www/$instance/sites/$domain_name.wikicompare.info/settings.php
sed -i -e "s/'host' => '[0-9.]*'/'host' => '$database_IP'/g" /var/www/$instance/sites/$domain_name.wikicompare.info/settings.php
pwd
echo Title $title
drush vset --yes --exact site_name $title
drush user-password $admin_user --password=$admin_password
EOF

if [[ $test == True ]]
then
ssh www-data@$IP << EOF
cd /var/www/$instance/sites/$domain_name.wikicompare.info
drush vset --yes --exact wikicompare_test_platform 1
EOF
fi


fi

ssh www-data@$IP << EOF
chown -R www-data:www-data /var/www/$instance
chmod -R 700 /var/www/$instance/sites/$domain_name.wikicompare.info/
EOF

if [[ $admin_user != $user_name ]]
then
ssh www-data@$IP << EOF
cd /var/www/$instance/sites/$domain_name.wikicompare.info
drush user-create $user_name --password="$user_password" --mail="$user_mail"
drush user-add-role wikicompare_admin $user_name
EOF
fi


echo Drupal ready

if [[ $skip_analytics != True ]]
then

if [[ $domain_name != 'demo' ]]
then
ssh $piwik_server << EOF
  mysql piwik -u piwik -p$piwik_password -se "INSERT INTO piwik_site (name, main_url, ts_created, timezone, currency) VALUES ('$domain_name.wikicompare.info', 'http://$domain_name.wikicompare.info', NOW(), 'Europe/Paris', 'EUR');"
EOF

piwik_id=$(mysql piwik -u piwik -p$piwik_password -se "select idsite from piwik_site WHERE name = '$domain_name.wikicompare.info' LIMIT 1")
ssh $piwik_server << EOF
  mysql piwik -u piwik -p$piwik_password -se "INSERT INTO piwik_access (login, idsite, access) VALUES ('anonymous', $piwik_id, 'view');"
EOF
else
piwik_id=$piwik_demo_id
fi

ssh www-data@$IP << EOF
cd /var/www/$instance/sites/$domain_name.wikicompare.info
drush variable-set piwik_site_id $piwik_id
drush variable-set piwik_url_http $piwik_url
drush variable-set piwik_privacy_donottrack 0
EOF

fi

escape='\$1'
ssh www-data@$IP << EOF
  echo "<VirtualHost *:80>" > /etc/apache2/sites-available/wikicompare_$1
  echo "ServerAdmin webmaster@localhost" >> /etc/apache2/sites-available/wikicompare_$1
  echo "ServerName $domain_name.wikicompare.info" >> /etc/apache2/sites-available/wikicompare_$1
  echo "DocumentRoot /var/www/$instance/" >> /etc/apache2/sites-available/wikicompare_$1
  echo "" >> /etc/apache2/sites-available/wikicompare_$1
  echo "<Directory />" >> /etc/apache2/sites-available/wikicompare_$1
  echo "Options FollowSymLinks" >> /etc/apache2/sites-available/wikicompare_$1
  echo "AllowOverride None" >> /etc/apache2/sites-available/wikicompare_$1
  echo "</Directory>" >> /etc/apache2/sites-available/wikicompare_$1
  echo "<Directory /var/www/$instance>" >> /etc/apache2/sites-available/wikicompare_$1
  echo "Options Indexes FollowSymLinks MultiViews" >> /etc/apache2/sites-available/wikicompare_$1
  echo "AllowOverride All" >> /etc/apache2/sites-available/wikicompare_$1
  echo "Order allow,deny" >> /etc/apache2/sites-available/wikicompare_$1
  echo "allow from all" >> /etc/apache2/sites-available/wikicompare_$1
  echo "RewriteEngine on" >> /etc/apache2/sites-available/wikicompare_$1
  echo "RewriteBase /" >> /etc/apache2/sites-available/wikicompare_$1
  echo "RewriteCond %{REQUEST_FILENAME} !-f" >> /etc/apache2/sites-available/wikicompare_$1
  echo "RewriteCond %{REQUEST_FILENAME} !-d" >> /etc/apache2/sites-available/wikicompare_$1
  echo "RewriteRule ^(.*)$ index.php?q=$escape [L,QSA]" >> /etc/apache2/sites-available/wikicompare_$1
  echo "</Directory>" >> /etc/apache2/sites-available/wikicompare_$1
  echo "ScriptAlias /cgi-bin/ /usr/lib/cgi-bin/" >> /etc/apache2/sites-available/wikicompare_$1
  echo '<Directory "/usr/lib/cgi-bin">' >> /etc/apache2/sites-available/wikicompare_$1
  echo "AllowOverride None" >> /etc/apache2/sites-available/wikicompare_$1
  echo "Options +ExecCGI -MultiViews +SymLinksIfOwnerMatch" >> /etc/apache2/sites-available/wikicompare_$1
  echo "Order allow,deny" >> /etc/apache2/sites-available/wikicompare_$1
  echo "Allow from all" >> /etc/apache2/sites-available/wikicompare_$1
  echo "</Directory>" >> /etc/apache2/sites-available/wikicompare_$1
  echo "ErrorLog /var/log/apache2/error.log" >> /etc/apache2/sites-available/wikicompare_$1
  echo "LogLevel warn" >> /etc/apache2/sites-available/wikicompare_$1
  echo "CustomLog /var/log/apache2/access.log combined" >> /etc/apache2/sites-available/wikicompare_$1
  echo 'Alias /doc/ "/usr/share/doc/"' >> /etc/apache2/sites-available/wikicompare_$1
  echo '<Directory "/usr/share/doc/">' >> /etc/apache2/sites-available/wikicompare_$1
  echo "Options Indexes MultiViews FollowSymLinks" >> /etc/apache2/sites-available/wikicompare_$1
  echo "AllowOverride None" >> /etc/apache2/sites-available/wikicompare_$1
  echo "Order deny,allow" >> /etc/apache2/sites-available/wikicompare_$1
  echo "Deny from all" >> /etc/apache2/sites-available/wikicompare_$1
  echo "Allow from 127.0.0.0/255.0.0.0 ::1/128" >> /etc/apache2/sites-available/wikicompare_$1
  echo "</Directory>" >> /etc/apache2/sites-available/wikicompare_$1
  echo "</VirtualHost>" >> /etc/apache2/sites-available/wikicompare_$1        
  sudo a2ensite wikicompare_$1
  sudo /etc/init.d/apache2 reload
EOF


ssh $dns_server << EOF
sed -i "/$1\sIN\sA/d" /etc/bind/db.wikicompare.info
echo "$domain_name IN A $IP" >> /etc/bind/db.wikicompare.info
sudo /etc/init.d/bind9 reload
EOF

directory=/var/wikicompare/control_backups/`date +%Y-%m-%d`_${instance}_${IP}
ssh $shinken_server << EOF
  echo "define service{" > /usr/local/shinken/etc/services/wikicompare_$1.cfg
  echo "service_description    HTTP $1" >> /usr/local/shinken/etc/services/wikicompare_$1.cfg
  echo "use            wikicompare-linux-service" >> /usr/local/shinken/etc/services/wikicompare_$1.cfg
  echo "register       0" >> /usr/local/shinken/etc/services/wikicompare_$1.cfg
  echo "host_name      wikicompare-linux-server" >> /usr/local/shinken/etc/services/wikicompare_$1.cfg
  echo "check_command  wikicompare_check_http!$domain_name.wikicompare.info" >> /usr/local/shinken/etc/services/wikicompare_$1.cfg
  echo "}" >> /usr/local/shinken/etc/services/wikicompare_$1.cfg
  echo "" >> /usr/local/shinken/etc/services/wikicompare_$1.cfg
  echo "define service{" >> /usr/local/shinken/etc/services/wikicompare_$1.cfg
  echo "service_description    Backup $1" >> /usr/local/shinken/etc/services/wikicompare_$1.cfg
  echo "use            wikicompare-linux-service" >> /usr/local/shinken/etc/services/wikicompare_$1.cfg
  echo "register       0" >> /usr/local/shinken/etc/services/wikicompare_$1.cfg
  echo "host_name      wikicompare-linux-server" >> /usr/local/shinken/etc/services/wikicompare_$1.cfg
  echo "check_interval 60" >> /usr/local/shinken/etc/services/wikicompare_$1.cfg
  echo "retry_interval 15" >> /usr/local/shinken/etc/services/wikicompare_$1.cfg
  echo "check_period period_backup" >> /usr/local/shinken/etc/services/wikicompare_$1.cfg
  echo "check_command  wikicompare_check_backup!$1" >> /usr/local/shinken/etc/services/wikicompare_$1.cfg
  echo "}" >> /usr/local/shinken/etc/services/wikicompare_$1.cfg
  /etc/init.d/shinken reload
EOF

if ssh $shinken_server stat $directory \> /dev/null 2\>\&1
then
  echo Shinken save already set
else
ssh $shinken_server << EOF
  mkdir $directory
  mkdir $directory/$instance
  echo 'lorem ipsum' > $directory/$instance/lorem.txt
EOF
fi

ssh $shinken_server << EOF
echo 'lorem ipsum' > $directory/wikicompare_$1.sql
EOF

cd $website_path
drush $module_path/wikicompare.script finish $1 $admin_user $admin_password


}


upgrade()
{
pear upgrade drush/drush

cd $website_path
result_wikicompare=$(drush sql-query "select n.title, fn.title, fndni.wikicompare_ip_value from node n 
INNER JOIN field_data_wikicompare_instance f ON n.nid=f.entity_id 
INNER JOIN node fn ON f.wikicompare_instance_target_id = fn.nid
INNER JOIN field_data_wikicompare_server fnd ON fn.nid=fnd.entity_id
INNER JOIN node fndn ON fnd.wikicompare_server_target_id = fndn.nid
INNER JOIN field_data_wikicompare_ip fndni ON fndn.nid=fndni.entity_id 
WHERE fn.title = '$1' AND fndn.title = '$2'  LIMIT 1")
i=0
wikicompare_name=''
instance_name=''
IP=''
for row_wikicompare in $result_wikicompare
do
  if [[ $i == 3 ]]
  then
    wikicompare_name=$row_wikicompare
  elif [[ $i == 4 ]]
  then
    instance_name=$row_wikicompare
  elif [[ $i == 5 ]]
  then
    IP=$row_wikicompare
  fi
  let i++
done
IP=${IP//[^0-9.]/}
echo wikicompare_name $wikicompare_name
echo instance_name $instance_name
echo ip $IP


if ssh www-data@$IP stat /var/www/$1 \> /dev/null 2\>\&1
then
  echo ok
else
  echo "No $1 instance, no upgrade"
  return
fi

ssh www-data@$IP << EOF
mkdir /var/www/$1/../sites_${1}_temp
cp -r /var/www/$1/sites/* /var/www/$1/../sites_${1}_temp
EOF

if [[ $wikicompare_name != '' ]]
then
domain_name=${wikicompare_name//_/-}

filename=`date +%Y-%m-%d_%H-%M`_upgrade_${1}_`date +%H-%M`.tar.gz
ssh www-data@$IP << EOF
cd /var/www/$1/sites/$domain_name.wikicompare.info
drush archive-dump @sites --destination=/var/wikicompare/backups/prepare/$filename
EOF
scp www-data@$IP:/var/wikicompare/backups/prepare/$filename /var/wikicompare/backups/$filename
ssh www-data@$IP << EOF
rm /var/wikicompare/backups/prepare/$filename
EOF
ncftp -u  $ftpuser -p $ftppass $ftpserver<< EOF
put /var/wikicompare/backups/$filename
EOF
fi


ssh www-data@$IP << EOF
rm -rf /var/www/$1/*
cd /var/www/$1
wget -q http://www.wikicompare.info/download/$archive/archive.tar.gz
tar -xf archive.tar.gz -C /var/www/$1
rm archive.tar.gz
rm -rf /var/www/$1/sites/*
cp -r /var/www/$1/../sites_${1}_temp/* /var/www/$1/sites/
rm -rf /var/www/$1/../sites_${1}_temp
EOF

ssh www-data@$IP << EOF
cd /var/www/$1/sites/
find . -name '*.wikicompare.info' -exec bash -c 'cd /var/www/$1/sites/{}; drush updatedb' \;
EOF

cd $website_path
version=$(curl http://www.wikicompare.info/download/$archive/VERSION.txt)
drush $module_path/wikicompare.script upgrade $1 $version

}




purge()
{

domain_name=${1//_/-}

cd $website_path
result_wikicompare=$(drush sql-query "select n.title, fn.title, fnb.wikicompare_bdd_value, fndni.wikicompare_ip_value, fndni.wikicompare_ip_value from node n
INNER JOIN field_data_wikicompare_instance f ON n.nid=f.entity_id 
INNER JOIN node fn ON f.wikicompare_instance_target_id = fn.nid 
INNER JOIN field_data_wikicompare_bdd fnb ON fn.nid=fnb.entity_id
INNER JOIN field_data_wikicompare_server fnd ON fn.nid=fnd.entity_id
INNER JOIN node fndn ON fnd.wikicompare_server_target_id = fndn.nid
INNER JOIN field_data_wikicompare_ip fndni ON fndn.nid=fndni.entity_id 
INNER JOIN field_data_wikicompare_bdd_server fd ON n.nid=fd.entity_id
INNER JOIN node fdn ON fd.wikicompare_bdd_server_target_id = fdn.nid
INNER JOIN field_data_wikicompare_ip fdni ON fdn.nid=fdni.entity_id 
WHERE n.title = '$1'  LIMIT 1")
i=0
wikicompare_name=''
instance_name=''
IP=''
database_IP=''
echo $result_wikicompare
for row_wikicompare in $result_wikicompare
do
  if [[ $i == 5 ]]
  then
    wikicompare_name=$row_wikicompare
  elif [[ $i == 6 ]]
  then
    instance_name=$row_wikicompare
  elif [[ $i == 7 ]]
  then
    db_type=$row_wikicompare    
  elif [[ $i == 8 ]]
  then
    IP=$row_wikicompare   
  elif [[ $i == 9 ]]
  then
    database_IP=$row_wikicompare   
  fi
  let i++
done
IP=${IP//[^0-9.]/}
database_IP=${database_IP//[^0-9.]/}
echo wikicompare_name $wikicompare_name
echo instance_name $instance_name
echo db_type $db_type
echo IP $IP
echo database_IP $database_IP

drush $module_path/wikicompare.script prepare_purge $1

ssh $shinken_server << EOF
rm /usr/local/shinken/etc/services/wikicompare_$1.cfg 
/etc/init.d/shinken reload
EOF

ssh $dns_server << EOF
sed -i "/$domain_name\sIN\sA/d" /etc/bind/db.wikicompare.info
sudo /etc/init.d/bind9 reload
EOF

db_name=wikicompare_$1
db_user=wkc_$1
if [[ $db_type != 'mysql' ]]
then
ssh postgres@$database_IP << EOF
  psql
  DROP DATABASE $db_name;
  DROP USER $db_user;
  \q
EOF

ssh www-data@$IP << EOF
sed -i "/:$db_name:$db_user:/d" $pgpass_file
sed -i "/:template1:$db_user:/d" $pgpass_file
EOF

else
ssh www-data@$database_IP << EOF
  mysql -u root -p$mysql_password -se "drop database $db_name;"
  mysql -u root -p$mysql_password -se "drop user '$db_user'@'${IP}';"
EOF
fi

ssh www-data@$IP << EOF
sudo a2dissite wikicompare_$1
rm /etc/apache2/sites-available/wikicompare_$1
sudo /etc/init.d/apache2 reload
EOF


if [[ $domain_name != 'demo' ]]
then

#TODO This part is not crossplatform because recover the variable will be difficult. When we will move piwik, consider open the post mysql to www server ip so we can continue query it directly.
#ssh $piwik_server << EOF
piwik_id=$(mysql piwik -u piwik -p$piwik_password -se "select idsite from piwik_site WHERE name = '$domain_name.wikicompare.info' LIMIT 1")
#EOF
echo piwik_id $piwik_id
fi

if [[ $piwik_id != '' ]]
then
ssh $piwik_server << EOF
  mysql piwik -u piwik -p$piwik_password -se "UPDATE piwik_site SET name = 'droped_$piwik_id'  WHERE idsite = $piwik_id;"
  mysql piwik -u piwik -p$piwik_password -se "DELETE FROM piwik_access WHERE idsite = $piwik_id;"
EOF
fi


echo $instance_name
if [[ $instance_name != '' ]]
then
ssh www-data@$IP << EOF
rm -rf /var/www/$instance_name/sites/$domain_name.wikicompare.info
EOF
fi

echo avant script
cd $website_path
drush $module_path/wikicompare.script purge $1
echo apres script
}


save()
{

if [[ $1 ]]
then

    cd $website_path
    result_wikicompare=$(drush sql-query "select n.title, fn.title, fndni.wikicompare_ip_value from node n
    INNER JOIN field_data_wikicompare_instance f ON n.nid=f.entity_id 
    INNER JOIN node fn ON f.wikicompare_instance_target_id = fn.nid
    INNER JOIN field_data_wikicompare_server fnd ON fn.nid=fnd.entity_id
    INNER JOIN node fndn ON fnd.wikicompare_server_target_id = fndn.nid
    INNER JOIN field_data_wikicompare_ip fndni ON fndn.nid=fndni.entity_id 
    WHERE n.title = '$1'  LIMIT 1")
    i=0
    wikicompare_name=''
    instance_name=''
    for row_wikicompare in $result_wikicompare
    do
      echo $i
      echo $row_wikicompare
      if [[ $i == 3 ]]
      then
        wikicompare_name=$row_wikicompare
      elif [[ $i == 4 ]]
      then
        instance_name=$row_wikicompare
      elif [[ $i == 5 ]]
      then
        IP=$row_wikicompare
      fi
      let i++
    done
    IP=${IP//[^0-9.]/}
    echo wikicompare_name $wikicompare_name
    echo instance $instance_name
    echo IP $IP

    domain_name=${wikicompare_name//_/-}
    filename=`date +%Y-%m-%d_%H-%M`_manual_${wikicompare_name}_`date +%H-%M`.tar.gz
ssh www-data@$IP << EOF
cd /var/www/$instance_name/sites/$domain_name.wikicompare.info
drush archive-dump $domain_name.wikicompare.info --destination=/var/wikicompare/backups/prepare/$filename
EOF
scp www-data@$IP:/var/wikicompare/backups/prepare/$filename /var/wikicompare/backups/$filename
ssh www-data@$IP << EOF
rm /var/wikicompare/backups/prepare/$filename
EOF

ncftp -u  $ftpuser -p $ftppass $ftpserver<< EOF
    put /var/wikicompare/backups/$filename
EOF


else

ssh $shinken_server << EOF
rm -rf /var/wikicompare/control_backups/*
EOF


cd $website_path
filename=`date +%Y-%m-%d`_wikicompare_www.tar.gz
rm /var/wikicompare/backups/$filename
drush archive-dump --destination=/var/wikicompare/backups/$filename
ncftp -u  $ftpuser -p $ftppass $ftpserver<< EOF
rm $filename
put /var/wikicompare/backups/$filename
EOF
echo website saved

filename=`date +%Y-%m-%d`_wikicompare_analytics.tar.gz
rm /var/wikicompare/backups/$filename
ssh $piwik_server << EOF
mkdir /var/wikicompare/backups/prepare/piwik_temp
mkdir /var/wikicompare/backups/prepare/piwik_temp/wikicompare_analytics
cp -r /var/www/piwik/* /var/wikicompare/backups/prepare/piwik_temp/wikicompare_analytics
mysqldump -u piwik -p$piwik_password piwik > /var/wikicompare/backups/prepare/piwik_temp/wikicompare_analytics.sql
cd /var/wikicompare/backups/prepare/piwik_temp
tar -czf ../$filename ./*
cd ../
rm -rf /var/wikicompare/backups/prepare/piwik_temp
EOF

scp $piwik_server:/var/wikicompare/backups/prepare/$filename /var/wikicompare/backups/$filename
ssh $piwik_server << EOF
rm /var/wikicompare/backups/prepare/$filename
EOF
ncftp -u  $ftpuser -p $ftppass $ftpserver<< EOF
rm $filename
put /var/wikicompare/backups/$filename

EOF
echo piwik saved

cd $website_path
result=$(drush sql-query "select nid from node WHERE type = 'wikicompare_instance'")
first=True

echo $result
for row in $result
do
  if [[ $first != True ]]
  then
    echo $row
    cd $website_path
    result_wikicompare=$(drush sql-query "select n.title, fn.title, fndni.wikicompare_ip_value from node n 
    INNER JOIN field_data_wikicompare_instance f ON n.nid=f.entity_id 
    INNER JOIN node fn ON f.wikicompare_instance_target_id = fn.nid 
    INNER JOIN field_data_wikicompare_server fnd ON fn.nid=fnd.entity_id
    INNER JOIN node fndn ON fnd.wikicompare_server_target_id = fndn.nid
    INNER JOIN field_data_wikicompare_ip fndni ON fndn.nid=fndni.entity_id
    WHERE f.wikicompare_instance_target_id=$row")
    i=1
    sites='default'
    entete=True
    wikicompare_name=''
    instance_name=''
    echo $result_wikicompare
    for row_wikicompare in $result_wikicompare
    do
      if [ $i == 1 ] && [ $entete == False ]
      then
        wikicompare_name=$row_wikicompare
        row_domain=${row_wikicompare//_/-}
        sites=$sites,$row_domain.wikicompare.info
      elif [ $i == 2 ] && [ $entete == False ]
      then
        instance_name=$row_wikicompare
      elif [ $i == 3 ] && [ $entete == False ]
      then
        IP=$row_wikicompare
      fi
      if [ $i == 3 ]
      then
        i=0
        entete=False
      fi
      let i++
    done
    IP=${IP//[^0-9.]/}
    echo wikicompare_name $wikicompare_name
    echo instance_name $instance_name
    echo IP $IP
    echo sites $sites

    if [[ $wikicompare_name != '' ]]
    then
      domain_name=${wikicompare_name//_/-}
      filename=`date +%Y-%m-%d`_${instance_name}_${IP}.tar.gz
      rm /var/wikicompare/backups/$filename
ssh www-data@$IP << EOF
      cd /var/www/$instance_name/sites/$domain_name.wikicompare.info
      echo ${instance_name}_`date +%Y-%m-%d`.tar.bz2
      drush archive-dump $sites --destination=/var/wikicompare/backups/prepare/$filename
EOF
scp www-data@$IP:/var/wikicompare/backups/prepare/$filename /var/wikicompare/backups/$filename
ssh www-data@$IP << EOF
rm /var/wikicompare/backups/prepare/$filename
EOF
ncftp -u  $ftpuser -p $ftppass $ftpserver<< EOF
      rm $filename
      put /var/wikicompare/backups/$filename
EOF
    fi

  else
    first=False
  fi

done

filename=`date +%Y-%m-%d -d '5 days ago'`_*
echo $filename
ncftp -u $ftpuser -p $ftppass $ftpserver<<EOF
rm $filename
EOF

ssh $shinken_server << EOF
ncftpget -u $ftpuser -p$ftppass -R $ftpserver /var/wikicompare/control_backups ./*
cd /var/wikicompare/control_backups
pwd
find . -name '*.tar.gz' -exec bash -c 'mkdir \`basename {} .tar.gz\`; tar -zxf {} -C \`basename {} .tar.gz\`' \;
rm *.tar.gz
EOF

find /var/wikicompare/backups/ -type f -mtime +4 | xargs -r rm


fi

}


control_backup()
{

    if [[ $2 ]]
    then
      instance_name=$2
      directory=/var/wikicompare/control_backups/`date +%Y-%m-%d`_${instance_name}
    else
    cd $website_path
    result_wikicompare=$(drush sql-query "select n.title, fn.title, fndni.wikicompare_ip_value from node n 
    INNER JOIN field_data_wikicompare_instance f ON n.nid=f.entity_id 
    INNER JOIN node fn ON f.wikicompare_instance_target_id = fn.nid
    INNER JOIN field_data_wikicompare_server fnd ON fn.nid=fnd.entity_id
    INNER JOIN node fndn ON fnd.wikicompare_server_target_id = fndn.nid
    INNER JOIN field_data_wikicompare_ip fndni ON fndn.nid=fndni.entity_id
    WHERE n.title = '$1'  LIMIT 1")
    i=0
    wikicompare_name=''
    instance_name=''
    for row_wikicompare in $result_wikicompare
    do
      if [[ $i == 3 ]]
      then
        wikicompare_name=$row_wikicompare
      elif [[ $i == 4 ]]
      then
        instance_name=$row_wikicompare
      elif [[ $i == 5 ]]
      then
        IP=$row_wikicompare
      fi
      let i++
    done
    IP=${IP//[^0-9.]/}
    directory=/var/wikicompare/control_backups/`date +%Y-%m-%d`_${instance_name}_${IP}
    fi
    
    if [[ ! $instance_name ]]
    then
      echo "L'instance n'a pas pu etre determine."
      exit 2
    fi    
    
        

    if [[ ! -d "$directory" ]]
    then
      echo "No backup of $1 today."
      exit 2
    fi

    cd $directory
    
    if [[ ! "$(ls -A $instance_name)" ]]
    then
      echo "The instance directory $instance_name is empty."
      exit 2
    fi

    if [[ ! (-s "${1/_/-}.wikicompare.info-wikicompare_${1}.sql" || -s "wikicompare_${1}.sql")  ]]
    then
      echo "The database file wikicompare_${wikicompare_name}.sql is empty."
      exit 2
    fi

    echo "Backup of ${wikicompare_name} OK"
    exit 0


}


build()
{

test=True

rm -rf $archive_path/wikicompare_${1}/*
cd $archive_path/wikicompare_${1}
drush make $module_path/wikicompare_${1}.make archive

patch -p0 -d $archive_path/wikicompare_${1}/archive/sites/all/modules/revisioning/ < $module_path/patch/revisioning_postgres.patch

if [[ $1 == 'dev' ]]
then
patch -p0 -d $archive_path/wikicompare_${1}/archive/sites/all/themes/wikicompare_theme/ < $module_path/patch/dev_zen_rebuild_registry.patch
fi

cd archive/
tar -czf ../archive.tar.gz ./* 
cd ../
echo 'temp' > VERSION.txt
chown -R www-data $archive_path/wikicompare_${1}/*

purge $1 /var/www/wikicompare_${1}
purge ${1}_my /var/www/wikicompare_${1}
rm -rf /var/www/wikicompare_${1}
rm -rf /var/www/wikicompare_${1}_mysql
build=True
skip_analytics=True
instance=wikicompare_${1}
archive=wikicompare_${1}

db_type='pgsql'
deploy $1
mkdir $archive_path/wikicompare_${1}/pgsql
mkdir $archive_path/wikicompare_${1}/pgsql/sites
cp -r /var/www/$instance/sites/${1}.wikicompare.info/* $archive_path/wikicompare_${1}/pgsql/sites/
echo Before pgdump
pg_dump -U wkc_${1} -h 88.190.33.202 -Fc --no-owner wikicompare_${1} > $archive_path/wikicompare_${1}/pgsql/build.sql
echo end pgdump
cp -R $archive_path/wikicompare_${1}/pgsql $archive_path/wikicompare_${1}/archive/
mkdir /var/www/$instance/pgsql
cp -R $archive_path/wikicompare_${1}/pgsql/* /var/www/$instance/pgsql/

db_type='mysql'
instance=wikicompare_${1}_mysql
deploy ${1}_my
mkdir $archive_path/wikicompare_${1}/mysql
mkdir $archive_path/wikicompare_${1}/mysql/sites
cp -r /var/www/$instance/sites/${1}-my.wikicompare.info/* $archive_path/wikicompare_${1}/mysql/sites/
echo before mysqldump
mysqldump -u root -p$mysql_password wikicompare_${1}_my > $archive_path/wikicompare_${1}/mysql/build.sql
echo end mysqldump
cp -R $archive_path/wikicompare_${1}/mysql $archive_path/wikicompare_${1}/archive/
mkdir /var/www/$instance/mysql
cp -R $archive_path/wikicompare_${1}/mysql/* /var/www/$instance/mysql/

cd /var/www/wikicompare_${1}/sites/${1}.wikicompare.info
version=$(drush status | grep 'Drupal version')
version=${version//[^0-9.]/}
version=$version.`date +%Y%m%d`
cd $website_path
drush vset --yes --exact wikicompare_${1}_version $version
drush $module_path/wikicompare.script upgrade wikicompare_${1} $version
echo $version > $archive_path/wikicompare_${1}/VERSION.txt
cp $archive_path/wikicompare_${1}/VERSION.txt $archive_path/wikicompare_${1}/archive/

cd $archive_path/wikicompare_${1}/
rm archive.tar.gz
cd archive/
tar -czf ../archive.tar.gz ./* 
cd ../
rm -rf archive
chown -R www-data $archive_path/wikicompare_${1}/*

echo 'Deploying demo data'
cd /var/www/wikicompare_${1}/sites/${1}.wikicompare.info
drush -y en wikicompare_generate_demo
drush $module_path/wikicompare.script deploy_demo
if [[ $1 == 'dev' ]]
then
drush -y en devel
fi
drush user-create wikiadmin --password="g00gle" --mail="wikicompare@yopmail.com"
drush user-add-role wikicompare_admin wikiadmin

echo 'Deploying mysql demo data'
cd /var/www/wikicompare_${1}_mysql/sites/${1}-my.wikicompare.info
drush -y en wikicompare_generate_demo
drush $module_path/wikicompare.script deploy_demo
if [[ $1 == 'dev' ]]
then
drush -y en devel
fi
drush user-create wikiadmin --password="g00gle" --mail="wikicompare@yopmail.com"
drush user-add-role wikicompare_admin wikiadmin

echo Build finished!

}


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
   command_line   $module_path/wikicompare.sh control_backup $ARG1$ $ARG2$
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

wikicompare_name=${2/-/_}

case $1 in
   deploy)
       if [[ -z "$2" ]]
       then 
         cat 'You need to specify the name of the wikicompare.'
         exit
       fi    
       deploy $wikicompare_name
       exit
       ;;
   upgrade)
       if [[ -z "$3" ]]
       then 
         cat 'You need to specify the server name.'
         exit
       fi 
       upgrade $instance $3
       exit
       ;;       
   purge)
       if [[ -z "$2" ]]
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
       if [[ -z "$2" ]]
       then
         cat 'You need to specify the name of the wikicompare.'
         exit
       fi
       control_backup $wikicompare_name $3
       exit
       ;;
   build)
       if [[ -z "$2" ]]
       then
         cat 'You need to specify the instance to rebuild.'
         exit
       fi
       build $2
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
       drush -y en wikicompare_generate_demo
       drush $module_path/wikicompare.script deploy_demo
       drush user-create wikiadmin --password="g00gle" --mail="wikicompare@yopmail.com"
       drush user-add-role wikicompare_admin wikiadmin

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



