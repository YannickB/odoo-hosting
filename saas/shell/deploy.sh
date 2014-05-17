#!/bin/bash


# usage()
# {
# cat << EOF
# usage: $0 options

# This script run the test1 or test2 over a machine.

# OPTIONS:
   # -h      Show this message
   # -t      Test type, can be ‘test1' or ‘test2'
   # -r      Server address
   # -p      Server root password
   # -v      Verbose
# EOF
# }



# echo deploying...


# ssh -q www-data@$IP exit
# echo $?
# if [[ $? != 0 ]]
# then
  # echo Impossible to contact the instance server
  # exit
# fi

# ssh -q www-data@${database_IP} exit
# echo $?
# if [[ $? != 0 ]]
# then
  # echo Impossible to contact the database server
  # exit
# fi




deploy_instance()
{

version=''
if ssh $system_user@$server stat $instances_path/$instance \> /dev/null 2\>\&1
then
  echo instance already exist
  exit
fi

ssh $system_user@$server << EOF
  mkdir $instances_path/$instance
EOF

echo $system_user@$server:$instances_path/$instance

scp $archive_path/$archive/archive.tar.gz $system_user@$server:$instances_path/$instance/


ssh $system_user@$server << EOF
  cd $instances_path/$instance
  tar -xf archive.tar.gz -C $instances_path/$instance/
  rm archive.tar.gz
EOF



echo Creating database user

#SI postgres, create user
echo $db_type
if [[ $db_type != 'mysql' ]]
then
ssh postgres@$database_server << EOF
  psql
  CREATE USER $db_user WITH PASSWORD '$database_password' CREATEDB;
  \q
EOF

ssh $system_user@$server << EOF
  sed -i "/:*:$db_user:/d" ~/.pgpass
  echo "$database_server:5432:*:$db_user:$database_password" >> ~/.pgpass
  chmod 700 ~/.pgpass
EOF

else
echo mysql -u root -p$mysql_password -se create user ${db_user}@${server} identified by $database_password; 
ssh $system_user@$database_server << EOF
  mysql -u root -p'$mysql_password' -se "create user '${db_user}' identified by '$database_password';"
EOF
fi

echo Database user created

$openerp_path/saas/saas/apps/$application_type/deploy.sh post_instance $instance $server $application $application_type $system_user $openerp_path $database_password $port


if ssh $system_user@$server stat $instances_path/$instance \> /dev/null 2\>\&1
then
  echo instance ok
else
  echo There was an error while creating the instance
  exit
fi

}



deploy_saas()
{


unique_name=$application-$saas-$domain
unique_name=${unique_name//./-}
unique_name_underscore=${unique_name//-/_}

db_user=${instance//-/_}

echo build : $build
if [[ $build == True ]]
then

  echo Creating database for $saas

  $openerp_path/saas/saas/apps/$application_type/deploy.sh create_database $application $domain $saas $server $database_password $port $system_user $instances_path $test $admin_password

  if [[ $? != 1 ]]
  then
    #SI postgres, create user
    echo $db_type
    if [[ $db_type != 'mysql' ]]
    then
    ssh postgres@$database_server << EOF
      psql
      CREATE DATABASE $unique_name_underscore;
      ALTER DATABASE $unique_name_underscore OWNER TO $db_user;
      \q
EOF

    ssh $system_user@$server << EOF
      sed -i "/:*:$db_user:/d" ~/.pgpass
      echo "$database_server:5432:*:$db_user:$database_password" >> ~/.pgpass
EOF

    else
    ssh www-data@$database_server << EOF
      mysql -u root -p'$mysql_password' -se "create database $unique_name_underscore;"
      mysql -u root -p'$mysql_password' -se "grant all on $unique_name_underscore.* to '${db_user}';"
EOF
    fi
  fi
  echo Database created

  $openerp_path/saas/saas/apps/$application_type/deploy.sh build $application $domain $instance $saas $db_type $system_user $server $database_server $database_password $admin_name $admin_password $admin_email $instances_path $port


else



  if [[ $db_type != 'mysql' ]]
  then
  ssh www-data@$IP << EOF
  pg_restore -U $db_user -h $database_IP --no-owner -Fc -d $unique_name $instances_path/$instance/$db_type/build.sql
EOF
  else
  ssh www-data@$database_IP << EOF
  mysql -u $db_user -p$admin_password -h $database_IP $unique_name < $instances_path/$instance/$db_type/build.sql
EOF
  fi

  $openerp_path/saas/saas/apps/$application_type/deploy.sh post_restore $application $domain $instance $saas $title $system_user $server $db_type $database_server $database_password $admin_name $admin_password $admin_email $instances_path

fi

if [[ $admin_name != $user_name ]]
then
  $openerp_path/saas/saas/apps/$application_type/deploy.sh create_poweruser $application $domain $instance $saas $system_user $server $user_name $user_password $user_email $instances_path
fi


if [[ $test == True ]]
then
  $openerp_path/saas/saas/apps/$application_type/deploy.sh test_specific $application $domain $instance $saas $system_user $server $user_name $instances_path $admin_name $admin_password $port
fi


  # ssh $system_user@$IP << EOF
  # chown -R $system_user:$system_user $instances_path/$instance
# EOF

$openerp_path/saas/saas/apps/$application_type/deploy.sh post_deploy $application $domain $instance $saas $system_user $server $instances_path


if [[ $skip_analytics != True ]]
then

  if [[ $saas != 'demo' ]]
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

  $openerp_path/saas/saas/apps/$application_type/deploy.sh post_piwik $application $domain $instance $saas $system_user $server $piwik_id $piwik_server $instances_path

fi


scp $openerp_path/saas/saas/apps/$application_type/apache.config www-data@$server:/etc/apache2/sites-available/$unique_name

# escape='\$1'
$openerp_path/saas/saas/apps/$application_type/deploy.sh prepare_apache $application $saas $instance $domain $server $port $unique_name $instances_path

ssh www-data@$server << EOF
  sudo a2ensite $unique_name
  sudo /etc/init.d/apache2 reload
EOF


ssh $dns_server << EOF
  sed -i "/$saas\sIN\sCNAME/d" /etc/bind/db.$domain
  echo "$saas IN CNAME $server." >> /etc/bind/db.$domain
  sudo /etc/init.d/bind9 reload
EOF


scp $openerp_path/saas/saas/shell/shinken.config $shinken_server:/usr/local/shinken/etc/services/${unique_name}.cfg

directory=$backup_directory/control_backups/`date +%Y-%m-%d`-${server}-${instance}-auto
directory=${directory//./-}

ssh $shinken_server << EOF
  sed -i 's/UNIQUE_NAME/${unique_name}/g' /usr/local/shinken/etc/services/${unique_name}.cfg
  sed -i 's/APPLICATION/${application}/g' /usr/local/shinken/etc/services/${unique_name}.cfg
  sed -i 's/SERVER/${server}/g' /usr/local/shinken/etc/services/${unique_name}.cfg
  sed -i 's/INSTANCE/${instance}/g' /usr/local/shinken/etc/services/${unique_name}.cfg
  sed -i 's/SAAS/${saas}/g' /usr/local/shinken/etc/services/${unique_name}.cfg
  sed -i 's/DOMAIN/${domain}/g' /usr/local/shinken/etc/services/${unique_name}.cfg
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
echo 'lorem ipsum' > $directory/$unique_name_underscore.sql
EOF

}


case $1 in
  instance)
    application_type=$2
    application=$3
    instance=$4
    instances_path=$5
    db_type=$6
    system_user=$7
    server=$8
    database_server=$9
    database_password=${10}
    archive=${11}
    archive_path=${12}
    openerp_path=${13}
    port=${14}
    mysql_password=${15}
    db_user=${instance//-/_}

    deploy_instance
    exit
    ;;

  saas)
    application_type=$2
    application=$3
    domain=$4
    saas=$5
    title=$6
    system_user=$7
    server=$8
    database_server=$9
    db_type=${10}
    database_password=${11}
    instance=${12}
    port=${13}
    admin_name=${14}
    admin_password=${15}
    admin_email=${16}
    user_name=${17}
    user_password=${18}
    user_email=${19}
    build=${20}
    test=${21}
    skip_analytics=${22}
    piwik_server=${23}
    piwik_password=${24}
    piwik_demo_id=${25}
    instances_path=${26}
    openerp_path=${27}
    dns_server=${28}
    shinken_server=${29}
    backup_directory=${30}
    mysql_password=${31}

    deploy_saas
    exit
    ;;
  ?)
    exit
    ;;
esac

