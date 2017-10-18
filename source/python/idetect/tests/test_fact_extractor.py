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

    def test_create_locations_with_names(self):
        """Creates locations for facts only with location names"""
        document = Document(type=DocumentType.WEB,
                            name="Hurricane Katrina Fast Facts")
        analysis = Analysis(document=document, status=Status.NEW)
        self.session.add(analysis)
        content = DocumentContent(
            content_clean="It was early Saturday when a flash flood hit large parts of London and Middlesex and washed away more than 500 houses")
        self.session.add(content)
        self.session.commit()
        analysis.content_id = content.id
        self.session.commit()
        extract_facts(analysis)
        facts = analysis.facts
        self.assertEqual(1, len(facts))
        fact = facts[0]
        self.assertEqual(2, len(fact.locations))
        loc_names = [loc.location_name for loc in fact.locations]
        self.assertIn('London', loc_names)
        self.assertIn('Middlesex', loc_names)
        self.assertEqual([None, None], [loc.country for loc in fact.locations])


    def test_use_existing_location(self):
        """Uses existing locations when they exist"""
        document = Document(type=DocumentType.WEB,
                            name="Hurricane Katrina Fast Facts")
        analysis = Analysis(document=document, status=Status.NEW)
        self.session.add(analysis)
        content = DocumentContent(
            content_clean="It was early Saturday when a flash flood hit large parts of Bosnia and washed away more than 500 houses")
        self.session.add(content)
        location = Location(location_name='Bosnia')
        self.session.add(location)
        self.session.commit()
        analysis.content_id = content.id
        self.session.commit()
        extract_facts(analysis)
        fact = analysis.facts[0]
        extracted_location = fact.locations[0]
        self.assertEqual(location.id, extracted_location.id)

