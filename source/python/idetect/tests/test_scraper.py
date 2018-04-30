import os
from unittest import TestCase

from sqlalchemy import create_engine

from idetect.model import Base, Session, Status, Gkg, Analysis, DocumentContent
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
        for gkg in self.session.query(Gkg).all():
            self.session.delete(gkg)
        self.session.commit()

    def test_scrape_html(self):
        gkg = Gkg(
            document_identifier="http://www.cnn.com/2013/08/23/us/hurricane-katrina-statistics-fast-facts/index.html")
        analysis = Analysis(gkg=gkg, status=Status.NEW)
        self.session.add(analysis)
        self.session.commit()
        scrape(analysis)
        content = analysis.content
        self.assertEqual("text", content.content_type)
        self.assertTrue("Katrina" in content.content_clean)
        self.assertTrue("Louisiana" in content.content_clean)
        self.assertTrue("\n" not in content.content_clean)
        self.assertTrue(content.content_ts is not None)
        matches = (
            self.session.query(DocumentContent)
                .filter(DocumentContent.content_ts.match('Katrina & Louisiana')).all()
        )
        self.assertIn(content, matches)

    def test_scrape_pdf(self):
        gkg = Gkg(
            document_identifier="https://www1.ncdc.noaa.gov/pub/data/extremeevents/specialreports/Hurricane-Katrina.pdf")
        analysis = Analysis(gkg=gkg, status=Status.NEW)
        self.session.add(analysis)
        self.session.commit()
        scrape(analysis)
        content = analysis.content
        self.assertEqual("pdf", content.content_type)
        self.assertTrue("Katrina" in content.content)
        self.assertTrue("Louisiana" in content.content)
        self.assertTrue("\n" not in content.content)
