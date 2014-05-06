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
    cd $instances_path/$instance/sites/
    find . -name '*[a-zA-Z0-9\-].*' -maxdepth 1 -type d -exec bash -c 'cd $instances_path/$instance/sites/{}; pwd; drush updatedb' \;
EOF
  


    exit
    ;;

  ?)
    exit
    ;;
esac
