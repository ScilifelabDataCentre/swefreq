#!/bin/bash

MYSQL_PORT=3366
MYSQL_HOST=127.0.0.1
MYSQL_PASS=rootpw

if [ -d mysql-data ]; then
    echo "mysq-data dir already exists, exiting" >&2
    exit 1
fi


echo "Creating data volume and starting mysql:5.7 docker container"
docker volume create swefreq-mysql-data > /dev/null
docker run -v swefreq-mysql-data:/var/lib/mysql --rm --name mysql -e MYSQL_ROOT_PASSWORD=$MYSQL_PASS -d -p $MYSQL_PORT:3306  mysql:5.7 >/dev/null


# Wait for it to start
while ! mysql -uroot -p$MYSQL_PASS -h127.0.0.1 -P$MYSQL_PORT -e exit 2>/dev/null; do
    echo -ne "\rWaiting for mysql to initialize...";
    sleep 1;
done
echo " DONE";


echo "Creating swefreq user and swefreq_test database"
mysql -u root -P$MYSQL_PORT -h$MYSQL_HOST -p$MYSQL_PASS <<__END__
CREATE USER IF NOT EXISTS 'swefreq';
CREATE DATABASE IF NOT EXISTS swefreq_test;
GRANT ALL ON swefreq_test.* TO 'swefreq'@'%';
__END__


echo "Copy the mysql data volume"
docker cp mysql:/var/lib/mysql mysql-data
docker stop mysql
tar cjf mysql-data.tar.bz2 mysql-data
