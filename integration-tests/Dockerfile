FROM node:8.16.0-alpine

RUN mkdir /code
WORKDIR /code

COPY package.json package-lock.json ./
RUN npm install

COPY . .

ARG url=http://localhost:8000/
ARG adminUser=root
ARG adminPassword=Root123
RUN npm t --url=$url --adminUser=$adminUser --adminPassword=$adminPassword
