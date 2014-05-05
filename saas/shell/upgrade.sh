#!/bin/bash

usage()
{
cat << EOF
usage: $0 options

This script run the test1 or test2 over a machine.

OPTIONS:
   -h      Show this message
   -t      Test type, can be ‘test1' or ‘test2'
   -r      Server address
   -p      Server root password
   -v      Verbose
EOF
}


while getopts "ht:p:a:n:c:u:s:e:r:d:bkz" OPTION;
do
     case $OPTION in
         h)
             usage
             exit 1
             ;;
         t)
             title=$OPTARG
             ;;
         a)
             admin_user=$OPTARG
             ;;
         p)
             admin_password=$OPTARG
             ;;
         n)
             instance=$OPTARG
             ;;
         c)
             archive_path=$OPTARG
             ;;
         u)
             user_name=$OPTARG
             ;;
         s)
             user_password=$OPTARG
             ;;
         e)
             user_mail=$OPTARG
             ;;
         r)
             server=$OPTARG
             ;;
         d)
             database_server=$OPTARG
             ;;
         k)
             skip_analytics=True
             ;;
         b)
             build=True
             archive='wikicompare_preprod'
             ;;
         z)
             test=True
             ;;
         ?)
             usage
             exit
             ;;
     esac
done

pear upgrade drush/drush

cd $website_path
result_wikicompare=$(drush sql-query "select n.title, fn.title, fndni.wikicompare_ip_value from node n 
INNER JOIN field_data_wikicompare_instance f ON n.nid=f.entity_id 
INNER JOIN node fn ON f.wikicompare_instance_target_id = fn.nid
INNER JOIN field_data_wikicompare_server fnd ON fn.nid=fnd.entity_id
INNER JOIN node fndn ON fnd.wikicompare_server_target_id = fndn.nid
INNER JOIN field_data_wikicompare_ip fndni ON fndn.nid=fndni.entity_id 
WHERE fn.title = '$1' AND fndn.title = '$2'  LIMIT 1")
i=0
wikicompare_name=''
instance_name=''
IP=''
for row_wikicompare in $result_wikicompare
do
  if [[ $i == 3 ]]
  then
    wikicompare_name=$row_wikicompare
  elif [[ $i == 4 ]]
  then
    instance_name=$row_wikicompare
  elif [[ $i == 5 ]]
  then
    IP=$row_wikicompare
  fi
  let i++
done
IP=${IP//[^0-9.]/}
echo wikicompare_name $wikicompare_name
echo instance_name $instance_name
echo ip $IP


if ssh www-data@$IP stat /var/www/$1 \> /dev/null 2\>\&1
then
  echo ok
else
  echo "No $1 instance, no upgrade"
  return
fi

ssh www-data@$IP << EOF
mkdir /var/www/$1/../sites_${1}_temp
cp -r /var/www/$1/sites/* /var/www/$1/../sites_${1}_temp
EOF

if [[ $wikicompare_name != '' ]]
then
domain_name=${wikicompare_name//_/-}

filename=`date +%Y-%m-%d_%H-%M`_upgrade_${1}_`date +%H-%M`.tar.gz
ssh www-data@$IP << EOF
cd /var/www/$1/sites/$domain_name.wikicompare.info
drush archive-dump @sites --destination=/var/wikicompare/backups/prepare/$filename
EOF
scp www-data@$IP:/var/wikicompare/backups/prepare/$filename /var/wikicompare/backups/$filename
ssh www-data@$IP << EOF
rm /var/wikicompare/backups/prepare/$filename
EOF
ncftp -u  $ftpuser -p $ftppass $ftpserver<< EOF
put /var/wikicompare/backups/$filename
EOF
fi


ssh www-data@$IP << EOF
rm -rf /var/www/$1/*
cd /var/www/$1
wget -q http://www.wikicompare.info/download/$archive/archive.tar.gz
tar -xf archive.tar.gz -C /var/www/$1
rm archive.tar.gz
rm -rf /var/www/$1/sites/*
cp -r /var/www/$1/../sites_${1}_temp/* /var/www/$1/sites/
rm -rf /var/www/$1/../sites_${1}_temp
EOF

ssh www-data@$IP << EOF
cd /var/www/$1/sites/
find . -name '*.wikicompare.info' -exec bash -c 'cd /var/www/$1/sites/{}; drush updatedb' \;
EOF

cd $website_path
version=$(curl http://www.wikicompare.info/download/$archive/VERSION.txt)
drush $module_path/wikicompare.script upgrade $1 $version