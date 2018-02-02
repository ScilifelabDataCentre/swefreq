#!/bin/bash

# After this script has run you can run the container like this for example
#
#  $ export MYSQL_PORT=3367
#  $ docker run -v $VOLUME:/var/lib/mysql --rm --name mysql -d -p $MYSQL_PORT:3306 mysql:5.7 >/dev/null

VOLUME='mysql-data-volume'

echo "Downloading data"
curl -O https://swefreq.nbis.se/static/testing/mysql-data.tar.bz2 
tar xjf mysql-data.tar.bz2

echo "Creating datavolume and filling it with data"
docker volume create $VOLUME > /dev/null
docker run -v $VOLUME:/var/lib/mysql --rm -d --name loader ubuntu:16.04 sleep infinity
cd mysql-data
docker cp . loader:/var/lib/mysql/
cd ..
docker stop loader
