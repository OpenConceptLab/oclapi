FROM python:2.7.13
ENV PYTHONUNBUFFERED 1

RUN mkdir /code
ADD . /code/
WORKDIR /code

RUN pip install -r requirements.txt

RUN echo deb http://apt.newrelic.com/debian/ newrelic non-free >> /etc/apt/sources.list.d/newrelic.list && \
    wget -O- https://download.newrelic.com/548C16BF.gpg | apt-key add - && \
    apt-get update  && \
    apt-get install newrelic-sysmond

EXPOSE 8000

CMD bash startup.sh