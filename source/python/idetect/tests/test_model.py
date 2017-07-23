import os
from unittest import TestCase

from sqlalchemy import create_engine

from idetect.model import Base, Session, Status, Article, CountryTerm, Location, \
    LocationType, Country, NotLatestException


class TestModel(TestCase):
    def setUp(self):
        db_host = os.environ.get('DB_HOST')
        db_url = 'postgresql://{user}:{passwd}@{db_host}/{db}'.format(
            user='tester', passwd='tester', db_host=db_host, db='idetect_test')
        engine = create_engine(db_url)
        Session.configure(bind=engine)
        Base.metadata.drop_all(engine)
        Base.metadata.create_all(engine)
        self.session = Session()

    def tearDown(self):
        self.session.rollback()
        self.session.query(Article).filter(Article.url == 'http://example.com').delete()
        self.session.commit()

    def test_status_update(self):
        article = Article(url='http://example.com',
                          url_id=123,
                          status=Status.NEW)
        self.session.add(article)
        self.session.commit()

        article.create_new_version(Status.FETCHING)
        self.assertEqual(article.status, Status.FETCHING)

        # meanwhile, some other process changed the status of this...
        session2 = Session()
        try:
            other = Article.get_latest_version(session2, article.url_id)
            other.create_new_version(Status.FETCHING_FAILED)
        finally:
            session2.rollback()

        with self.assertRaises(NotLatestException):
            article.create_new_version(Status.FETCHED)

    def test_select_latest_version(self):
        article1 = Article(url='http://example.com',
                           url_id=123,
                           status=Status.NEW)
        self.session.add(article1)
        self.session.commit()
        article1.create_new_version(Status.FETCHING)
        article2 = Article(url='http://example.com',
                           url_id=234,
                           status=Status.NEW)
        self.session.add(article2)
        self.session.commit()
        article2.create_new_version(Status.FETCHING)
        article2.create_new_version(Status.FETCHED)

        new = Article.select_latest_version(self.session) \
            .filter(Article.status == Status.NEW) \
            .all()
        self.assertCountEqual(new, [])

        fetching = Article.select_latest_version(self.session) \
            .filter(Article.status == Status.FETCHING) \
            .all()
        self.assertCountEqual(fetching, [article1])

        fetched = Article.select_latest_version(self.session) \
            .filter(Article.status == Status.FETCHED) \
            .all()
        self.assertCountEqual(fetched, [article2])

    def test_country_term(self):
        mmr = Country(code="MMR", preferred_term="Myanmar")
        myanmar = CountryTerm(term="Myanmar", country=mmr)
        burma = CountryTerm(term="Burma", country=mmr)
        yangon = Location(description="Yangon",
                          location_type=LocationType.CITY,
                          country=mmr,
                          latlong="16°51′N 96°11′E")

        self.assertEqual(yangon.country, myanmar.country)
        self.assertEqual(yangon.country, burma.country)
