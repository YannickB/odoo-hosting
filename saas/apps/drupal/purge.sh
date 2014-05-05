#!/bin/bash



case $1 in
  pre_instance)
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

    instance=$application-$saas

    if [[ $instance_name != '' ]]
    then
    ssh $system_user@$server << EOF
    rm -rf $instances_path/$instance_name/sites/$saas.$domain
EOF
    fi


    exit
    ;;


  ?)
    exit
    ;;
esac
 

