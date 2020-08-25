#!/bin/bash

# Environment variables required by psql
export PGUSER=${DB_USER}
export PGPASSWORD=${DB_PASSWORD}
export PGDATABASE=${DB_NAME}
export PGHOST=${DB_HOST}
export PGPORT=${DB_PORT}

set -x
psql -c "REFRESH MATERIALIZED VIEW idetect_map_mview;"
psql -c "REFRESH MATERIALIZED VIEW idetect_map_week_mview;"
psql -c "REFRESH MATERIALIZED VIEW idetect_fact_api_locations"
psql -c "REFRESH MATERIALIZED VIEW idetect_fact_api"
set +x
