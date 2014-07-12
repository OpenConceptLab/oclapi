from __future__ import with_statement
import os
from fabric.api import local, settings, abort, run, cd
from fabric.state import env

__author__ = 'misternando'

BACKUP_DIR = '/var/backups/ocl'
CHECKOUT_DIR = '/var/tmp'
DEPLOY_DIR = '/opt/deploy/django'

env.user = os.environ['FAB_USER']
env.password = os.environ['FAB_PASSWORD']
env.hosts = [os.environ['OCL_STAGING_HOST']]


def hello(name="World"):
    print("Hello %s" % name)


def test_local():
    local("./manage.py test users")


def backup():
    with cd(DEPLOY_DIR):
        run("tar -czvf ocl_`date +%Y%m%d`.tgz ocl")
        run("mv ocl_*.tgz %s" % BACKUP_DIR)
        run("rm -rf ocl")


def checkout():
    with cd(CHECKOUT_DIR):
        run("rm -rf oclapi")
        run("git clone https://github.com/OpenConceptLab/oclapi.git")
        run("cp -r oclapi/django-nonrel/ocl /opt/deploy/django")


def deploy():
    backup()
    checkout()
