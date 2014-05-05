#!/bin/bash




case $1 in
  build_archive)

    app=$2
    name=$3
    archive_path=$4
    openerp_path=$5
    build_directory=$6


    echo create openerp archive
    echo $build_directory/$dir



    for dir in $build_directory/*
    do
        bzr pull -d $dir
    done

    mkdir $archive_path/${app}-${name}/archive
    cp -R $build_directory/* $archive_path/${app}-${name}/archive

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
    
    exit
    ;;

  get_version)
    app=$2
    name=$3
    domain=$4
    instances_path=$5

    version='1'
    echo $version
    exit
    ;;


  ?)
    exit
    ;;
esac