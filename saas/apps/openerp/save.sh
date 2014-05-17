 #!/bin/bash




case $1 in
  save_dump)

    application=$2
    saas_names=$3
    filename=$4
    server=$5
    database_server=$6
    instance=$7
    system_user=$8
    backup_directory=$9
    instances_path=${10}

    saas_names=${saas_names//,/ }

    ssh $system_user@$server << EOF
    mkdir $backup_directory/backups/prepare_temp/${filename}
    mkdir $backup_directory/backups/prepare_temp/${filename}/filestore
EOF

    echo $saas_names
    for saas_name in $saas_names
    do
      echo $saas_name
      saas_name=$application-$saas_name
      saas_name_underscore=${saas_name//-/_}
      saas_name_underscore=${saas_name_underscore//./_}
      db_user=${instance//-/_}

      ssh $system_user@$server << EOF
      pg_dump -U $db_user -h $database_server $saas_name_underscore > $backup_directory/backups/prepare_temp/${filename}/${saas_name_underscore}.sql
      cp -R $instances_path/filestore/${saas_name_underscore} $backup_directory/backups/prepare_temp/${filename}/filestore
EOF

    done

    ssh $system_user@$server << EOF
      cd $backup_directory/backups/prepare_temp/${filename}
      tar -czf ../../prepare/$filename ./*
      cd ../../
      rm -rf $backup_directory/backups/prepare_temp/${filename}
EOF

    exit
    ;;


  ?)
    exit
    ;;
esac