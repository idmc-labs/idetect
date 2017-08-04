import os
from unittest import TestCase

from sqlalchemy import create_engine

from idetect.model import Base, Session, Status, Article
from idetect.scraper import scrape


class TestScraper(TestCase):
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
        for article in self.session.query(Article).all():
            self.session.delete(article)
        self.session.commit()

    def test_scrape_html(self):
        article = Article(url="http://www.cnn.com/2013/08/23/us/hurricane-katrina-statistics-fast-facts/index.html",
                          url_id=1,
                          status=Status.NEW)
        self.session.add(article)
        self.session.commit()
        scrape(article)
        content = article.content[0]
        self.assertEqual("text", content.content_type)
        self.assertTrue("Katrina" in content.content)
        self.assertTrue("Louisiana" in content.content)
        self.assertTrue("\n" not in content.content)

    def test_scrape_pdf(self):
        article = Article(url="https://www1.ncdc.noaa.gov/pub/data/extremeevents/specialreports/Hurricane-Katrina.pdf",
                          url_id=2,
                          status=Status.NEW)
        self.session.add(article)
        self.session.commit()
        scrape(article)
        content = article.content[0]
        self.assertEqual("pdf", content.content_type)
        self.assertTrue("Katrina" in content.content)
        self.assertTrue("Louisiana" in content.content)
        self.assertTrue("\n" not in content.content)
