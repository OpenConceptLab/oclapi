#!/bin/bash -e

MONGO_IP=`docker inspect --format '{{ .NetworkSettings.Networks.ocl_default.IPAddress }}' ocl_mongo`

TMP_DIR="/tmp/mongorestore/"
rm -rf $TMP_DIR && mkdir $TMP_DIR
if [[ $1 =~ \.tar$ ]];
then
        #FILENAME=$(echo $1 | sed 's/.*\///')
        FILENAME=ocl/
        mkdir $TMP_DIR
        echo "Data will be extracted into :"$TMP_DIR
        tar -C $TMP_DIR -xvf $1
else
        FILENAME=$(echo $1 | sed 's/.*\///')
        cp $1 $TMP_DIR$FILENAME
fi

docker run -it --rm --link ocl_mongo:mongo --net=ocl_default -v $TMP_DIR:/tmp mongo bash -c 'mongorestore --drop -v --host `echo $MONGO_IP`:27017 --db ocl /tmp/'$FILENAME
rm -rf $TMP_DIR

#usage is ./mongo-restore.sh ~/backups/<filename>.tar