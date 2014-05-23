#!/bin/bash




case $1 in
  pre_upgrade)
    instance=$2
    system_user=$3
    server=$4
    instances_path=$5
    
    pear upgrade drush/drush

    ssh $system_user@$server << EOF
    mkdir $instances_path/sites-${instance}-temp
    cp -r $instances_path/$instance/sites/* $instances_path/sites-${instance}-temp
EOF

    exit
    ;;

  post_upgrade)
    instance=$2
    system_user=$3
    server=$4
    instances_path=$5
  
    ssh $system_user@$server << EOF
    rm -rf $instances_path/$instance/sites/*
    cp -r $instances_path/sites-${instance}-temp/* $instances_path/$instance/sites/
    rm -rf $instances_path/sites-${instance}-temp
EOF

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
    saas_name_dot=${saas_name//-/.}


    ssh $system_user@$server << EOF
    cd $instances_path/$instance/sites/${saas_name_dot}
    drush updatedb
EOF
  
#find . -name '*[a-zA-Z0-9\-].*' -maxdepth 1 -type d -exec bash -c 'cd $instances_path/$instance/sites/{}; pwd; drush updatedb' \;


    exit
    ;;

  ?)
    exit
    ;;
esac
