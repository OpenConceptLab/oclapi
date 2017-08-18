"""
    Control API server

    e.g.

    # to checkout code to the API server on dev
    fab dev checkout

    # to restart the staging API server
    fab staging restart

"""
from __future__ import with_statement
from time import sleep
from fabric.api import local, run, cd
from fabric.context_managers import prefix
from fabric.operations import sudo
from fabric.state import env

__author__ = 'misternando'

BACKUP_DIR = '/var/backups/ocl'
CHECKOUT_DIR = '/var/tmp'
DEPLOY_DIR = '/opt/deploy'


def dev():
    """
    Make this the first task when calling fab to
    perform operations on dev machine.
    This "task" defines key variables for all the operations on that
    particular server.

    e.g.:
        fab dev release_web_app
    """
    env.hosts = ['dev.openconceptlab.org', ]
    env.user = 'deploy'
    env.web_domain = 'dev.openconceptlab.com'
    env.api_domain = 'api.dev.openconceptlab.com'


def staging():
    """
    Make this the first task when calling fab to
    perform operations on staging machine.
    """
    env.hosts = ['staging.openconceptlab.org', ]
    env.user = 'deploy'
    env.web_domain = 'staging.openconceptlab.com'
    env.api_domain = 'api.staging.openconceptlab.com'


def production():
    """
    Make this the first task when calling fab to
    perform operations on staging machine.
    """
    env.hosts = ['www.openconceptlab.org', ]
    env.user = 'deploy'


def hello(name="World"):
    print("Hello %s" % name)


def test_local():
    local("./manage.py test users")
    local("./manage.py test orgs")
    local("./manage.py test sources")
    local("./manage.py test collection")
    local("./manage.py test concepts")
    local("./manage.py test mappings")


def backup():
    """ Backup source to /var/backups/ocl """
    with cd(DEPLOY_DIR):
        run("tar -czvf ocl_`date +%Y%m%d`.tgz ocl_api solr/collection1/conf")
        run("mv ocl_*.tgz %s" % BACKUP_DIR)
        run("rm -rf ocl_api solr/collection1/conf")


def checkout():
    with cd(CHECKOUT_DIR):
        run("rm -rf oclapi")
        run("git clone https://github.com/OpenConceptLab/oclapi.git")


def provision():
    with cd(CHECKOUT_DIR):
        run("cp -r oclapi/django-nonrel %s/ocl_api" % DEPLOY_DIR)
        run("cp -r oclapi/solr/collection1/conf %s/solr/collection1" % DEPLOY_DIR)

    with cd("%s/ocl_api/ocl" % DEPLOY_DIR):
        run("cp common.py.deploy common.py")
        with prefix("source /opt/virtualenvs/ocl_api/bin/activate"):
            run("pip install -r requirements.txt")
            # commenting these out now, takes too long
            # run("./manage.py test users")
            # run("./manage.py test orgs")
            # run("./manage.py test sources")
            # run("./manage.py test collection")
            # run("./manage.py test concepts")
            run("./manage.py build_solr_schema > /opt/deploy/solr/collection1/conf/schema.xml")
            sudo('/etc/init.d/jetty restart')
            sleep(5)
            run("./manage.py rebuild_index")


def restart():
    """ Restart API server """
    run('supervisorctl restart ocl_api')


def deploy():
    backup()
    checkout()
    provision()
    restart()
