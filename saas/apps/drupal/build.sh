#!/bin/bash




case $1 in
  build_archive)

    app=$2
    name=$3
    archive_path=$4
    openerp_path=$5
    build_directory=$6

echo $openerp_path/saas/saas/apps/drupal/wikicompare_${name}.make
    drush make $openerp_path/saas/saas/apps/drupal/wikicompare_${name}.make $archive_path/${app}-${name}/archive

    patch -p0 -d $archive_path/${app}-${name}/archive/sites/all/modules/revisioning/ < $openerp_path/saas/saas/apps/drupal/patch/revisioning_postgres.patch

    if [[ $name == 'dev' ]]
    then
    patch -p0 -d $archive_path/${app}-${name}/archive/sites/all/themes/wikicompare_theme/ < $openerp_path/saas/saas/apps/drupal/patch/dev_zen_rebuild_registry.patch
    fi

    exit
    ;;

  build_dump)
    app=$2
    name=$3
    instance=$4
    domain=$5
    db_type=$6
    archive_path=$7
    instances_path=$8
    
    name_truncated=${name//-my/}

    mkdir $archive_path/${app}-${name_truncated}/$db_type/sites
    scp -r root@localhost:$instances_path/$instance/sites/${name}.$domain/* $archive_path/${app}-${name_truncated}/$db_type/sites/
    exit
    ;;

  get_version)
    app=$2
    name=$3
    domain=$4
    instances_path=$5
    archive_path=$6

    cd $instances_path/${app}-${name}/sites/${name}.${domain}
    version=$(drush status | grep 'Drupal version')
    version=${version//[^0-9.]/}
    version=$version.`date +%Y%m%d`
    echo $version > $archive_path/${app}-${name}/VERSION.txt
    exit
    ;;

  ?)
    exit
    ;;
esac

