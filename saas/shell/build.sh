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
 
 





build_archive()
{
echo $archive_path/${app}-${name}
rm -rf $archive_path/${app}-${name}
mkdir $archive_path/${app}-${name}
cd $archive_path/${app}-${name}

$openerp_path/saas/saas/apps/$application_type/build.sh build_archive $app $name $archive_path $openerp_path $build_directory

cd $archive_path/${app}-${name}/archive
tar -czf ../archive.tar.gz ./* 
cd ../
echo 'temp' > VERSION.txt

chmod -R 777 $archive_path/${app}-${name}/*


}

build_copy()
{

rm -rf $archive_path/${app}-${name}
mkdir $archive_path/${app}-${name}
cp -R $archive_path/${app}-${name_source}/* $archive_path/${app}-${name}

ssh root@localhost << EOF
chmod -R 777 $archive_path/${app}-${name}/
EOF
}

build_dump()
{

unique_name=$application-$name-$domain
unique_name=${unique_name//./-}
unique_name_underscore=${unique_name//-/_}

db_user=${instance//-/_}

name_truncated=${name//-my/}


mkdir $archive_path/${application}-${name_truncated}/$db_type
ssh root@localhost << EOF
chmod -R 777 $archive_path/${application}-${name_truncated}/
EOF

$openerp_path/saas/saas/apps/$application_type/build.sh build_dump $application $name $instance $domain $db_type $archive_path $instances_path

echo Before dump
if [[ $db_type != 'mysql' ]]
then
ssh $system_user@$server << EOF
pg_dump -U $db_user -h $database_server -Fc --no-owner $unique_name_underscore > $archive_path/${application}-${name}/pgsql/build.sql
EOF
else
mysqldump -u root -p$mysql_password $unique_name_underscore > $archive_path/${application}-${name_truncated}/mysql/build.sql
fi
echo end dump

ssh root@localhost << EOF
chmod -R 777 $archive_path/${application}-${name_truncated}/
EOF
cp -R $archive_path/${application}-${name_truncated}/$db_type $archive_path/${application}-${name_truncated}/archive/
ssh $system_user@$server << EOF
mkdir $instances_path/$instance/$db_type
cp -R $archive_path/${application}-${name_truncated}/$db_type/* $instances_path/$instance/$db_type/
EOF

}



get_version()
{

$openerp_path/saas/saas/apps/$application_type/build.sh get_version $application $name $domain $instances_path $archive_path

}


build_after()
{

cp $archive_path/${application}-${name}/VERSION.txt $archive_path/${application}-${name}/archive/

cd $archive_path/${application}-${name}/
rm archive.tar.gz
cd archive/
tar -czf ../archive.tar.gz ./* 
cd ../
rm -rf archive
ssh root@localhost << EOF
  chown -R www-data $archive_path/${application}-${name}/*
  chmod -R 777 $archive_path/${application}-${name}/*
EOF


}





case $1 in
  build_archive)
    application_type=$2
    app=$3
    name=$4
    system_user=$5
    archive_path=$6
    openerp_path=$7
    build_directory=$8

    build_archive
    exit
    ;;

  build_copy)
    application_type=$2
    app=$3
    name=$4
    name_source=$5
    openerp_path=$6
    archive_path=$7

    build_copy
    exit
    ;;

  build_dump)
    application_type=$2
    application=$3
    name=$4
    domain=$5
    instance=$6
    system_user=$7
    server=$8
    database_server=$9
    db_type=${10}
    openerp_path=${11}
    archive_path=${12}
    instances_path=${13}
    mysql_password=${14}

    build_dump
    exit
    ;;

  get_version)
    application_type=$2
    application=$3
    name=$4
    domain=$5
    openerp_path=$6
    instances_path=$7
    archive_path=$8

    get_version
    exit
    ;;

  build_after)
    application_type=$2
    application=$3
    name=$4
    version=$5
    openerp_path=$6
    archive_path=$7

    build_after
    exit
    ;;


  ?)
    exit
    ;;
esac