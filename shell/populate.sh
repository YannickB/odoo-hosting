#!/bin/bash




case $1 in

  populate)

    application=$2
    preprod_archive=$3
    prod_archive=$4
    archive_path=$5

    if [[ ! -d "$archive_path/$application/versions" ]]
    then
    mkdir $archive_path/$application
    mkdir $archive_path/$application/versions
    fi


    rm -rf $archive_path/$application/$prod_archive
    mkdir $archive_path/$application/$prod_archive
    cp -r $archive_path/$application/$preprod_archive/* $archive_path/$application/$prod_archive


    version=$(cat $archive_path/$application/$prod_archive/VERSION.txt)
    if [[ $version != '' ]]
    then
      rm -rf $archive_path/$application/versions/$version
      mkdir $archive_path/$application/versions/$version
      cp -r $archive_path/$application/$prod_archive/* $archive_path/$application/versions/$version/
    fi

    exit
    ;;

  remove_version)
    application=$2
    version=$3
    archive_path=$4

    rm -rf $archive_path/$application/versions/$version

    exit
    ;;



  ?)
    exit
    ;;
esac