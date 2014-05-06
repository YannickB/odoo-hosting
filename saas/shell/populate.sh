#!/bin/bash

application=$1
preprod_archive=$2
prod_archive=$3
archive_path=$4

if [[ ! -d "$archive_path/$application-old-releases" ]]
then
mkdir $archive_path/$application-old-releases
fi

if [[ ! -d "$archive_path/$prod_archive" ]]
then
version=$(cat $archive_path/$prod_archive/VERSION.txt)
rm -rf $archive_path/$application-old-releases/$version
mkdir $archive_path/$application-old-releases/$version
cp -r $archive_path/$prod_archive/* $archive_path/$application-old-releases/$version/
fi
rm -rf $archive_path/$prod_archive
mkdir $archive_path/$prod_archive
cp -r $archive_path/$preprod_archive/* $archive_path/$prod_archive
