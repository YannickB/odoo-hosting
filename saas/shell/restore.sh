#!/bin/bash

restore_saas()
{

    from_unique_name=$application-$from_saas-$domain
    from_unique_name_underscore=${from_unique_name//-/_}
    from_unique_name_underscore=${from_unique_name_underscore//./_}
    db_user=${instance//-/_}

    to_unique_name=$application-$to_saas-$domain
    to_unique_name_underscore=${to_unique_name//-/_}
    to_unique_name_underscore=${to_unique_name_underscore//./_}

    echo transfer file


    ncftpget -u $ftpuser -p$ftppass $ftpserver $backup_directory/restore $filename.tar.gz
    mkdir $backup_directory/restore/$filename
    cd $backup_directory/restore/$filename
    tar -zxf $backup_directory/restore/$filename.tar.gz
    scp $backup_directory/restore/$filename/${from_unique_name_underscore}.sql $system_user@$server:$backup_directory/${to_unique_name_underscore}.sql

    echo start restore

    ssh $system_user@$server << EOF
    dropdb -U $db_user -h $database_server $to_unique_name_underscore
    createdb -U $db_user -h $database_server $to_unique_name_underscore
    pg_restore -U $db_user -h $database_server --no-owner -Fc -d $to_unique_name_underscore $backup_directory/${to_unique_name_underscore}.sql
    rm $backup_directory/${to_unique_name_underscore}.sql
EOF


  $openerp_path/saas/saas/apps/$application_type/restore.sh restore_saas $application $from_saas $to_saas $domain $server $system_user $filename $instances_path $backup_directory

  rm -rf $backup_directory/restore/${filename}*

}



case $1 in
  restore_saas)

    application_type=$2
    application=$3
    from_saas=$4
    to_saas=$5
    domain=$6
    instance=$7
    server=$8
    system_user=$9
    database_server=${10}
    filename=${11}
    instances_path=${12}
    backup_directory=${13}
    shinken_server=${14}
    openerp_path=${15}
    ftpuser=${16}
    ftppass=${17}
    ftpserver=${18}

    restore_saas
    exit
    ;;

  ?)
    exit
    ;;
esac

