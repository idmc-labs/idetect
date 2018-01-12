### Update Fact locations to deal with duplicates
update idetect_fact_locations set location = (
  select min from (
    select il1.location_name, min(il1.id) as min, il2.id as id2
    from idetect_locations il1
    join idetect_locations il2 on il1.location_name = il2.location_name
    group by il1.location_name, il2.id
  ) as x
  where location = id2
);

### Add UNIQUE constraint
ALTER TABLE idetect_locations
ADD CONSTRAINT unique_location_name UNIQUE (location_name);
