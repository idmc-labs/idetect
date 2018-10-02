-- idetect_fact_api_locations
--TODO this can also be replaced by either a sequence or md5 hash of location names
DROP MATERIALIZED VIEW if EXISTS idetect_fact_api;
DROP MATERIALIZED VIEW if EXISTS idetect_fact_api_locations;
CREATE MATERIALIZED VIEW idetect_fact_api_locations AS
WITH fact_locations AS (
         SELECT idetect_fact_locations.fact,
            sort(array_agg(idetect_fact_locations.location)) AS location_ids,
            array_agg(idetect_locations.location_name) AS location_names
           FROM (idetect_fact_locations
             LEFT JOIN idetect_locations ON ((idetect_fact_locations.location = idetect_locations.id)))
          WHERE (idetect_fact_locations.location IS NOT NULL)
          GROUP BY idetect_fact_locations.fact
        ), location_ids_uniqueid AS (
         SELECT DISTINCT ON (fact_locations_1.location_ids) fact_locations_1.location_ids,
            row_number() OVER (ORDER BY fact_locations_1.location_ids) AS location_ids_num
           FROM fact_locations fact_locations_1
        )
 SELECT fact_locations.fact,
    fact_locations.location_ids,
    fact_locations.location_names,
    location_ids_uniqueid.location_ids_num
   FROM (fact_locations
     LEFT JOIN location_ids_uniqueid USING (location_ids));
ALTER TABLE idetect_fact_api_locations OWNER TO idetect;
-- idetect_fact_api
CREATE MATERIALIZED VIEW idetect_fact_api AS (
          SELECT
    gkg.document_identifier,
    gkg.source_common_name,
    TO_DATE(SUBSTR((gkg.date)::text, 1, 8), 'YYYYMMDD'::text) AS gdelt_day,
    idetect_facts.id AS fact,
    idetect_facts.unit,
    idetect_facts.term,
    idetect_facts.specific_reported_figure,
    idetect_facts.vague_reported_figure,
    idetect_facts.iso3,
    idetect_fact_locations.location,
    idetect_analyses.gkg_id,
    idetect_analyses.category,
    idetect_analyses.content_id,
    idetect_fact_api_locations.location_ids_num
  from idetect_facts
  join idetect_analysis_facts ON idetect_facts.id = idetect_analysis_facts.fact
  join idetect_analyses ON idetect_analysis_facts.analysis = idetect_analyses.gkg_id
  join gkg ON gkg.id = idetect_analyses.gkg_id
  inner join idetect_fact_locations ON idetect_facts.id = idetect_fact_locations.fact
  join idetect_fact_api_locations ON idetect_fact_api_locations.fact=idetect_facts.id
  where idetect_analyses.category is not null
);
ALTER TABLE idetect_fact_api OWNER TO idetect;

CREATE INDEX idetect_fact_api_fact_day_idx on idetect_fact_api (fact,gdelt_day);
CREATE INDEX idetect_fact_api_loc_day_idx on idetect_fact_api (location, gdelt_day);
CREATE INDEX idetect_fact_api_day_loc_idx on idetect_fact_api (gdelt_day, location);
CREATE INDEX idetect_fact_api_loc_cat_idx on idetect_fact_api (location, category);
CREATE INDEX idetect_fact_api_day_cat_idx on idetect_fact_api (gdelt_day, category);
CREATE INDEX idetect_fact_api_cat_idx on idetect_fact_api (category);
CREATE INDEX idetect_fact_api_fact_hash ON idetect_fact_api USING HASH (fact);
CREATE INDEX idetect_fact_api_locations_fact_idx ON idetect_fact_api_locations (fact);
CREATE INDEX idetect_fact_api_locidsnum_idx ON idetect_fact_api (location_ids_num);

-- wordcloud

ALTER TABLE idetect_document_contents ADD COLUMN content_ts tsvector;

CREATE INDEX idetect_document_contents_gin
  ON idetect_document_contents using GIN (content_ts);

UPDATE idetect_document_contents
SET content_ts = to_tsvector('simple_english',
REGEXP_REPLACE(content_clean,'[0-9]|said|year|people|says|one|two', '','g'))
WHERE content_clean IS NOT NULL
AND content_ts IS NULL;

CREATE EXTENSION intarray;

-- index on document identifier to speedup search for analyse_url API
CREATE INDEX gkg_identifier_idx on gkg (document_identifier);

-- map_week_mview
CREATE MATERIALIZED VIEW idetect_map_week_mview AS (
          WITH input_table AS (
         SELECT date_trunc('week'::text, (to_date(substr((gkg.date)::text, 1, 8), 'YYYYMMDD'::text))::timestamp with time zone) AS gdelt_day,
            idetect_locations.id AS location_id,
            split_part((idetect_locations.latlong)::text, ','::text, 1) AS latitude,
            split_part((idetect_locations.latlong)::text, ','::text, 2) AS longitude,
            idetect_analyses.category,
            count(*) AS count
           FROM (((((idetect_facts
             JOIN idetect_fact_locations ON ((idetect_facts.id = idetect_fact_locations.fact)))
             JOIN idetect_locations ON ((idetect_fact_locations.location = idetect_locations.id)))
             JOIN idetect_analysis_facts ON ((idetect_facts.id = idetect_analysis_facts.fact)))
             JOIN idetect_analyses ON ((idetect_analysis_facts.analysis = idetect_analyses.gkg_id)))
             JOIN gkg ON ((idetect_analyses.gkg_id = gkg.id)))
            WHERE ((idetect_facts.specific_reported_figure < 100000000) AND (idetect_analyses.category IS NOT NULL))
          GROUP BY (date_trunc('week'::text, (to_date(substr((gkg.date)::text, 1, 8), 'YYYYMMDD'::text))::timestamp with time zone)), idetect_locations.id, (split_part((idetect_locations.latlong)::text, ','::text, 1)), (split_part((idetect_locations.latlong)::text, ','::text, 2)), idetect_analyses.category
          ORDER BY (date_trunc('week'::text, (to_date(substr((gkg.date)::text, 1, 8), 'YYYYMMDD'::text))::timestamp with time zone))
        ), entries AS (
         SELECT row_to_json(input_table.*) AS entry
           FROM input_table
        )
 SELECT jsonb_agg(entries.entry) AS entries
   FROM entries
);
ALTER TABLE idetect_map_week_mview OWNER TO idetect;


