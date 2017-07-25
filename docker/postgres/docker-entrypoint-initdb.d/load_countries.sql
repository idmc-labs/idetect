\copy country(code, preferred_term) FROM '/home/idetect/data/countries.csv' DELIMITER ',' CSV HEADER;

\copy country_term(term, country) FROM '/home/idetect/data/country_terms.csv' DELIMITER ',' CSV HEADER;

\copy location(description, location_type, country_code, latlong) FROM '/home/idetect/data/country_locations.csv' DELIMITER ',' CSV HEADER;
