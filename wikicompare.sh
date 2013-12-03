#!/bin/bash

website_path='/var/www/wikicompare_www'
ftpuser='sd-34468'
ftppass='#g00gle!'
ftpserver='dedibackup-dc3.online.net'

cd $website_path

title=''
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
mysql_password=$(drush vget wikicompare_mysql_password --format=json --exact)
mysql_password=${mysql_password//[\"\\]/}
piwik_password=$(drush vget wikicompare_piwik_password --format=json --exact)
piwik_password=${piwik_password//[\"\\]/}
piwik_url=$(drush vget wikicompare_piwik_url --format=json --exact)
piwik_url=${piwik_url//[\"\\]/}
module_path=$(drush vget wikicompare_module_path --format=json --exact)
module_path=${module_path//[\"\\]/}


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


while getopts "ht:p:a:n:c:u:s:e:d:bkz" OPTION;
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
         d)
             server=$OPTARG
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
db_name=wikicompare_$1
db_user=wkc_$1
domain_name=${1//_/-}
#IP=${IP//[a-z_\/n\/r ]/}
drush $module_path/wikicompare.script install $1 $admin_password $user_name $user_mail ${node_id//[a-z ]/} $db_type

echo Creating database wikicompare_$1 for user $db_user
#SI postgres, create user
echo $db_type
if [[ $db_type != 'mysql' ]]
then
sudo -u postgres psql <<EOF
CREATE USER $db_user WITH PASSWORD '$admin_password';
CREATE DATABASE $db_name;
ALTER DATABASE $db_name OWNER TO $db_user;
EOF


sed -i "/:$db_name:$db_user:/d" $pgpass_file
sed -i "/:template1:$db_user:/d" $pgpass_file
cat >>$pgpass_file << EOF
127.0.0.1:5432:$db_name:$db_user:$admin_password
127.0.0.1:5432:template1:$db_user:$admin_password
EOF

else
mysql -u root -p$mysql_password << EOF
create database $db_name;
grant all on $db_name.* to "${db_user}"@'localhost' identified by "$admin_password";
EOF
fi
echo Database created

if [ ! -d "/var/www/$instance" ]; then
  mkdir /var/www/$instance
  tar -xf $archive_path/$archive/archive.tar.gz -C /var/www/$instance
  version=$(cat $archive_path/$archive/VERSION.txt)
  drush $module_path/wikicompare.script upgrade $instance $version
fi

if [ ! -d "/var/www/$instance" ]; then
  echo There is an error while creating the instance
  exit
fi

echo Instance ok

if [[ $build == True ]]
then

#drush -y si  --db-url=pgsql://wiki_build@127.0.0.1/wikicompare_build
cd /var/www/$instance
pwd
drush -y si --db-url=$db_type://${db_user}:$admin_password@127.0.0.1/$db_name --account-mail=$admin_email --account-name=$admin_user --account-pass=$admin_password --sites-subdir=$domain_name.wikicompare.info minimal
cd sites/$domain_name.wikicompare.info
pwd
drush -y en piwik admin_menu_toolbar bakery wikicompare wikicompare_profiles wikicompare_translation wikicompare_inherit_product
drush -y pm-enable wikicompare_theme
drush vset --yes --exact theme_default wikicompare_theme

drush vset --yes --exact bakery_master $bakery_master_site
drush vset --yes --exact bakery_key $bakery_private_key
drush vset --yes --exact bakery_domain $bakery_cookie_domain
#drush vset --yes --exact site_frontpage 'compare'
#drush cc all


else

mkdir /var/www/$instance/sites/$domain_name.wikicompare.info
if [[ $db_type != 'mysql' ]]
then
pg_restore -U $db_user -h 127.0.0.1 -Fc -d $db_name /var/www/$instance/$db_type/build.sql
else
mysql -u $db_user -p$admin_password $db_name < /var/www/$instance/$db_type/build.sql
fi
cp -r /var/www/$instance/$db_type/sites/* /var/www/$instance/sites/$domain_name.wikicompare.info/

cd /var/www/$instance/sites/$domain_name.wikicompare.info
sed -i -e "s/'database' => 'wikicompare_[a-z0-9_]*'/'database' => 'wikicompare_$1'/g" /var/www/$instance/sites/$domain_name.wikicompare.info/settings.php
sed -i -e "s/'username' => 'wkc_[a-z0-9_]*'/'username' => 'wkc_$1'/g" /var/www/$instance/sites/$domain_name.wikicompare.info/settings.php
sed -i -e "s/'password' => '[#a-z0-9_!]*'/'password' => '$admin_password'/g" /var/www/$instance/sites/$domain_name.wikicompare.info/settings.php
drush vset --yes --exact site_name $title
drush user-password $admin_user --password=$admin_password

if [[ $test == True ]]
then
drush vset --yes --exact wikicompare_test_platform 1
fi


fi
chown -R www-data:www-data /var/www/$instance
chmod -R 700 /var/www/$instance/sites/$domain_name.wikicompare.info/
echo Drupal ready

if [[ $admin_user != $user_name ]]
then
drush user-create $user_name --password="$user_password" --mail="$user_mail"
drush user-add-role wikicompare_admin $user_name
fi

if [[ $skip_analytics != True ]]
then

if [[ domain_name != 'demo' ]]
then
mysql -u piwik -p$piwik_password piwik<< EOF
INSERT INTO piwik_site (name, main_url, ts_created, timezone, currency) VALUES ('$domain_name.wikicompare.info', 'http://$domain_name.wikicompare.info', NOW(), 'Europe/Paris', 'EUR');
EOF
piwik_id=$(mysql piwik -u piwik -p$piwik_password -se "select idsite from piwik_site WHERE name = '$domain_name.wikicompare.info' LIMIT 1")
mysql -u piwik -p$piwik_password piwik<< EOF
INSERT INTO piwik_access (login, idsite, access) VALUES ('anonymous', $piwik_id, 'view');
EOF
else
piwik_id=$(drush vget wikicompare_piwik_demo_id --format=json --exact)
piwik_id=${piwik_id//[\"\\]/}
fi

drush variable-set piwik_site_id $piwik_id
drush variable-set piwik_url_http $piwik_url
drush variable-set piwik_privacy_donottrack 0

fi


cat >/etc/apache2/sites-available/wikicompare_$1 << EOF
<VirtualHost *:80>
        ServerAdmin webmaster@localhost
        ServerName $domain_name.wikicompare.info
        DocumentRoot /var/www/$instance/

        <Directory />
                Options FollowSymLinks
                AllowOverride None
        </Directory>
        <Directory /var/www/$instance>

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
sudo a2ensite wikicompare_$1
sudo /etc/init.d/apache2 reload


sed -i "/$1\sIN\sA/d" /etc/bind/db.wikicompare.info
cat >>/etc/bind/db.wikicompare.info << EOF
$domain_name IN A $IP
EOF
sudo /etc/init.d/bind9 reload

cat >/usr/local/shinken/etc/services/wikicompare_$1.cfg << EOF
define service{
   service_description    HTTP $1
   use            wikicompare-linux-service
   register       0
   host_name      wikicompare-linux-server
   check_command  wikicompare_check_http!$domain_name.wikicompare.info
}

define service{
   service_description    Backup $1
   use            wikicompare-linux-service
   register       0
   host_name      wikicompare-linux-server
   check_interval 60
   retry_interval 15
   check_period period_backup
   check_command  wikicompare_check_backup!$1
}

EOF
ssh shinken@www.wikicompare.info /etc/init.d/shinken reload

directory=/var/wikicompare/control_backups/`date +%Y-%m-%d`_${instance}    

if [[ ! -d "$directory" ]]
then
  mkdir $directory
  mkdir $directory/$instance
  echo 'lorem ipsum' > $directory/$instance/lorem.txt
fi

echo 'lorem ipsum' > $directory/wikicompare_$1.sql
chown -R www-data:shinken /var/wikicompare/control_backups
chmod -R 755 /var/wikicompare/control_backups

cd $website_path
drush $module_path/wikicompare.script finish $1 $admin_user $admin_password


}


upgrade()
{
pear upgrade drush/drush

if [[ ! -d /var/www/$1 ]]
then
  echo "No $1 instance, no upgrade"
  return
fi

mkdir /var/www/$1/../sites_${1}_temp
cp -r /var/www/$1/sites/* /var/www/$1/../sites_${1}_temp


cd $website_path
result_wikicompare=$(drush sql-query "select n.title, fn.title from node n INNER JOIN field_data_wikicompare_instance f ON n.nid=f.entity_id INNER JOIN node fn ON f.wikicompare_instance_target_id = fn.nid WHERE fn.title = '$1'  LIMIT 1")
i=0
wikicompare_name=''
instance_name=''
for row_wikicompare in $result_wikicompare
do
  if [[ $i == 2 ]]
  then
    wikicompare_name=$row_wikicompare
  elif [[ $i == 3 ]]
  then
    instance_name=$row_wikicompare
  fi
  let i++
done

if [[ $wikicompare_name != '' ]]
then
domain_name=${wikicompare_name//_/-}
cd /var/www/$1/sites/$domain_name.wikicompare.info

filename=`date +%Y-%m-%d_%H-%M`_upgrade_${1}_`date +%H-%M`.tar.gz
drush archive-dump @sites --destination=/var/wikicompare/backups/$filename

ncftp -u  $ftpuser -p $ftppass $ftpserver<< EOF
    put /var/wikicompare/backups/$filename
EOF
fi

rm -rf /var/www/$1/*

tar -xf $archive_path/$archive/archive.tar.gz -C /var/www/$1

rm -rf /var/www/$1/sites/*

cp -r /var/www/$1/../sites_${1}_temp/* /var/www/$1/sites/

rm -rf /var/www/$1/../sites_${1}_temp

for DIR in /var/www/$1/sites/*;
do
  if [ -d "$DIR" ]; then 
    if [[ $DIR != /var/www/$1/sites/all && $DIR != /var/www/$1/sites/default ]]
      then
      echo $DIR
      cd $DIR
      drush updatedb
    fi
  fi
done

cd $website_path
version=$(cat $archive_path/$archive/VERSION.txt)
drush $module_path/wikicompare.script upgrade $1 $version

}




purge()
{

domain_name=${1//_/-}

cd $website_path
result_wikicompare=$(drush sql-query "select n.title, fn.title, fnd.wikicompare_bdd_value from node n INNER JOIN field_data_wikicompare_instance f ON n.nid=f.entity_id INNER JOIN node fn ON f.wikicompare_instance_target_id = fn.nid INNER JOIN field_data_wikicompare_bdd fnd ON fn.nid=fnd.entity_id  WHERE n.title = '$1'  LIMIT 1")
i=0
wikicompare_name=''
instance_name=''
echo $result_wikicompare
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
    db_type=$row_wikicompare    
  fi
  let i++
done



drush $module_path/wikicompare.script prepare_purge $1

rm /usr/local/shinken/etc/services/wikicompare_$1.cfg 
ssh shinken@www.wikicompare.info /etc/init.d/shinken reload

sed -i "/$domain_name\sIN\sA/d" /etc/bind/db.wikicompare.info
sudo /etc/init.d/bind9 reload

db_name=wikicompare_$1
db_user=wkc_$1
if [[ $db_type != 'mysql' ]]
then
sudo -u postgres psql <<EOF
DROP DATABASE $db_name;
DROP USER $db_user;
EOF

sed -i "/:$db_name:$db_user:/d" $pgpass_file
sed -i "/:template1:$db_user:/d" $pgpass_file

else
mysql -u root -p$mysql_password << EOF
drop database $db_name;
drop user '$db_user'@'localhost';
EOF
fi

sudo a2dissite wikicompare_$1
rm /etc/apache2/sites-available/wikicompare_$1
sudo /etc/init.d/apache2 reload

if [[ domain_name != 'demo' ]]
then
piwik_id=$(mysql piwik -u piwik -p$piwik_password -se "select idsite from piwik_site WHERE name = '$domain_name.wikicompare.info' LIMIT 1")
echo $piwik_id
if [[ $piwik_id != '' ]]
then
mysql -u piwik -p$piwik_password piwik<< EOF
UPDATE piwik_site SET name = 'droped_$piwik_id'  WHERE idsite = $piwik_id;
DELETE FROM piwik_access WHERE idsite = $piwik_id;
EOF
fi
fi


echo $instance_name
if [[ $instance_name != '' ]]
then
rm -rf /var/www/$instance_name/sites/$domain_name.wikicompare.info
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
    result_wikicompare=$(drush sql-query "select n.title, fn.title from node n INNER JOIN field_data_wikicompare_instance f ON n.nid=f.entity_id INNER JOIN node fn ON f.wikicompare_instance_target_id = fn.nid WHERE n.title = '$1'  LIMIT 1")
    i=0
    wikicompare_name=''
    instance_name=''
    for row_wikicompare in $result_wikicompare
    do
      echo $i
      echo $row_wikicompare
      if [[ $i == 2 ]]
      then
        wikicompare_name=$row_wikicompare
      elif [[ $i == 3 ]]
      then
        instance_name=$row_wikicompare
      fi
      let i++
    done
    echo $wikicompare_name
    echo $instance_name
    domain_name=${wikicompare_name//_/-}
    cd /var/www/$instance_name/sites/$domain_name.wikicompare.info
    filename=`date +%Y-%m-%d_%H-%M`_manual_${wikicompare_name}_`date +%H-%M`.tar.gz
    drush archive-dump $domain_name.wikicompare.info --destination=/var/wikicompare/backups/$filename

    ncftp -u  $ftpuser -p $ftppass $ftpserver<< EOF
    put /var/wikicompare/backups/$filename
EOF


else




rm -rf /var/wikicompare/control_backups/*


cd $website_path
filename=`date +%Y-%m-%d`_wikicompare_www.tar.gz
rm /var/wikicompare/backups/$filename
drush archive-dump --destination=/var/wikicompare/backups/$filename
ncftp -u  $ftpuser -p $ftppass $ftpserver<< EOF
rm $filename
put /var/wikicompare/backups/$filename
EOF
echo website saved

rm -rf /var/wikicompare/backups/piwik_temp
mkdir /var/wikicompare/backups/piwik_temp
mkdir /var/wikicompare/backups/piwik_temp/wikicompare_analytics
cp -r /var/www/piwik/* /var/wikicompare/backups/piwik_temp/wikicompare_analytics
mysqldump -u piwik -p$piwik_password piwik > /var/wikicompare/backups/piwik_temp/wikicompare_analytics.sql
filename=`date +%Y-%m-%d`_wikicompare_analytics.tar.gz
rm /var/wikicompare/backups/$filename
cd /var/wikicompare/backups/piwik_temp
tar -czf ../$filename ./*
cd ../
rm -rf /var/wikicompare/backups/piwik_temp
ncftp -u  $ftpuser -p $ftppass $ftpserver<< EOF
rm $filename
put /var/wikicompare/backups/$filename
EOF
echo piwik saved

cd $website_path
result=$(drush sql-query "select nid from node WHERE type = 'wikicompare_instance'")
first=True

for row in $result
do
  if [[ $first != True ]]
  then
    echo $row
    cd $website_path
    result_wikicompare=$(drush sql-query "select n.title, fn.title from node n INNER JOIN field_data_wikicompare_instance f ON n.nid=f.entity_id INNER JOIN node fn ON f.wikicompare_instance_target_id = fn.nid WHERE f.wikicompare_instance_target_id=$row")
    i=0
    sites='default'
    even=''
    wikicompare_name=''
    instance_name=''
    for row_wikicompare in $result_wikicompare
    do
      echo $i
      echo $row_wikicompare
      if [[ $even == 'even' ]]
      then
        wikicompare_name=$row_wikicompare
        row_domain=${row_wikicompare//_/-}
        sites=$sites,$row_domain.wikicompare.info
        even='odd'
      elif [[ $even == 'odd' ]]
      then
        instance_name=$row_wikicompare
        even='even'
      fi
      if [[ $i == 1 ]]
      then
        even='even'
      fi
      let i++
    done
    echo $wikicompare_name
    echo $instance_name
    echo $sites

    if [[ $wikicompare_name != '' ]]
    then
      domain_name=${wikicompare_name//_/-}
      cd /var/www/$instance_name/sites/$domain_name.wikicompare.info
      echo ${instance_name}_`date +%Y-%m-%d`.tar.bz2
      filename=`date +%Y-%m-%d`_${instance_name}.tar.gz
      rm /var/wikicompare/backups/$filename
      drush archive-dump $sites --destination=/var/wikicompare/backups/$filename

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


cd /var/wikicompare/control_backups
pwd
ncftp -u $ftpuser -p $ftppass $ftpserver<<EOF
get ./*
EOF
for file in *.tar.gz
do
  mkdir ${file//.tar.gz/}
  tar -zxf $file -C ${file//.tar.gz/}
done
rm *.tar.gz

find /var/wikicompare/backups/ -type f -mtime +4 | xargs -r rm


fi

chown -R www-data /var/wikicompare/backups
chmod -R 700 /var/wikicompare/backups
chown -R www-data:shinken /var/wikicompare/control_backups
chmod -R 755 /var/wikicompare/control_backups
}


control_backup()
{

    if [[ $2 ]]
    then
      instance_name=$2
    else
    cd $website_path
    result_wikicompare=$(drush sql-query "select n.title, fn.title from node n INNER JOIN field_data_wikicompare_instance f ON n.nid=f.entity_id INNER JOIN node fn ON f.wikicompare_instance_target_id = fn.nid WHERE n.title = '$1'  LIMIT 1")
    i=0
    wikicompare_name=''
    instance_name=''
    for row_wikicompare in $result_wikicompare
    do
      if [[ $i == 2 ]]
      then
        wikicompare_name=$row_wikicompare
      elif [[ $i == 3 ]]
      then
        instance_name=$row_wikicompare
      fi
      let i++
    done
    fi
    
    if [[ ! $instance_name ]]
    then
      echo "L'instance n'a pas pu etre determine."
      exit 2
    fi    
    
    directory=/var/wikicompare/control_backups/`date +%Y-%m-%d`_${instance_name}
        

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

if [[ $1 == 'dev' ]]
then
sed -i 's/settings[zen_rebuild_registry] = 0/settings[zen_rebuild_registry] = 1/' $archive_path/wikicompare_${1}/archive/sites/all/themes/wikicompare_theme/wikicompare_theme.info
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
pg_dump -U wkc_${1} -h 127.0.0.1 -Fc wikicompare_${1} > $archive_path/wikicompare_${1}/pgsql/build.sql
cp -R $archive_path/wikicompare_${1}/pgsql $archive_path/wikicompare_${1}/archive/
mkdir /var/www/$instance/pgsql
cp -R $archive_path/wikicompare_${1}/pgsql/* /var/www/$instance/pgsql/

db_type='mysql'
instance=wikicompare_${1}_mysql
deploy ${1}_my
mkdir $archive_path/wikicompare_${1}/mysql
mkdir $archive_path/wikicompare_${1}/mysql/sites
cp -r /var/www/$instance/sites/${1}-my.wikicompare.info/* $archive_path/wikicompare_${1}/mysql/sites/
mysqldump -u root -p$mysql_password wikicompare_${1}_my > $archive_path/wikicompare_${1}/mysql/build.sql
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
       upgrade $instance
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
       upgrade $instance

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



