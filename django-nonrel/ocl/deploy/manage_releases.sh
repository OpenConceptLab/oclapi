#!/bin/bash

clear_releases() {
  RELEASES_DIR=$1
  if [ -z $1 ]; then RELEASES_DIR="~/releases/"; fi;

  find $RELEASES_DIR -type f -name "oclapi*.tgz" -mtime +30 -exec rm -f {} \;
}