#!/usr/bin/env bash
set -xe

## SETUP SETTINGS
cp settings_sample.json settings.json
sed -i.tmp 's/"postgresHost" : "postgres host"/"postgresHost" : "127.0.0.1"/' settings.json
sed -i.tmp 's/"postgresPort" : 5432/"postgresPort" : 5433/' settings.json

echo "SETTINGS"
cat settings.json
echo "/SETTINGS"

echo ">>> Test 1. The SQL Patch"

LATEST_RELEASE=$(git tag | grep '^v' | sort -V | tail -n 1)
git show ${LATEST_RELEASE}:sql/*_schema.sql > master-schema.sql

psql -U postgres -h 127.0.0.1 -p 5433 -f master-schema.sql
psql -U postgres -h 127.0.0.1 -p 5433 -f sql/patch-master-db.sql

# Empty the database
psql -U postgres -h 127.0.0.1 -p 5433 <<__END__
DROP SCHEMA data;
DROP SCHEMA users;
__END__


echo ">>> Test 2. Load the swefreq schema"
psql -U postgres -h 127.0.0.1 -p 5433 -f sql/data_schema.sql
psql -U postgres -h 127.0.0.1 -p 5433 -f sql/user_schema.sql
psql -U postgres -h 127.0.0.1 -p 5433 -f test/data/load_dummy_data.sql

echo ">>> Test 3. Check that the backend starts"

(cd backend && ../test/01_daemon_starts.sh)


echo ">>> Test 4. the backend API"
coverage run backend/route.py --port=4000 --develop 1>http_log.txt 2>&1 &
BACKEND_PID=$!

sleep 2 # Lets wait a little bit so the server has started

exit_handler() {
    rv=$?
    # Ignore errors in the exit handler
    set +e
    # We want to make sure the background process has stopped, otherwise the
    # travis test will stall for a long time.
    kill -9 $BACKEND_PID

    echo "THE HTTP LOG WAS:"
    cat http_log.txt
    exit $rv
}

trap exit_handler EXIT


python backend/test.py -v

# Quit the app
curl localhost:4000/developer/quit
sleep 2 # Lets wait a little bit so the server has stopped

if [ -f .coverage ]; then
    coveralls
    coverage report
fi
