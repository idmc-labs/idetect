import os
from unittest import TestCase

from sqlalchemy import create_engine

from idetect.model import Base, Session, Status, Document, Analysis, DocumentContent, DocumentType, Country, Location
from idetect.fact_extractor import extract_facts, process_location
from idetect.load_data import load_countries, load_terms


class TestFactExtractor(TestCase):

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

    def tearDown(self):
        self.session.rollback()
        for article in self.session.query(Document).all():
            self.session.delete(article)
        self.session.commit()

    def test_extract_facts_simple(self):
        """Extracts simple facts when present and saves to DB"""
        document = Document(type=DocumentType.WEB,
                            name="Hurricane Katrina Fast Facts")
        analysis = Analysis(document=document, status=Status.NEW)
        self.session.add(analysis)
        content = DocumentContent(
            content_clean="It was early Saturday when a flash flood hit the area and washed away more than 500 houses")
        self.session.add(content)
        self.session.commit()
        analysis.content_id = content.id
        self.session.commit()
        extract_facts(analysis)
        self.assertEqual(1, len(analysis.facts))

    def test_create_facts_per_country(self):
        """Creates one fact per country mentioned"""
        document = Document(type=DocumentType.WEB,
                            name="Hurricane Katrina Fast Facts")
        analysis = Analysis(document=document, status=Status.NEW)
        self.session.add(analysis)
        content = DocumentContent(
            content_clean="It was early Saturday when a flash flood hit large parts of Pakistan and India and washed away more than 500 houses")
        self.session.add(content)
        self.session.commit()
        analysis.content_id = content.id
        self.session.commit()
        extract_facts(analysis)
        facts = analysis.facts
        self.assertEqual(2, len(facts))
        iso_codes = [f.iso3 for f in facts]
        self.assertIn('IND', iso_codes)
        self.assertIn('PAK', iso_codes)

    def test_use_existing_locations_for_facts(self):
        """Uses existing locations when creating facts"""
        d1 = Document(type=DocumentType.WEB,
                      name="Hurricane Katrina Fast Facts")
        analysis1 = Analysis(document=d1, status=Status.NEW)
        self.session.add(analysis1)
        content = DocumentContent(
            content_clean="It was early Saturday when a flash flood hit large parts of India and washed away more than 500 houses")
        self.session.add(content)
        self.session.commit()
        analysis1.content_id = content.id
        self.session.commit()
        extract_facts(analysis1)

        d2 = Document(type=DocumentType.WEB,
                      name="Hurricane Katrina Fast Facts")
        analysis2 = Analysis(document=d2, status=Status.NEW)
        self.session.add(analysis2)
        content = DocumentContent(
            content_clean="It was early Saturday when a flash flood hit large parts of India and washed away more than 500 houses")
        self.session.add(content)
        self.session.commit()
        analysis2.content_id = content.id
        self.session.commit()
        extract_facts(analysis2)

        self.assertEqual(analysis1.facts[0].locations[
                         0], analysis2.facts[0].locations[0])

    def test_process_location_return_existing(self):
        """Returns existing location if it exsits"""
        country = self.session.query(Country).filter_by(
            iso3='GBR').one_or_none()
        location = Location(location_name='Ruislip', location_type='',
                            country_iso3=country.iso3,
                            country=country, latlong='')
        self.session.add(location)
        self.session.commit()
        locations = process_location("Ruislip", self.session)
        self.assertEqual(locations[0].id, location.id)

    def test_process_location_create_new(self):
        """Creates new location if it doesn't exist"""
        country_locations = self.session.query(Location)\
            .filter(Location.country_iso3 == 'GBR').all()
        location_names = [l.location_name for l in country_locations]
        self.assertNotIn("Ruislip", location_names)
        process_location("Ruislip", self.session)
        country_locations = self.session.query(Location)\
            .filter(Location.country_iso3 == 'GBR').all()
        location_names = [l.location_name for l in country_locations]
        self.assertIn("Ruislip", location_names)
