import os
from datetime import datetime
from unittest import TestCase

from sqlalchemy import create_engine

from idetect.model import Base, Session, Status, Article, CountryTerm, Location, \
    LocationType, Country, Content, NotLatestException, Report


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
        for article in self.session.query(Article).filter(Article.url == 'http://example.com').all():
            self.session.delete(article)
        self.session.commit()

    def test_status_update(self):
        article = Article(url='http://example.com',
                          url_id=123,
                          status=Status.NEW)
        self.session.add(article)
        self.session.commit()

        article.create_new_version(Status.SCRAPING)
        self.assertEqual(article.status, Status.SCRAPING)

        # meanwhile, some other process changed the status of this...
        session2 = Session()
        try:
            other = Article.get_latest_version(session2, article.url_id)
            other.create_new_version(Status.SCRAPING_FAILED)
        finally:
            session2.rollback()

        with self.assertRaises(NotLatestException):
            article.create_new_version(Status.SCRAPED)

    def test_create_new_version(self):
        article = Article(url='http://example.com',
                          url_id=123,
                          status=Status.PROCESSING)
        content = Content(content_type="text/html", content="Lorem ipsum")
        article.content = content
        report = Report(analysis_date=datetime.now())
        article.reports = [report]
        self.session.add(article)
        self.session.commit()

        old_id = article.id
        article.create_new_version(Status.PROCESSED)
        self.assertNotEqual(old_id, article.id)
        self.assertEqual(article.content, content)
        self.assertEqual(article.reports, [report])

        old_article = self.session.query(Article).get(old_id)
        self.assertEqual(old_article.content, content)
        self.assertEqual(old_article.reports, [report])

    def test_cascading_delete(self):
        article = Article(url='http://example.com',
                          url_id=123,
                          status=Status.PROCESSING)
        content = Content(content_type="text/html", content="Lorem ipsum")
        article.content = content
        report = Report(analysis_date=datetime.now())
        article.reports = [report]
        self.session.add(article)
        self.session.commit()

        old_id = article.id
        article.create_new_version(Status.PROCESSED)
        new_id = article.id
        self.assertIsNotNone(new_id)
        self.assertNotEqual(old_id, new_id)
        self.assertEqual(article.content, content)
        self.assertEqual(article.reports, [report])

        old_article = self.session.query(Article).get(old_id)
        self.assertEqual(old_article.content, content)
        self.assertEqual(old_article.reports, [report])

        self.assertEqual(self.session.query(Article).count(), 2)
        self.assertEqual(self.session.query(Report).count(), 1)
        self.assertEqual(self.session.query(Content).count(), 1)

        self.session.delete(article)
        self.session.commit()

        self.assertEqual(self.session.query(Article).count(), 1)
        self.assertEqual(self.session.query(Report).count(), 1)
        self.assertEqual(self.session.query(Content).count(), 1)

        self.assertIsNone(self.session.query(Article).get(new_id))
        self.assertIsNotNone(self.session.query(Article).get(old_id))

    def test_select_latest_version(self):
        article1 = Article(url='http://example.com',
                           url_id=123,
                           status=Status.NEW)
        self.session.add(article1)
        self.session.commit()
        article1.create_new_version(Status.SCRAPING)
        article2 = Article(url='http://example.com',
                           url_id=234,
                           status=Status.NEW)
        self.session.add(article2)
        self.session.commit()
        article2.create_new_version(Status.SCRAPING)
        article2.create_new_version(Status.SCRAPED)

        new = Article.select_latest_version(self.session) \
            .filter(Article.status == Status.NEW) \
            .all()
        self.assertCountEqual(new, [])

        fetching = Article.select_latest_version(self.session) \
            .filter(Article.status == Status.SCRAPING) \
            .all()
        self.assertCountEqual(fetching, [article1])

        fetched = Article.select_latest_version(self.session) \
            .filter(Article.status == Status.SCRAPED) \
            .all()
        self.assertCountEqual(fetched, [article2])

        self.assertEqual(Article.status_counts(self.session), {'scraping': 1, 'scraped': 1})

    def test_content_transfer(self):
        article = Article(url='http://example.com',
                          url_id=123,
                          status=Status.SCRAPING)
        self.session.add(article)
        self.session.commit()

        article.create_new_version(Status.SCRAPED)
        article.content = Content(content_type="text", content="Lorem ipsum")
        self.session.commit()
        old_article_id = article.id
        old_content_id = article.content.id

        article.create_new_version(Status.PROCESSING)
        self.assertNotEqual(old_article_id, article.id)
        self.assertEqual(old_content_id, article.content.id)

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
