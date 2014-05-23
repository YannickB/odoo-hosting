#!/bin/bash



case $1 in
  pre_upgrade)
    instance=$2
    system_user=$3
    server=$4
    instances_path=$5


    exit
    ;;

  post_upgrade)
    instance=$2
    system_user=$3
    server=$4
    instances_path=$5
  
    exit
    ;;

  upgrade_saas)
    application=$2
    saas=$3
    domain=$4
    instance=$5
    system_user=$6
    server=$7
    port=$8
    admin_user=$9
    admin_password=${10}
    instances_path=${11}

    saas_name=$application-$saas-$domain
    saas_name_underscore=${saas_name//-/_}
    saas_name_underscore=${saas_name_underscore//./_}
    db_user=${instance//-/_}

    /usr/local/bin/erppeek --server http://$server:$port -u $admin_user -p $admin_password -d $saas_name_underscore << EOF
client.upgrade('base')
EOF

    exit
    ;;

  ?)
    exit
    ;;
esac
