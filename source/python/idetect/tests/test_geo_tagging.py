import os
from unittest import TestCase

from sqlalchemy import create_engine

from idetect.model import Base, Session, LocationType
from idetect.load_data import load_countries
from idetect.geotagger import get_geo_info


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

    def tearDown(self):
        self.session.rollback()

    def test_sets_no_results_flag(self):
        """Sets no-results flag if nothing found"""
        results = get_geo_info("xghijdshfkljdes")
        self.assertEqual(results['flag'], "no-results")

    def test_returns_detail_for_places(self):
        """Returns sufficient level of detail for results"""
        results = get_geo_info("Paris")
        self.assertNotEqual(results['country_code'], '')
        self.assertNotEqual(results['coordinates'], '')
        self.assertNotEqual(results['type'], '')

    def test_accuracy(self):
        """Returns sufficient level of detail for results"""
        results = get_geo_info("Beijing")
        self.assertEqual(results['country_code'], 'CHN')
        self.assertEqual(results['coordinates'],
                         "39.937967,116.417592")

    def test_location_types(self):
        """Corectly distinguishes between Countries, Cities and Subdivisions"""
        results = get_geo_info("London")
        self.assertEqual(results['type'], LocationType.CITY)
        results = get_geo_info("India")
        self.assertEqual(results['type'], LocationType.COUNTRY)
        results = get_geo_info("Alaska")
        self.assertEqual(results['type'], LocationType.SUBDIVISION)



