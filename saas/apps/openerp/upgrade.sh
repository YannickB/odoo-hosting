#!/bin/bash




case $1 in
  pre_upgrade)
    instance=$2
    system_user=$3
    server=$4
    instances_path=$5


    exit
    ;;

  post_upgrade)
    instance=$2
    system_user=$3
    server=$4
    instances_path=$5

    exit
    ;;

  ?)
    exit
    ;;
esac
