FROM python:2.7.13
ENV PYTHONUNBUFFERED 1

RUN apt-get update --fix-missing
RUN apt-get install -y openssh-server
RUN apt-get install -y sudo
RUN mkdir /var/run/sshd
RUN echo 'root:Root123' | chpasswd
RUN sed -i 's/PermitRootLogin without-password/PermitRootLogin yes/' /etc/ssh/sshd_config

# SSH login fix. Otherwise user is kicked off after login
RUN sed 's@session\s*required\s*pam_loginuid.so@session optional pam_loginuid.so@g' -i /etc/pam.d/sshd

# ENV NOTVISIBLE "in users profile"
RUN echo "export VISIBLE=now" >> /etc/profile

# fix for pycharm debug ssh connection
RUN echo "KexAlgorithms=diffie-hellman-group1-sha1" >> /etc/ssh/sshd_config

# Allows sshd to read /root/.ssh/environment
RUN echo "PermitUserEnvironment=yes" >> /etc/ssh/sshd_config

EXPOSE 22

RUN touch /root/.bash_profile
RUN echo "cd /code" >> /root/.bash_profile

RUN mkdir /root/.ssh/
RUN touch /root/.ssh/environment

RUN mkdir /code
ADD . /code/
WORKDIR /code

RUN pip install -r requirements.txt

EXPOSE 8000

CMD bash startup.sh