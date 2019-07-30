#!/bin/sh

if [ "$1" != "" ]; then
  url=$1
else
  echo "Usage: ./wait_for_url.sh url [max_attempts]"
  exit 1
fi

if [ "$2" != "" ]; then
  max_attempts=$2
else
  max_attempts=60
fi

echo "Waiting for $1"

attempt_counter=0
until $(curl --output /dev/null --silent --head --fail $url); do
  if [ ${attempt_counter} -eq ${max_attempts} ];then
    echo "Max attempts reached"
    exit 1
  fi
  printf '.'
  attempt_counter=$(($attempt_counter+1))
  sleep 5
done
