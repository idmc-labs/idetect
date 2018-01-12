-- Add row to countries for Unkown
INSERT INTO idetect_countries (iso3, preferred_term) VALUES ('XXX', 'Unknown');

-- Delete fact-location duplicates if they exist
DELETE FROM idetect_fact_locations
WHERE exists (SELECT 1
              FROM idetect_fact_locations t2
              WHERE t2.fact = idetect_fact_locations.fact and
                    t2.location = idetect_fact_locations.location and
                    t2.ctid > idetect_fact_locations.ctid
             );

-- Add Unique Constraint on fact_location
ALTER TABLE idetect_fact_locations
  ADD CONSTRAINT fact_locations_uni UNIQUE(fact, location);