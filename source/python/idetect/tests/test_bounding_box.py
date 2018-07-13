import os
from unittest import TestCase, mock

from sqlalchemy import create_engine

from idetect.model import Base, Session, Status, Gkg, Analysis, DocumentContent, Country, Location, LocationType, Fact
from idetect.load_data import load_countries, load_terms
from idetect.fact_extractor import extract_facts
from idetect.geotagger import get_geo_info, process_locations, nominatim_coordinates, GeotagException

import pycountry 

def extract_all_countries(content):
    countries_in_content=[]
    countries = (c for c in list(pycountry.countries))
    for country in countries:  # Loop through all countries
        if country.name in content:  # Look directly at country name
            countries_in_content.append(country.alpha_3)
        # In some cases the country also has a common name
        elif hasattr(country, 'common_name') and country.common_name in content:
            countries_in_content.append(country.alpha_3)
    return set(countries_in_content)


class TestGeoTagger(TestCase):
 
    def setUp(self):
        db_host = os.environ.get('DB_HOST')
        db_url = 'postgresql://{user}:{passwd}@{db_host}/{db}'.format(
            user='tester', passwd='tester', db_host=db_host, db='idetect_test')
        engine = create_engine(db_url)
        Session.configure(bind=engine)
        Base.metadata.drop_all(engine)
        Base.metadata.create_all(engine)
        self.session = Session()
        load_countries(self.session)
        load_terms(self.session)


    def test_bounding_box_on_new_location(self):
        "Creates locations for facts only with location names"
        gkg = Gkg()
        analysis = Analysis(gkg=gkg, status=Status.NEW)
        self.session.add(analysis)
        content = DocumentContent(
            # example from  http://news.power102fm.com/20-people-now-homeless-as-land-beneath-them-shifts-52980
            content_clean="Five families have been affected by coastal erosion\
             which occurred at Bamboo Village, Cedros, leaving 20 people homeless.\
             Up to late last night, the Trinidad and Tobago Fire Services as well as\
            the Councillor for the area, Shankar Teelucksingh, were on site to monitor\
            the situation in efforts to ensure the safety of the villagers.")
        self.session.add(content)
        self.session.commit()
        analysis.content_id = content.id
        self.session.commit()
        extract_facts(analysis)
        self.session.commit()
        process_locations(analysis)
        self.session.commit()
        facts = analysis.facts
        print('nfacts:',len(facts))
        fact = facts[0]
        loc_iso3 = [loc.country_iso3 for loc in fact.locations]
        loc_latlong = [loc.latlong for loc in fact.locations]
        print('in test, iso3 in locations:',loc_iso3)
        print('in test, latlong in locations:',loc_latlong)
        print('in test, locations in text:',extract_all_countries(content.content_clean))

    def test_bounding_box_on_existing_location(self):
        return True
