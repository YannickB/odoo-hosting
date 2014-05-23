#!/bin/bash

# usage()
# {
# cat << EOF
# usage: $0 options

# This script run the test1 or test2 over a machine.

# OPTIONS:
   # -h      Show this message
   # -t      Test type, can be ‘test1' or ‘test2'
   # -r      Server address
   # -p      Server root password
   # -v      Verbose
# EOF
# }


# while getopts "ht:p:a:n:c:u:s:e:r:d:bkz" OPTION;
# do
     # case $OPTION in
         # h)
             # usage
             # exit 1
             # ;;
         # t)
             # title=$OPTARG
             # ;;
         # a)
             # admin_user=$OPTARG
             # ;;
         # p)
             # admin_password=$OPTARG
             # ;;
         # n)
             # instance=$OPTARG
             # ;;
         # c)
             # archive_path=$OPTARG
             # ;;
         # u)
             # user_name=$OPTARG
             # ;;
         # s)
             # user_password=$OPTARG
             # ;;
         # e)
             # user_mail=$OPTARG
             # ;;
         # r)
             # server=$OPTARG
             # ;;
         # d)
             # database_server=$OPTARG
             # ;;
         # k)
             # skip_analytics=True
             # ;;
         # b)
             # build=True
             # archive='wikicompare_preprod'
             # ;;
         # z)
             # test=True
             # ;;
         # ?)
             # usage
             # exit
             # ;;
     # esac
# done 
 
 
save_dump()
{


$openerp_path/saas/saas/apps/$application_type/save.sh save_dump $application $saas_names $filename $server $database_server $instance $system_user $backup_directory $instances_path

scp $system_user@$server:$backup_directory/backups/prepare/${filename}.tar.gz $backup_directory/backups/${filename}.tar.gz
ssh $system_user@$server << EOF
rm $backup_directory/backups/prepare/${filename}.tar.gz
EOF

ncftp -u  $ftpuser -p $ftppass $ftpserver<< EOF
    put $backup_directory/backups/${filename}.tar.gz
EOF

}



save_after()
{

echo ncftp -u $ftpuser -p $ftppass $ftpserver

filename=`date +%Y-%m-%d -d '5 days ago'`-*
echo $filename
ncftp -u $ftpuser -p $ftppass $ftpserver<<EOF
rm $filename
EOF

ssh $shinken_server << EOF
ncftpget -u $ftpuser -p$ftppass -R $ftpserver $backup_directory/control_backups ./*
cd $backup_directory/control_backups
pwd
find . -name '*.tar.gz' -exec bash -c 'mkdir \`basename {} .tar.gz\`; tar -zxf {} -C \`basename {} .tar.gz\`' \;
rm *.tar.gz
EOF

find $backup_directory/backups/ -type f -mtime +4 | xargs -r rm

}


# cd $website_path
# filename=`date +%Y-%m-%d`_${letscoop_type}_www.tar.gz
# rm /var/wikicompare/backups/$filename
# drush archive-dump --destination=/var/wikicompare/backups/$filename
# ncftp -u  $ftpuser -p $ftppass $ftpserver<< EOF
# rm $filename
# put /var/wikicompare/backups/$filename
# EOF
# echo website saved

# if [[ $letscoop_type != 'wezer' ]]
# then
# filename=`date +%Y-%m-%d`_wikicompare_analytics.tar.gz
# rm /var/wikicompare/backups/$filename
# ssh $piwik_server << EOF
# mkdir /var/wikicompare/backups/prepare/piwik_temp
# mkdir /var/wikicompare/backups/prepare/piwik_temp/wikicompare_analytics
# cp -r /var/www/piwik/* /var/wikicompare/backups/prepare/piwik_temp/wikicompare_analytics
# mysqldump -u piwik -p$piwik_password piwik > /var/wikicompare/backups/prepare/piwik_temp/wikicompare_analytics.sql
# cd /var/wikicompare/backups/prepare/piwik_temp
# tar -czf ../$filename ./*
# cd ../
# rm -rf /var/wikicompare/backups/prepare/piwik_temp
# EOF

# scp $piwik_server:/var/wikicompare/backups/prepare/$filename /var/wikicompare/backups/$filename
# ssh $piwik_server << EOF
# rm /var/wikicompare/backups/prepare/$filename
# EOF
# ncftp -u  $ftpuser -p $ftppass $ftpserver<< EOF
# rm $filename
# put /var/wikicompare/backups/$filename

# EOF
# echo piwik saved
# fi

save_remove()
{

rm $backup_directory/backups/${filename}.tar.gz

ncftp -u $ftpuser -p $ftppass $ftpserver<<EOF
rm ${filename}.tar.gz
EOF

ssh $shinken_server << EOF
rm -rf $backup_directory/control_backups/$filename
EOF

}

case $1 in
  save_dump)

    application_type=$2
    application=$3
    saas_names=$4
    filename=$5
    server=$6
    database_server=$7
    instance=$8
    system_user=$9
    backup_directory=${10}
    instances_path=${11}
    openerp_path=${12}
    ftpuser=${13}
    ftppass=${14}
    ftpserver=${15}

    save_dump
    exit
    ;;

  save_prepare)

    backup_directory=$2
    shinken_server=$3

    ssh $shinken_server << EOF
    rm -rf $backup_directory/control_backups/*
EOF

    exit
    ;;

  save_after)

    backup_directory=$2
    shinken_server=$3
    ftpuser=$4
    ftppass=$5
    ftpserver=$6

    save_after
    exit
    ;;

  save_remove)
    filename=$2
    backup_directory=$3
    shinken_server=$4
    ftpuser=$5
    ftppass=$6
    ftpserver=$7

    save_remove
    exit
    ;;

  ?)
    exit
    ;;
esac
