#!/usr/bin/env bash
set -x

docker pull mysql:5.7
docker pull ubuntu:16.04

VOLUME='mysql-data-volume'
MYSQL_PORT=3366

test/docker-db/load_database_in_volume.sh
docker run -v $VOLUME:/var/lib/mysql --rm --name mysql -d -p $MYSQL_PORT:3306 mysql:5.7
