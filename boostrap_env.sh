apt-get update
apt-get install python2.7
apt-get install apt-transport-https ca-certificates
apt-key adv --keyserver hkp://p80.pool.sks-keyservers.net:80 --recv-keys 58118E89F3A912897C070ADBF76221572C52609D
echo "deb https://apt.dockerproject.org/repo ubuntu-xenial main" | sudo tee /etc/apt/sources.list.d/docker.list
apt-get update
apt-get purge lxc-docker
apt-cache policy docker-engine
apt-get install -y docker-engine
systemctl status docker
curl -L https://github.com/docker/compose/releases/download/1.8.0/docker-compose-`uname -s`-`uname -m` > /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose
docker-compose --version

apt-get install postgresql
apt-get install python-pip
apt-get install python-setuptools
easy_install virtualenv
apt-get install nodejs
apt-get install npm
