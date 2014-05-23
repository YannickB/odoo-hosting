#!/bin/bash

application_type=$1
application=$2
instance=$3
system_user=$4
server=$5
version=$6
instances_path=$7
openerp_path=$8
archive_path=$9

if ssh $system_user@$server stat $instances_path/$instance \> /dev/null 2\>\&1
then
  echo ok
else
  echo "No $instance instance, no upgrade"
  return
fi

$openerp_path/saas/saas/apps/$application_type/upgrade.sh pre_upgrade $instance $system_user $server $instances_path
echo after pre_upgrade

ssh $system_user@$server << EOF
rm -rf $instances_path/$instance/*
EOF

scp $archive_path/$application/versions/$version/archive.tar.gz $system_user@$server:$instances_path/$instance/

ssh $system_user@$server << EOF
cd $instances_path/$instance
tar -xf archive.tar.gz -C $instances_path/$instance
rm archive.tar.gz
EOF

echo before post_upgrade
$openerp_path/saas/saas/apps/$application_type/upgrade.sh post_upgrade $instance $system_user $server $instances_path

