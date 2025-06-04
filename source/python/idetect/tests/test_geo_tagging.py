import os
from unittest import TestCase, mock

from sqlalchemy import create_engine

from idetect.model import Base, Session, Status, Gkg, Analysis, DocumentContent, Country, Location, LocationType, Fact
from idetect.load_data import load_countries
from idetect.fact_extractor import extract_facts
from idetect.geotagger import get_geo_info, process_locations, nominatim_coordinates, GeotagException


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
        self.assertEqual(results['coordinates'], "39.906217,116.3912757")
    
    def test_country_code(self):
        """Returns sufficient level of detail for results"""
        results = get_geo_info("Bidibidi")
        self.assertEqual(results['country_code'], 'UGA')
        results = get_geo_info("Marrakech")
        self.assertEqual(results['country_code'], 'MAR')
        results = get_geo_info("Fairfax County")
        self.assertEqual(results['country_code'], 'USA')


    def test_location_types(self):
        """Corectly distinguishes between Countries, Cities and Subdivisions"""
        results = get_geo_info("London")
        self.assertEqual(results['type'], LocationType.CITY)
        results = get_geo_info("India")
        self.assertEqual(results['type'], LocationType.COUNTRY)
        results = get_geo_info("Alaska")
        self.assertEqual(results['type'], LocationType.SUBDIVISION)

    # DONT RUN geotagging if detail already exists
    @mock.patch('idetect.geotagger.nominatim_coordinates')
    def dont_geotag_if_detail_exists(self, nominatim):
        gkg = Gkg(
            id=3771256,
            gkgrecordid="20170215174500-2503",
            date=20170215174500,
            document_identifier="http://www.philstar.com/headlines/2017/02/16/1672746/yasay-harris-affirm-stronger-phl-us-ties"
        )
        self.session.add(gkg)
        analysis = Analysis(gkg=gkg, status=Status.NEW)
        self.session.add(analysis)
        content = DocumentContent(
            content_clean="It was early Saturday when a flash flood hit large parts of India and Pakistan and washed away more than 500 houses")
        self.session.add(content)
        self.session.commit()
        analysis.content_id = content.id
        self.session.commit()
        fact = Fact(unit='person', term='displaced')
        self.session.add(fact)
        self.session.commit()
        loc1 = self.session.query(Location).filter(Location.location_name == 'India').one_or_none()
        fact.locations.append(loc1)
        analysis.facts.append(fact)
        self.session.commit()
        process_locations(analysis)
        assert not nominatim.called


    def test_create_duplicate_fact(self):
        """Creates duplicate fact if locations from multiple countries exist"""
        gkg = Gkg(
            id=3771256,
            gkgrecordid="20170215174500-2503",
            date=20170215174500,
            document_identifier="http://www.philstar.com/headlines/2017/02/16/1672746/yasay-harris-affirm-stronger-phl-us-ties"
        )
        self.session.add(gkg)
        analysis = Analysis(gkg=gkg, status=Status.NEW)
        self.session.add(analysis)
        self.session.commit()
        fact = Fact(unit='person', term='displaced')
        self.session.add(fact)
        self.session.commit()
        loc1 = self.session.query(Location).filter(Location.location_name == 'India').one_or_none()
        loc2 = self.session.query(Location).filter(Location.location_name == 'Pakistan').one_or_none()
        fact.locations.append(loc1)
        fact.locations.append(loc2)
        analysis.facts.append(fact)
        self.session.commit()
        self.assertEqual(1, len(analysis.facts))
        process_locations(analysis)
        self.assertEqual(2, len(analysis.facts))
        fact_countries = [f.iso3 for f in analysis.facts]
        self.assertIn('IND', fact_countries)
        self.assertIn('PAK', fact_countries)
        self.assertEqual(1, len(analysis.facts[0].locations))
        self.assertEqual(1, len(analysis.facts[1].locations))


    @mock.patch('idetect.geotagger.nominatim_coordinates')
    def test_fail_if_geotagging_fails(self, nominatim):
        """Location processing should fail if geotagging fails"""
        nominatim.side_effect = GeotagException()
        gkg = Gkg(
            id=3771256,
            gkgrecordid="20170215174500-2503",
            date=20170215174500,
            document_identifier="http://www.philstar.com/headlines/2017/02/16/1672746/yasay-harris-affirm-stronger-phl-us-ties"
        )
        self.session.add(gkg)
        analysis = Analysis(gkg=gkg, status=Status.NEW)
        self.session.add(analysis)
        self.session.commit()
        fact = Fact(unit='person', term='displaced')
        self.session.add(fact)
        self.session.commit()
        loc1 = Location(location_name="Ruislip")
        fact.locations.append(loc1)
        analysis.facts.append(fact)
        self.session.commit()
        with self.assertRaises(GeotagException):
            process_locations(analysis)


