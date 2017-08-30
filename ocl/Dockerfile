FROM python:2.7.13
ENV PYTHONUNBUFFERED 1

RUN mkdir /code
ADD . /code/
WORKDIR /code

RUN pip install -r requirements.txt

EXPOSE 8000

CMD bash startup.sh