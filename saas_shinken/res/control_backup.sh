#!/bin/bash


directory=/opt/control-bup/restore/$2/latest

date=`date +%Y-%m-%d`
date_save=`cat $directory/backup-date`

if [[ ! -d "$directory" ]]
then
  echo "$repo_name backup missing."
  exit 2
fi

if [[ $date != $date_save ]]
then
  echo "No backup for today."
  exit 2
fi

if [[ $1 == 'base' ]]
then

  if [[ ! (-s "${directory}/${2}.dump")  ]]
  then
    echo "The database file ${2}.dump is empty."
    exit 2
  fi

fi

echo "Backup of ${2} OK"
exit 0
