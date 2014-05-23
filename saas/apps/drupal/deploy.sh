#!/bin/bash




case $1 in
  post_instance)
    instance=$2
    server=$3
    application=$4
    application_type=$5
    system_user=$6
    openerp_path=$7
    database_password=$8
    port=$9

    exit
    ;;


  create_database)
    application=$2
    domain=$3
    saas=$4
    server=$5
    database_password=$6
    port=$7
    system_user=$8
    instances_path=$9
    build=${10}
    test=${11}
    admin_password=${12}

    unique_name=$application-$saas-$domain
    unique_name=${unique_name//./-}
    unique_name_underscore=${unique_name//-/_}

    exit 0
    ;;

  build)
  
    application=$2
    domain=$3
    instance=$4
    saas=$5
    db_type=$6
    system_user=$7
    server=$8
    database_server=$9
    database_password=${10}
    admin_user=${11}
    admin_password=${12}
    admin_email=${13}
    instances_path=${14}
    port=${15}
	
	  unique_name=$application-$saas-$domain
    unique_name=${unique_name//./-}
    unique_name_underscore=${unique_name//-/_}

    db_user=${instance//-/_}
  
    echo drush -y si --db-url=$db_type://${db_user}:$database_password@$database_server/$unique_name_underscore --account-mail=$admin_email --account-name=$admin_user --account-pass=$admin_password --sites-subdir=$saas.$domain minimal

    ssh $system_user@$server << EOF
      cd $instances_path/$instance
      pwd
      drush -y si --db-url=$db_type://${db_user}:$database_password@$database_server/$unique_name_underscore --account-mail=$admin_email --account-name=$admin_user --account-pass=$admin_password --sites-subdir=$saas.$domain minimal
      cd sites/$saas.$domain
      pwd
      drush -y en piwik admin_menu_toolbar wikicompare wikicompare_profiles wikicompare_translation wikicompare_inherit_product
      drush -y pm-enable wikicompare_theme
      drush vset --yes --exact theme_default wikicompare_theme
EOF

  # drush vset --yes --exact bakery_master $bakery_master_site
  # drush vset --yes --exact bakery_key '$bakery_private_key'
  # drush vset --yes --exact bakery_domain $bakery_cookie_domain

    exit
    ;;


  post_restore)

    application=$2
    domain=$3
    instance=$4
    saas=$5
    title=$6
    system_user=$7
    server=$8
    db_type=$9
    database_server=${10}
    database_password=${11}
    admin_user=${12}
    admin_password=${13}
    admin_email=${14}
    instances_path=${15}
    
    
    unique_name=$application-$saas-$domain
    unique_name=${unique_name//./-}
    unique_name_underscore=${unique_name//-/_}
  
    db_user=${instance//-/_}

    echo post_restore
  
    ssh $system_user@$server << EOF
      mkdir $instances_path/$instance/sites/$saas.$domain
      cp -r $instances_path/$instance/$db_type/sites/* $instances_path/$instance/sites/$saas.$domain/
      cd $instances_path/$instance/sites/$saas.$domain
      sed -i "s/'database' => '[#a-z0-9_!]*'/'database' => '$unique_name_underscore'/g" $instances_path/$instance/sites/$saas.$domain/settings.php
      sed -i "s/'username' => '[#a-z0-9_!]*'/'username' => '$db_user'/g" $instances_path/$instance/sites/$saas.$domain/settings.php
      sed -i "s/'password' => '[#a-z0-9_!]*'/'password' => '$database_passwpord'/g" $instances_path/$instance/sites/$saas.$domain/settings.php
      sed -i "s/'host' => '[0-9.]*'/'host' => '$database_server'/g" $instances_path/$instance/sites/$saas.$domain/settings.php
      pwd
      echo Title $title
      drush vset --yes --exact site_name $title
      drush user-password $admin_user --password=$admin_password
EOF
  
    exit
    ;;

  create_poweruser)
  
    application=$2
    domain=$3
    instance=$4
    saas=$5
    system_user=$6
    server=$7
    user_name=$8
    user_password=$9
    user_email=${10}
    instances_path=${11}
    
    
    ssh $system_user@$server << EOF  
    cd $instances_path/$instance/sites/$saas.$domain
    drush user-create $user_name --password=$user_password --mail=$user_email
    drush user-add-role wikicompare_admin $user_name
EOF
    exit
    ;;    
    
    
  test_specific)

    application=$2
    domain=$3
    instance=$4
    saas=$5
    system_user=$6
    server=$7
    user_name=$8
    instances_path=$9
    admin_user=${10}
    admin_password=${11}
    port=${12}
  
    echo 'Deploying demo data'
    ssh $system_user@$server << EOF
      cd $instances_path/$instance/sites/$saas.$domain
      drush vset --yes --exact wikicompare_test_platform 1
      drush -y en wikicompare_generate_demo
      drush $module_path/wikicompare.script --user=$user_name deploy_demo
EOF

    if [[ $1 == 'dev' ]]
    then
      ssh $system_user@$server << EOF
        drush -y en devel
EOF
    fi

    
    exit
    ;;

  post_deploy)
  
    application=$2
    domain=$3
    instance=$4
    saas=$5
    system_user=$6
    server=$7
    instances_path=$8
  
    
    ssh $system_user@$server << EOF
    chmod -R 700 $instances_path/$instance/sites/$saas.$domain/
EOF
  
    exit
    ;;



  post_piwik)
  
    application=$2
    domain=$3
    instance=$4
    saas=$5
    system_user=$6
    server=$7
    piwik_id=$8
    piwik_url=$9
    instances_path=${10}
  

    ssh $system_user@$server << EOF
    cd $instances_path/$instance/sites/$saas.$domain
    drush variable-set piwik_site_id $piwik_id
    drush variable-set piwik_url_http $piwik_url
    drush variable-set piwik_privacy_donottrack 0
EOF
  
    exit
    ;;

  prepare_apache)
    application=$2
    saas=$3
    instance=$4
    domain=$5
    server=$6
    port=$7
    unique_name=$8
    instances_path=$9



    ssh www-data@$server << EOF
    sed -i 's/SAAS/${saas}/g' /etc/apache2/sites-available/$unique_name
    sed -i 's/DOMAIN/${domain}/g' /etc/apache2/sites-available/$unique_name
    sed -i 's/INSTANCE/${instance}/g' /etc/apache2/sites-available/$unique_name
    sed -i 's,INSTPATH,${instances_path},g' /etc/apache2/sites-available/$unique_name
EOF


    echo after prepare_apache
    exit
    ;;

  ?)
    exit
    ;;
esac
