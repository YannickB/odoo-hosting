#!/bin/bash



application=$1
server=$2
instance=$3
domain=$4
saas=$5

directory=/var/saas/control_backups/`date +%Y-%m-%d`-${server}-${instance}-auto
directory=${directory//./-}

unique_name=$application-$saas-$domain
unique_name=${unique_name//./-}
unique_name_underscore=${unique_name//-/_}
 


if [[ ! -d "$directory" ]]
then
  echo "$directory backup missing."
  exit 2
fi

cd $directory

# if [[ $letscoop_type != 'wezer' ]]
# then
# if [[ ! "$(ls -A $instance_name)" ]]
# then
  # echo "The instance directory $instance_name is empty."
  # exit 2
# fi
# fi

if [[ ! (-s "${1/_/-}.wikicompare.info-wikicompare_${1}.sql" || -s "${unique_name_underscore}.sql")  ]]
then
  echo "The database file ${unique_name_underscore}.sql is empty."
  exit 2
fi

echo "Backup of ${unique_name} OK"
exit 0
 
