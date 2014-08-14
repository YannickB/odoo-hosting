#!/bin/bash



container_name=$1

directory=/opt/control-bup/restore/$container_name/latest

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



# if [[ ! (-s "${1/_/-}.wikicompare.info-wikicompare_${1}.sql" || -s "${unique_name_underscore}.sql")  ]]
# then
  # echo "The database file ${unique_name_underscore}.sql is empty."
  # exit 2
# fi

echo "Backup of ${container_name} OK"
exit 0
