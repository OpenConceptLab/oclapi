#!/bin/bash

cd ~/oclapi/django-nonrel/ocl && docker-compose build && docker-compose up -d

iptables -A DOCKER 1 -p tcp ! -s 172.18.0.0/16 -p tcp -m tcp --dport 6379 -j DROP
iptables -A DOCKER 1 -p tcp ! -s 172.18.0.0/16 -p tcp -m tcp --dport 8983 -j DROP
iptables -A DOCKER 1 -p tcp ! -s 172.18.0.0/16 -p tcp -m tcp --dport 8000 -j DROP
iptables -A DOCKER 1 -p tcp ! -s 172.18.0.0/16 -p tcp -m tcp --dport 5555 -j DROP
iptables -A DOCKER 1 -p tcp ! -s 172.18.0.0/16 -p tcp -m tcp --dport 27017 -j DROP

iptables-save