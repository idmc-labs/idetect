### Set all fact_locations for Syria to first row
UPDATE idetect_fact_locations
SET location = (SELECT id FROM idetect_locations WHERE location_name = 'Syrian Arab Republic'
ORDER BY id ASC LIMIT 1)
WHERE location IN (SELECT COUNT(id) FROM idetect_locations WHERE location_name = 'Syrian Arab Republic'
AND id != (SELECT id FROM idetect_locations WHERE location_name = 'Syrian Arab Republic'
ORDER BY id ASC LIMIT 1));

DELETE FROM idetect_locations WHERE id IN (SELECT COUNT(id) FROM idetect_locations WHERE location_name = 'Syrian Arab Republic'
AND id != (SELECT id FROM idetect_locations WHERE location_name = 'Syrian Arab Republic'
ORDER BY id ASC LIMIT 1));


### Set all fact_locations for Bosnia to first row
UPDATE idetect_fact_locations
SET location = (SELECT id FROM idetect_locations WHERE location_name = 'Bosnia and Herzegovina'
ORDER BY id ASC LIMIT 1)
WHERE location IN (SELECT COUNT(id) FROM idetect_locations WHERE location_name = 'Bosnia and Herzegovina'
AND id != (SELECT id FROM idetect_locations WHERE location_name = 'Bosnia and Herzegovina'
ORDER BY id ASC LIMIT 1));

DELETE FROM idetect_locations WHERE id IN (SELECT COUNT(id) FROM idetect_locations WHERE location_name = 'Bosnia and Herzegovina'
AND id != (SELECT id FROM idetect_locations WHERE location_name = 'Bosnia and Herzegovina'
ORDER BY id ASC LIMIT 1));


### Set all fact_locations for NZ to first row
UPDATE idetect_fact_locations
SET location = (SELECT id FROM idetect_locations WHERE location_name = 'NZ'
ORDER BY id ASC LIMIT 1)
WHERE location IN (SELECT COUNT(id) FROM idetect_locations WHERE location_name = 'NZ'
AND id != (SELECT id FROM idetect_locations WHERE location_name = 'NZ'
ORDER BY id ASC LIMIT 1));

DELETE FROM idetect_locations WHERE id IN (SELECT COUNT(id) FROM idetect_locations WHERE location_name = 'NZ'
AND id != (SELECT id FROM idetect_locations WHERE location_name = 'NZ'
ORDER BY id ASC LIMIT 1));


### Set all fact_locations for Juniper Acres to first row
UPDATE idetect_fact_locations
SET location = (SELECT id FROM idetect_locations WHERE location_name = 'Juniper Acres'
ORDER BY id ASC LIMIT 1)
WHERE location IN (SELECT COUNT(id) FROM idetect_locations WHERE location_name = 'Juniper Acres'
AND id != (SELECT id FROM idetect_locations WHERE location_name = 'Juniper Acres'
ORDER BY id ASC LIMIT 1));

DELETE FROM idetect_locations WHERE id IN (SELECT COUNT(id) FROM idetect_locations WHERE location_name = 'Juniper Acres'
AND id != (SELECT id FROM idetect_locations WHERE location_name = 'Juniper Acres'
ORDER BY id ASC LIMIT 1));


### Set all fact_locations for Pappinbarra Road to first row
UPDATE idetect_fact_locations
SET location = (SELECT id FROM idetect_locations WHERE location_name = 'Pappinbarra Road'
ORDER BY id ASC LIMIT 1)
WHERE location IN (SELECT COUNT(id) FROM idetect_locations WHERE location_name = 'Pappinbarra Road'
AND id != (SELECT id FROM idetect_locations WHERE location_name = 'Pappinbarra Road'
ORDER BY id ASC LIMIT 1));

DELETE FROM idetect_locations WHERE id IN (SELECT COUNT(id) FROM idetect_locations WHERE location_name = 'Pappinbarra Road'
AND id != (SELECT id FROM idetect_locations WHERE location_name = 'Pappinbarra Road'
ORDER BY id ASC LIMIT 1));


### Set all fact_locations for Programme to first row
UPDATE idetect_fact_locations
SET location = (SELECT id FROM idetect_locations WHERE location_name = 'Programme'
ORDER BY id ASC LIMIT 1)
WHERE location IN (SELECT COUNT(id) FROM idetect_locations WHERE location_name = 'Programme'
AND id != (SELECT id FROM idetect_locations WHERE location_name = 'Programme'
ORDER BY id ASC LIMIT 1));

DELETE FROM idetect_locations WHERE id IN (SELECT COUNT(id) FROM idetect_locations WHERE location_name = 'Programme'
AND id != (SELECT id FROM idetect_locations WHERE location_name = 'Programme'
ORDER BY id ASC LIMIT 1));


### Add UNIQUE constraint
ALTER TABLE idetect_locations
ADD CONSTRAINT unique_location_name UNIQUE (location_name);
