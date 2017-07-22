import os
from unittest import TestCase

import sqlalchemy
from sqlalchemy import create_engine

from idetect.model import Base, Session, Status, Article, UnexpectedArticleStatusException, CountryTerm, Location, \
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
        self.session.query(Article).filter(Article.url =='http://example.com').delete()
        self.session.commit()

    def test_status_update(self):
        article = Article(url='http://example.com',
                          url_id=123,
                          status=Status.NEW)
        self.session.add(article)
        self.session.commit()

        article.update_status(Status.FETCHING)
        self.assertEqual(article.status, Status.FETCHING)

        # meanwhile, some other process changed the status of this...
        session2 = Session()
        try:
            other = Article.most_recent(session2, article.url_id)
            other.update_status(Status.FETCHING_FAILED)
        finally:
            session2.rollback()

        with self.assertRaises(NotLatestException):
            article.update_status(Status.FETCHED)

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