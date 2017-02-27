#!/usr/bin/env bash
if [ -z $1 ]; then exit 0; fi;

APIKEY=$1

echo deb http://apt.newrelic.com/debian/ newrelic non-free >> /etc/apt/sources.list.d/newrelic.list
wget -O- https://download.newrelic.com/548C16BF.gpg | apt-key add -
apt-get update
apt-get install newrelic-sysmond
nrsysmond-config --set license_key=$APIKEY
newrelic-admin generate-config $APIKEY newrelic-api.ini
sed -i -e's/app_name = Python Application/app_name = OCL API/' newrelic-api.ini
/etc/init.d/newrelic-sysmond start