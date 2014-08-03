from __future__ import with_statement
import os
from fabric.api import local, settings, abort, run, cd
from fabric.context_managers import prefix
from fabric.operations import sudo
from fabric.state import env

__author__ = 'misternando'

BACKUP_DIR = '/var/backups/ocl'
CHECKOUT_DIR = '/var/tmp'
DEPLOY_DIR = '/opt/deploy'

env.user = os.environ['FAB_USER']
env.password = os.environ['FAB_PASSWORD']
env.hosts = [os.environ['OCL_STAGING_HOST']]


def hello(name="World"):
    print("Hello %s" % name)


def test_local():
    local("./manage.py test users")
    local("./manage.py test orgs")
    local("./manage.py test sources")
    local("./manage.py test concepts")
    local("./manage.py test mappings")


def backup():
    with cd(DEPLOY_DIR):
        run("tar -czvf ocl_`date +%Y%m%d`.tgz django solr/collection1/conf")
        run("mv ocl_*.tgz %s" % BACKUP_DIR)
        run("rm -rf django solr/collection1/conf")


def checkout():
    with cd(CHECKOUT_DIR):
        run("rm -rf oclapi")
        run("git clone https://github.com/OpenConceptLab/oclapi.git")


def provision():
    with cd(CHECKOUT_DIR):
        run("cp -r oclapi/django-nonrel %s/django" % DEPLOY_DIR)
        run("cp -r oclapi/solr/collection1/conf %s/solr/collection1" % DEPLOY_DIR)
        sudo("chown -R solr:wheel %s/solr" % DEPLOY_DIR)
    with cd("%s/django/ocl" % DEPLOY_DIR):
        run("cp settings.py.deploy settings.py")
        with prefix("source /opt/virtualenvs/ocl/bin/activate"):
            run("pip install -r requirements.txt")
            run("./manage.py build_solr_schema > /opt/deploy/solr/collection1/conf/schema.xml")
            sudo('/etc/init.d/jetty restart')
            run("./manage.py rebuild_index")


def restart():
    sudo('/etc/init.d/httpd restart')


def deploy():
    backup()
    checkout()
    provision()
    restart()
