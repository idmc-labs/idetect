DROP MATERIALIZED VIEW if EXISTS idetect_fact_api;
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
    idetect_analyses.content_id
  from idetect_facts
  join idetect_analysis_facts ON idetect_facts.id = idetect_analysis_facts.fact
  join idetect_analyses ON idetect_analysis_facts.analysis = idetect_analyses.gkg_id
  join gkg ON gkg.id = idetect_analyses.gkg_id
  left join idetect_fact_locations ON idetect_facts.id = idetect_fact_locations.fact
);

CREATE INDEX idetect_fact_api_loc_day_idx on idetect_fact_api (location, gdelt_day);
CREATE INDEX idetect_fact_api_day_loc_idx on idetect_fact_api (gdelt_day, location);
CREATE INDEX idetect_fact_api_loc_idx on idetect_fact_api (location, category);
CREATE INDEX idetect_fact_api_day_idx on idetect_fact_api (gdelt_day, category);
CREATE INDEX idetect_fact_api_category_idx on idetect_fact_api (category);
create INDEX idetect_fact_api_fact_hash ON idetect_fact_api USING HASH (fact);

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