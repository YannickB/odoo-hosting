#!/bin/bash



case $1 in
  pre_instance)
    instance=$2
    server=$3
    system_user=$4
    db_type=$5

    ssh root@$server << EOF
    /etc/init.d/${instance} stop
    rm /etc/openerp/${instance}.config
    rm /etc/init.d/${instance}
EOF



    exit
    ;;



  post_purge)
    application=$2
    domain=$3
    saas=$4
    server=$5
    system_user=$6
    instances_path=$7

    unique_name=$application-$saas-$domain
    unique_name=${unique_name//./-}
    unique_name_underscore=${unique_name//-/_}

    ssh $system_user@$server << EOF
      rm -rf $instances_path/filestore/$unique_name_underscore
EOF


    exit
    ;;


  ?)
    exit
    ;;
esac
 


