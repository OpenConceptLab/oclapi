mkdir -p ~/backups

MONGO_IP=`docker inspect --format '{{ .NetworkSettings.Networks.ocl_default.IPAddress }}' ocl_mongo`

rm -rf /tmp/mongodump && mkdir /tmp/mongodump
docker run -it --rm --link ocl_mongo:mongo --net=ocl_default -v /tmp/mongodump:/tmp mongo bash -c "mongodump -v --host `$MONGO_IP`:27017 --db ocl --out=/tmp"
tar -cvf ~/backups/mongo_`date +"%Y%m%d%H%M%S"` -C /tmp/mongodump *
rm -rf /tmp/mongodump