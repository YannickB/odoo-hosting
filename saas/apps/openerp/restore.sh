 #!/bin/bash




case $1 in
  restore_saas)

    application=$2
    from_saas=$3
    to_saas=$4
    domain=$5
    server=$6
    system_user=$7
    filename=$8
    instances_path=$9
    backup_directory=${10}

    from_unique_name=$application-$from_saas-$domain
    from_unique_name_underscore=${from_unique_name//-/_}
    from_unique_name_underscore=${from_unique_name_underscore//./_}

    to_unique_name=$application-$to_saas-$domain
    to_unique_name_underscore=${to_unique_name//-/_}
    to_unique_name_underscore=${to_unique_name_underscore//./_}

    ssh $system_user@$server << EOF
    rm -rf $instances_path/filestore/${to_unique_name_underscore}
    mkdir $instances_path/filestore/${to_unique_name_underscore}
EOF

    scp $backup_directory/restore/$filename/filestore/${from_unique_name_underscore}/* $system_user@$server:$instances_path/filestore/${to_unique_name_underscore}

    exit
    ;;


  ?)
    exit
    ;;
esac