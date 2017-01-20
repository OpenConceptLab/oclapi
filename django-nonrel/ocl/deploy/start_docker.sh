#!/bin/bash

cd ~/oclapi/django-nonrel/ocl && docker-compose build && docker-compose up -d

iptables -I DOCKER 1 -p tcp ! -s 172.18.0.0/16 --dport 6379 -j DROP
iptables -I DOCKER 1 -p tcp ! -s 172.18.0.0/16 --dport 8983 -j DROP
iptables -I DOCKER 1 -p tcp ! -s 172.18.0.0/16 --dport 8000 -j DROP
iptables -I DOCKER 1 -p tcp ! -s 172.18.0.0/16 --dport 5555 -j DROP
iptables -I DOCKER 1 -p tcp ! -s 172.18.0.0/16 --dport 27017 -j DROP

iptables-save