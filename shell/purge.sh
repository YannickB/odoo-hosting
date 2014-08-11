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


# while getopts "ht:p:a:n:c:u:s:e:r:d:bkz" OPTION;
# do
     # case $OPTION in
         # h)
             # usage
             # exit 1
             # ;;
         # t)
             # title=$OPTARG
             # ;;
         # a)
             # admin_user=$OPTARG
             # ;;
         # p)
             # admin_password=$OPTARG
             # ;;
         # n)
             # instance=$OPTARG
             # ;;
         # c)
             # archive_path=$OPTARG
             # ;;
         # u)
             # user_name=$OPTARG
             # ;;
         # s)
             # user_password=$OPTARG
             # ;;
         # e)
             # user_mail=$OPTARG
             # ;;
         # r)
             # server=$OPTARG
             # ;;
         # d)
             # database_server=$OPTARG
             # ;;
         # k)
             # skip_analytics=True
             # ;;
         # b)
             # build=True
             # archive='wikicompare_preprod'
             # ;;
         # z)
             # test=True
             # ;;
         # ?)
             # usage
             # exit
             # ;;
     # esac
# done 
 
 



purge_instance()
{

db_user=${instance//-/_}

$openerp_path/saas/saas/apps/$application_type/purge.sh pre_instance $instance $server $system_user $db_type


if [[ $db_type != 'mysql' ]]
then
ssh postgres@$database_server << EOF
  psql
  DROP USER $db_user;
  \q
EOF

ssh $system_user@$server << EOF
  sed -i "/:*:$db_user:/d" ~/.pgpass
EOF

else
echo mysql -u root -p$mysql_password -se "drop user $db_user;" 
ssh $system_user@$database_server << EOF
  mysql -u root -p'$mysql_password' -se "drop user $db_user;"
EOF
fi


ssh $system_user@$server << EOF
  rm -rf $instances_path/$instance
EOF


}



 

purge_saas()
{


unique_name=$application-$saas-$domain
unique_name=${unique_name//./-}
unique_name_underscore=${unique_name//-/_}

ssh $shinken_server << EOF
rm /usr/local/shinken/etc/services/$unique_name.cfg 
/etc/init.d/shinken reload
EOF

ssh $dns_server << EOF
sed -i "/$saas\sIN\sCNAME/d" /etc/bind/db.$domain
sudo /etc/init.d/bind9 reload
EOF



if [[ $db_type != 'mysql' ]]
then
ssh postgres@$database_server << EOF
  psql
  update pg_database set datallowconn = 'false' where datname = '$unique_name_underscore';
  SELECT pg_terminate_backend(procpid) FROM pg_stat_activity WHERE datname = '$unique_name_underscore';
  DROP DATABASE $unique_name_underscore;
  \q
EOF



else
ssh www-data@$database_server << EOF
  mysql -u root -p'$mysql_password' -se "drop database $unique_name_underscore;"
EOF
fi



ssh www-data@$server << EOF
sudo a2dissite $unique_name
rm /etc/apache2/sites-available/$unique_name
sudo /etc/init.d/apache2 reload
EOF


$openerp_path/saas/saas/apps/$application_type/purge.sh post_purge $application $domain $saas $server $system_user $instances_path

if [[ $saas != 'demo' ]]
then

#TODO This part is not crossplatform because recover the variable will be difficult. When we will move piwik, consider open the post mysql to www server ip so we can continue query it directly.
#ssh $piwik_server << EOF
piwik_id=$(mysql piwik -u piwik -p$piwik_password -se "select idsite from piwik_site WHERE name = '$saas.$domain' LIMIT 1")
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

}





case $1 in
  instance)
    application_type=$2
    instance=$3
    instances_path=$4
    db_type=$5
    system_user=$6
    server=$7
    database_server=$8
    openerp_path=$9
    mysql_password=${10}
    db_user=${instance//-/_}

    purge_instance
    exit
    ;;

  saas)
    application_type=$2
    application=$3
    domain=$4
    saas=$5
    system_user=$6
    server=$7
    database_server=$8
    db_type=$9
    piwik_server=$10
    piwik_password=${11}
    instances_path=${12}
    openerp_path=${13}
    dns_server=${14}
    shinken_server=${15}
    mysql_password=${16}

    purge_saas
    exit
    ;;
  ?)
    exit
    ;;
esac
