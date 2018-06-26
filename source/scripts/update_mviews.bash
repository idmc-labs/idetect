#!/bin/bash

echo "REFRESH MATERIALIZED VIEW idetect_fact_api_locations" | psql -h localdb -U idetect
echo "REFRESH MATERIALIZED VIEW idetect_fact_api" | psql -h localdb -U idetect
echo "REFRESH MATERIALIZED VIEW idetect_map_week_mview" | psql -h localdb -U idetect