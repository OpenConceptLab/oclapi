#!/bin/bash

test_should_clear_oclapi_releases_when_files_older_than_one_month() {
  source $(pwd)/manage_releases.sh

  SEVEN_DAYS_AGO_FORMAT=$(date --date="-7 day" +"%Y%m%d%H%M.%S")
  SEVEN_DAYS_AGO_FILE_NAME=$(date --date="-7 day" +"%Y%m%d%H%M")
  FORTY_DAYS_AGO_FORMAT=$(date --date="-40 day" +"%Y%m%d%H%M.%S")
  FORTY_DAYS_AGO_FILE_NAME=$(date --date="-40 day" +"%Y%m%d%H%M")
  TMP_TEST_DIR="/tmp/test"

  mkdir -p $TMP_TEST_DIR/
  rm -f $TMP_TEST_DIR/*

  touch -a -m -t $SEVEN_DAYS_AGO_FORMAT $TMP_TEST_DIR/oclapi$SEVEN_DAYS_AGO_FILE_NAME.tgz
  touch -a -m -t $SEVEN_DAYS_AGO_FORMAT $TMP_TEST_DIR/otherfile$SEVEN_DAYS_AGO_FILE_NAME.tgz
  touch -a -m -t $FORTY_DAYS_AGO_FORMAT $TMP_TEST_DIR/oclapi$FORTY_DAYS_AGO_FILE_NAME.tgz
  touch -a -m -t $FORTY_DAYS_AGO_FORMAT $TMP_TEST_DIR/otherfile$FORTY_DAYS_AGO_FILE_NAME.tgz

  assert_equals "4" $(find $TMP_TEST_DIR/ -type f | wc -l) "Test directory should have 4 files"

  clear_releases $TMP_TEST_DIR/

  assert_equals "3" $(find $TMP_TEST_DIR/ -type f | wc -l) "Should clear older than 30 days files and test directory should have 2 files"

  rm -f $TMP_TEST_DIR/*
  rmdir $TMP_TEST_DIR
}