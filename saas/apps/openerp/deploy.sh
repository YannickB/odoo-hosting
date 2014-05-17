#!/bin/bash




case $1 in
  post_instance)
    instance=$2
    server=$3
    application=$4
    application_type=$5
    system_user=$6
    openerp_path=$7
    database_password=$8
    port=$9

    db_user=${instance//-/_}

    scp $openerp_path/saas/saas/apps/$application_type/openerp.config root@$server:/etc/openerp/${instance}.config
    scp $openerp_path/saas/saas/apps/$application_type/openerp.init root@$server:/etc/init.d/$instance

    ssh root@$server << EOF
    sed -i 's/INSTANCE/${instance}/g' /etc/openerp/${instance}.config
    sed -i 's/DBUSER/${db_user}/g' /etc/openerp/${instance}.config
    sed -i 's/DATABASE_PASSWORD/${database_password}/g' /etc/openerp/${instance}.config
    sed -i 's/PORT/${port}/g' /etc/openerp/${instance}.config
    sed -i 's/APPLICATION/$application/g' /etc/openerp/${instance}.config
    sed -i 's/INSTANCE/${instance}/g' /etc/init.d/${instance}
    sed -i 's/SYSTEM_USER/$system_user/g' /etc/init.d/${instance}
    sed -i 's/APPLICATION/$application/g' /etc/init.d/${instance}
    /etc/init.d/$instance start
EOF
    exit
    ;;


  create_database)
    application=$2
    domain=$3
    saas=$4
    server=$5
    database_password=$6
    port=$7
    system_user=$8
    instances_path=$9
    test=${10}
    admin_password=${11}

    unique_name=$application-$saas-$domain
    unique_name=${unique_name//./-}
    unique_name_underscore=${unique_name//-/_}

    echo creating openerp database

    echo $test

# -p $database_password 
/usr/local/bin/erppeek --server http://$server:$port << EOF
client.create_database('$database_password', '$unique_name_underscore', demo=$test, lang='fr_FR', user_password='$admin_password')
EOF

    ssh $system_user@$server << EOF
      mkdir $instances_path/filestore/$unique_name_underscore
EOF

    exit 1
    ;;

  build)

    application=$2
    domain=$3
    instance=$4
    saas=$5
    db_type=$6
    system_user=$7
    server=$8
    database_server=$9
    database_password=${10}
    admin_user=${11}
    admin_password=${12}
    admin_email=${13}
    instances_path=${14}
    port=${15}
	
	  unique_name=$application-$saas-$domain
    unique_name=${unique_name//./-}
    unique_name_underscore=${unique_name//-/_}

/usr/local/bin/erppeek --server http://$server:$port -u $admin_user -p $admin_password -d $unique_name_underscore << EOF
client.install('account_accountant', 'account_chart_install', 'l10n_fr')
client.execute('account.chart.template', 'install_chart', 'l10n_fr', 'l10n_fr_pcg_chart_template', 1, 1)
client.install('community')
EOF
    exit
    ;;


  post_restore)
    exit
    ;;

  test_specific)

    application=$2
    domain=$3
    instance=$4
    saas=$5
    system_user=$6
    server=$7
    user_name=$8
    instances_path=$9
    admin_user=${10}
    admin_password=${11}
    port=${12}

	  unique_name=$application-$saas-$domain
    unique_name=${unique_name//./-}
    unique_name_underscore=${unique_name//-/_}

    echo server : $server, user_name: $user_name, instances_path: $instances_path, admin_user : $admin_user, admin_password: $admin_password, port : $port
    echo 'Deploying demo data'
/usr/local/bin/erppeek --server http://$server:$port -u $admin_user -p $admin_password -d $unique_name_underscore << EOF
client.install('community_blog', 'community_crm', 'community_event', 'community_forum', 'community_marketplace', 'community_project')
EOF

    exit
    ;;

  post_deploy)
    exit
    ;;

  create_poweruser)
    exit
    ;;

  post_piwik)
    exit
    ;;

  prepare_apache)
    application=$2
    saas=$3
    instance=$4
    domain=$5
    server=$6
    port=$7
    unique_name=$8
    instances_path=$9

    ssh www-data@$server << EOF
    sed -i 's/SAAS/${saas}/g' /etc/apache2/sites-available/$unique_name
    sed -i 's/DOMAIN/${domain}/g' /etc/apache2/sites-available/$unique_name
    sed -i 's/PORT/${port}/g' /etc/apache2/sites-available/$unique_name
EOF
    exit
    ;;

  ?)
    exit
    ;;
esac














