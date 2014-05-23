 #!/bin/bash




case $1 in
  move_saas)

    application=$2
    from_saas=$3
    from_domain=$4
    from_server=$5
    from_system_user=$6
    to_saas=$7
    to_domain=$8
    to_server=$9
    to_system_user=${10}
    instances_path=${11}

    from_unique_name=$application-$from_saas-$from_domain
    from_unique_name_underscore=${from_unique_name//-/_}
    from_unique_name_underscore=${from_unique_name_underscore//./_}

    to_unique_name=$application-$to_saas-$to_domain
    to_unique_name_underscore=${to_unique_name//-/_}
    to_unique_name_underscore=${to_unique_name_underscore//./_}

    mkdir /tmp/${from_unique_name_underscore}-filestore

    ssh $to_system_user@$to_server << EOF
    rm -rf $instances_path/filestore/${to_unique_name_underscore}
    mkdir $instances_path/filestore/${to_unique_name_underscore}
EOF

    scp -r $from_system_user@$from_server:$instances_path/filestore/${from_unique_name_underscore}/* /tmp/${from_unique_name_underscore}-filestore
    scp -r /tmp/${from_unique_name_underscore}-filestore/* $to_system_user@$to_server:$instances_path/filestore/${to_unique_name_underscore}

    rm -rf /tmp/${from_unique_name_underscore}-filestore

    exit
    ;;


  ?)
    exit
    ;;
esac