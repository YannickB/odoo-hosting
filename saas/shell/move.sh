#!/bin/bash

move_saas()
{

  from_unique_name=$application-$from_saas-$from_domain
  from_unique_name_underscore=${from_unique_name//-/_}
  from_unique_name_underscore=${from_unique_name_underscore//./_}
  from_db_user=${from_instance//-/_}

  to_unique_name=$application-$to_saas-$to_domain
  to_unique_name_underscore=${to_unique_name//-/_}
  to_unique_name_underscore=${to_unique_name_underscore//./_}
  to_db_user=${to_instance//-/_}

  ssh $from_system_user@$from_server << EOF
  pg_dump -Fc -U $from_db_user -h $from_database_server $from_unique_name_underscore > /tmp/${from_unique_name_underscore}.sql
EOF

  scp $from_system_user@$from_server:/tmp/${from_unique_name_underscore}.sql /tmp/temp-${from_unique_name_underscore}.sql
  scp /tmp/temp-${from_unique_name_underscore}.sql $to_system_user@$to_server:/tmp/${to_unique_name_underscore}.sql
  rm /tmp/temp-${from_unique_name_underscore}.sql

  ssh $from_system_user@$from_server << EOF
  rm /tmp/${from_unique_name_underscore}.sql
EOF

  ssh $to_system_user@$to_server << EOF
  pg_restore -U $to_db_user -h $to_database_server --no-owner -Fc -d $to_unique_name_underscore /tmp/${to_unique_name_underscore}.sql
  rm /tmp/${to_unique_name_underscore}.sql
EOF

  $openerp_path/saas/saas/apps/$application_type/move.sh move_saas $application $from_saas $from_domain $from_server $from_system_user $to_saas $to_domain $to_server $to_system_user $instances_path

}



case $1 in
  move_saas)

    application_type=$2
    application=$3
    from_saas=$4
    from_domain=$5
    from_instance=$6
    from_server=$7
    from_system_user=$8
    from_database_server=$9
    to_saas=${10}
    to_domain=${11}
    to_instance=${12}
    to_server=${13}
    to_system_user=${14}
    to_database_server=${15}
    instances_path=${16}
    backup_directory=${17}
    openerp_path=${18}

    move_saas
    exit
    ;;

  ?)
    exit
    ;;
esac

