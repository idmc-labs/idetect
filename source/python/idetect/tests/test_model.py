import os
from datetime import datetime
from unittest import TestCase

from sqlalchemy import create_engine

from idetect.model import Base, Session, Status, Article, CountryTerm, Location, \
    LocationType, Country, Content, NotLatestException, Report, ArticleHistory


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
            other = session2.query(Article).get(article.id)
            other.create_new_version(Status.SCRAPING_FAILED)
        finally:
            session2.rollback()

        with self.assertRaises(NotLatestException):
            article.create_new_version(Status.SCRAPED)

    def test_version_lifecycle(self):
        article = Article(url='http://example.com',
                          url_id=123,
                          status=Status.NEW)
        self.session.add(article)
        self.session.commit()

        article.create_new_version(Status.SCRAPING)

        history = self.session.query(ArticleHistory).filter(ArticleHistory.article == article)
        self.assertEqual(1, history.count())
        self.assertEqual(1, history.filter(ArticleHistory.status == Status.NEW).count())

        content = Content(content_type="text/html", content="Lorem ipsum")
        article.content = content
        article.create_new_version(Status.SCRAPED)

        self.assertEqual(2, history.count())
        self.assertEqual(1, history.filter(ArticleHistory.status == Status.NEW).count())
        self.assertEqual(1, history.filter(ArticleHistory.status == Status.SCRAPING).count())

        article.create_new_version(Status.EXTRACTING)

        self.assertEqual(3, history.count())
        self.assertEqual(1, history.filter(ArticleHistory.status == Status.NEW).count())
        self.assertEqual(1, history.filter(ArticleHistory.status == Status.SCRAPING).count())
        self.assertEqual(1, history.filter(ArticleHistory.status == Status.SCRAPED).count())

        # content is preserved
        scraped = history.filter(ArticleHistory.status == Status.SCRAPED).one_or_none()
        self.assertEqual(article.content, scraped.content)

        report = Report(analysis_date=datetime.now())
        article.reports = [report]
        article.create_new_version(Status.EXTRACTED)

        self.assertEqual(4, history.count())
        self.assertEqual(1, history.filter(ArticleHistory.status == Status.NEW).count())
        self.assertEqual(1, history.filter(ArticleHistory.status == Status.SCRAPING).count())
        self.assertEqual(1, history.filter(ArticleHistory.status == Status.SCRAPED).count())
        self.assertEqual(1, history.filter(ArticleHistory.status == Status.EXTRACTING).count())

        # content still preserved
        extracting = history.filter(ArticleHistory.status == Status.EXTRACTING).one_or_none()
        self.assertEqual(article.content, extracting.content)

        article.create_new_version(Status.EDITING)
        article.content = Content(content_type="text/html", content="Lorem edited")
        article.create_new_version(Status.EDITED)

        self.assertEqual(6, history.count())
        self.assertEqual(1, history.filter(ArticleHistory.status == Status.NEW).count())
        self.assertEqual(1, history.filter(ArticleHistory.status == Status.SCRAPING).count())
        self.assertEqual(1, history.filter(ArticleHistory.status == Status.SCRAPED).count())
        self.assertEqual(1, history.filter(ArticleHistory.status == Status.EXTRACTING).count())
        self.assertEqual(1, history.filter(ArticleHistory.status == Status.EXTRACTED).count())
        self.assertEqual(1, history.filter(ArticleHistory.status == Status.EDITING).count())

        # content has changed, but reports are preserved
        extracted = history.filter(ArticleHistory.status == Status.EXTRACTED).one_or_none()
        self.assertNotEqual(article.content.id, extracted.content.id)
        self.assertCountEqual([r.id for r in article.reports], [r.id for r in extracted.reports])

        article.create_new_version(Status.EDITING)
        report2 = Report(analysis_date=datetime.now())
        article.reports.append(report2)
        article.create_new_version(Status.EDITED)

        self.assertEqual(8, history.count())
        self.assertEqual(1, history.filter(ArticleHistory.status == Status.NEW).count())
        self.assertEqual(1, history.filter(ArticleHistory.status == Status.SCRAPING).count())
        self.assertEqual(1, history.filter(ArticleHistory.status == Status.SCRAPED).count())
        self.assertEqual(1, history.filter(ArticleHistory.status == Status.EXTRACTING).count())
        self.assertEqual(1, history.filter(ArticleHistory.status == Status.EXTRACTED).count())
        self.assertEqual(2, history.filter(ArticleHistory.status == Status.EDITING).count())
        self.assertEqual(1, history.filter(ArticleHistory.status == Status.EDITED).count())

        edited = history.filter(ArticleHistory.status == Status.EDITED).one_or_none()
        self.assertCountEqual([r.id for r in article.reports], [report.id, report2.id])
        self.assertCountEqual([r.id for r in edited.reports], [report.id])

    def test_status_counts(self):
        article1 = Article(url='http://example.com',
                           url_id=123,
                           status=Status.NEW)
        self.session.add(article1)
        self.session.commit()

        self.assertEqual(Article.status_counts(self.session),
                         {Status.NEW: 1})

        article1.create_new_version(Status.SCRAPING)

        self.assertEqual(Article.status_counts(self.session),
                         {Status.SCRAPING: 1})

        article2 = Article(url='http://example.com',
                           url_id=234,
                           status=Status.NEW)
        self.session.add(article2)
        self.session.commit()

        self.assertEqual(Article.status_counts(self.session),
                         {Status.NEW: 1,
                          Status.SCRAPING: 1})

        article2.create_new_version(Status.SCRAPING)

        self.assertEqual(Article.status_counts(self.session),
                         {Status.SCRAPING: 2})

        article2.create_new_version(Status.SCRAPED)

        self.assertEqual(Article.status_counts(self.session),
                         {Status.SCRAPED: 1,
                          Status.SCRAPING: 1})

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
