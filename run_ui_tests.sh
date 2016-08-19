#!/bin/bash

cd ~/ocl_web
nohup phantomjs --webdriver=9515 > nohup_ui_tests.out  2>&1 &
sleep 3
./node_modules/protractor/bin/protractor ./ocl_web/tests/ui_tests/conf.js
