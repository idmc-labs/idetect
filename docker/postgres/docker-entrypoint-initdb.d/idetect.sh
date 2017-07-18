#!/bin/bash
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" <<-EOSQL
    CREATE USER idetect WITH PASSWORD 'democracy';
    CREATE DATABASE idetect;
    GRANT ALL PRIVILEGES ON DATABASE idetect TO idetect;

    CREATE USER tester WITH PASSWORD 'tester';
    CREATE DATABASE idetect_test;
    GRANT ALL PRIVILEGES ON DATABASE idetect_test TO tester;
EOSQL
