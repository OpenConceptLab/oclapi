#!/usr/bin/env bash
if [ -z $1 ]; then exit 0; fi;

APIKEY=$1
nrsysmond-config --set license_key=$APIKEY
newrelic-admin generate-config $APIKEY newrelic-api.ini
sed -i -e's/app_name = Python Application/app_name = OCL API/' newrelic-api.ini
/etc/init.d/newrelic-sysmond start