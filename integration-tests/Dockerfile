FROM node:8.16.0-alpine

RUN mkdir /code
WORKDIR /code

COPY package.json package-lock.json ./
RUN npm install

RUN apk add --no-cache curl

COPY . .

ARG url=http://localhost:8000/
ARG adminUser=root
ARG adminPassword=Root123
ARG endpoint="admin/authtoken/token/"

ARG CACHEBUST=1
RUN ./wait_for_url.sh $url$endpoint && npm t --url=$url --adminUser=$adminUser --adminPassword=$adminPassword
