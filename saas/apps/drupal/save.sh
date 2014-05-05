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
    
    echo $saas_names
    echo $system_user@$server

    saas=''
    for saas_name in $saas_names
    do    
      saas=$saas_name
    done

    ssh $system_user@$server << EOF
      cd $instances_path/$instance/sites/$saas
      drush archive-dump $saas_names --destination=$backup_directory/backups/prepare/$filename
EOF

    echo after drupal save_dump

    exit
    ;;


  ?)
    exit
    ;;
esac
