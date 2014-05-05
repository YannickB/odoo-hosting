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

    unique_name=$application-$saas-$domain
    unique_name=${unique_name//./-}
    unique_name_underscore=${unique_name//-/_}

    echo creating openerp database

/usr/local/bin/erppeek --server http://$server:$port -p $database_password << EOF
client.create_database('$database_password', '$unique_name_underscore')
EOF

    ssh $system_user@$server << EOF
      mkdir $instances_path/filestore/$unique_name_underscore
EOF

    exit 1
    ;;

  build)
    exit
    ;;


  post_restore)
    exit
    ;;

  test_specific)
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
    domain=$4
    server=$5
    port=$6
    unique_name=$7
    instances_path=$8

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














