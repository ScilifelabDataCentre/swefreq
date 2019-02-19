#!/usr/bin/env bash
set -x

PSQL_VERSION="10"
PSQL_PORT="5433"

docker pull postgres:"${PSQL_VERSION}"

docker run --rm -d -p $PSQL_PORT:5432 postgres:"${PSQL_VERSION}"
