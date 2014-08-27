#!/bin/bash
IFS=","

repo=( $(ssh $3 cat /opt/backup/list/$4/repo) )

directory=/opt/backup/simple/$repo/latest
if [[ $1 == 'bup' ]]
then
    directory=/tmp/control-backup/$repo
    ssh $3 << EOF
      rm -rf $directory
      mkdir -p $directory
      export BUP_DIR=/opt/backup/bup
      bup restore -C $directory $repo/latest
EOF
    directory=/tmp/control-backup/$repo/latest
fi


if ! ssh $3 "[ -d $directory ]"
then
  echo "$4 backup missing."
  exit 2
fi


date=`date +%Y-%m-%d`
date_save=( $(ssh $3 cat $directory/backup-date) )
if [[ $date != $date_save ]]
then
  echo "No backup for today."
  exit 2
fi

if [[ $2 == 'base' ]]
then
  for database in $5
  do
    if ! ssh $3 "[ -s $directory/${database}.dump ]"
    then
      echo "The database file ${database}.dump is empty."
      exit 2
    fi
  done
fi



if [[ $1 == 'bup' ]]
then
    directory=/tmp/control-backup/$repo
    ssh $3 << EOF
      rm -rf $directory
EOF
fi

echo "Backup of ${4} OK"
exit 0
