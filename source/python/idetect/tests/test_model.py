import os
from datetime import datetime, date
from unittest import TestCase

import dateutil.parser
from sqlalchemy import create_engine

from idetect.model import Base, Session, Status, Gkg, \
    Analysis, DocumentContent, NotLatestException, AnalysisHistory, Country, CountryTerm, Location, LocationType, Fact


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
        self.sample_data()

    def sample_data(self):
        gkg1 = Gkg(
            id=3771256,
            gkgrecordid="20170215174500-2503",
            date=20170215174500,
            document_identifier="http://www.philstar.com/headlines/2017/02/16/1672746/yasay-harris-affirm-stronger-phl-us-ties"
        )
        self.session.add(gkg1)

        gkg2 = Gkg(
            id=3771257,
            gkgrecordid="20170215174500-1536",
            date=20170215174500,
            document_identifier="http://wynkcountry.iheart.com/onair/cmt-cody-alan-54719/thomas-rhett-and-lauren-akins-are-15565244/"
        )
        self.session.add(gkg2)
        self.session.commit()

    def tearDown(self):
        self.session.rollback()
        for gkg in self.session.query(Gkg).all():
            self.session.delete(gkg)
        self.session.commit()

    def test_status_update(self):
        gkg = self.session.query(Gkg).first()
        analysis = Analysis(gkg=gkg, status=Status.NEW)
        self.session.add(analysis)
        self.session.commit()

        analysis.create_new_version(Status.SCRAPING)
        self.assertEqual(analysis.status, Status.SCRAPING)

        # meanwhile, some other process changed the status of this...
        session2 = Session()
        try:
            other = session2.query(Analysis).get(analysis.gkg_id)
            other.create_new_version(Status.SCRAPING_FAILED)
        finally:
            session2.rollback()

        with self.assertRaises(NotLatestException):
            analysis.create_new_version(Status.SCRAPED)

    def test_version_lifecycle(self):
        gkg = self.session.query(Gkg).first()
        analysis = Analysis(gkg=gkg, status=Status.NEW)
        self.session.add(analysis)
        self.session.commit()

        analysis.create_new_version(Status.SCRAPING)

        history = self.session.query(AnalysisHistory).filter(AnalysisHistory.gkg == gkg)
        self.assertEqual(1, history.count())
        self.assertEqual(1, history.filter(AnalysisHistory.status == Status.NEW).count())

        content = DocumentContent(content_type="text/html", content="Lorem ipsum")
        analysis.content = content
        analysis.create_new_version(Status.SCRAPED)

        self.assertEqual(2, history.count())
        self.assertEqual(1, history.filter(AnalysisHistory.status == Status.NEW).count())
        self.assertEqual(1, history.filter(AnalysisHistory.status == Status.SCRAPING).count())

        analysis.create_new_version(Status.EXTRACTING)

        self.assertEqual(3, history.count())
        self.assertEqual(1, history.filter(AnalysisHistory.status == Status.NEW).count())
        self.assertEqual(1, history.filter(AnalysisHistory.status == Status.SCRAPING).count())
        self.assertEqual(1, history.filter(AnalysisHistory.status == Status.SCRAPED).count())

        # content is preserved
        scraped = history.filter(AnalysisHistory.status == Status.SCRAPED).one_or_none()
        self.assertEqual(analysis.content, scraped.content)

        fact = Fact(analysis_date=datetime.now())
        analysis.facts = [fact]
        analysis.create_new_version(Status.EXTRACTED)

        self.assertEqual(4, history.count())
        self.assertEqual(1, history.filter(AnalysisHistory.status == Status.NEW).count())
        self.assertEqual(1, history.filter(AnalysisHistory.status == Status.SCRAPING).count())
        self.assertEqual(1, history.filter(AnalysisHistory.status == Status.SCRAPED).count())
        self.assertEqual(1, history.filter(AnalysisHistory.status == Status.EXTRACTING).count())

        # content still preserved
        extracting = history.filter(AnalysisHistory.status == Status.EXTRACTING).one_or_none()
        self.assertEqual(analysis.content, extracting.content)

        analysis.create_new_version(Status.EDITING)
        analysis.content = DocumentContent(content_type="text/html", content="Lorem edited")
        analysis.create_new_version(Status.EDITED)

        self.assertEqual(6, history.count())
        self.assertEqual(1, history.filter(AnalysisHistory.status == Status.NEW).count())
        self.assertEqual(1, history.filter(AnalysisHistory.status == Status.SCRAPING).count())
        self.assertEqual(1, history.filter(AnalysisHistory.status == Status.SCRAPED).count())
        self.assertEqual(1, history.filter(AnalysisHistory.status == Status.EXTRACTING).count())
        self.assertEqual(1, history.filter(AnalysisHistory.status == Status.EXTRACTED).count())
        self.assertEqual(1, history.filter(AnalysisHistory.status == Status.EDITING).count())

        # content has changed, but reports are preserved
        extracted = history.filter(AnalysisHistory.status == Status.EXTRACTED).one_or_none()
        self.assertNotEqual(analysis.content.id, extracted.content.id)
        self.assertCountEqual([f.id for f in analysis.facts], [f.id for f in extracted.facts])

        analysis.create_new_version(Status.EDITING)
        fact2 = Fact(analysis_date=datetime.now())
        analysis.facts.append(fact2)
        analysis.create_new_version(Status.EDITED)

        self.assertEqual(8, history.count())
        self.assertEqual(1, history.filter(AnalysisHistory.status == Status.NEW).count())
        self.assertEqual(1, history.filter(AnalysisHistory.status == Status.SCRAPING).count())
        self.assertEqual(1, history.filter(AnalysisHistory.status == Status.SCRAPED).count())
        self.assertEqual(1, history.filter(AnalysisHistory.status == Status.EXTRACTING).count())
        self.assertEqual(1, history.filter(AnalysisHistory.status == Status.EXTRACTED).count())
        self.assertEqual(2, history.filter(AnalysisHistory.status == Status.EDITING).count())
        self.assertEqual(1, history.filter(AnalysisHistory.status == Status.EDITED).count())

        edited = history.filter(AnalysisHistory.status == Status.EDITED).one_or_none()
        self.assertCountEqual([f.id for f in analysis.facts], [fact.id, fact2.id])
        self.assertCountEqual([f.id for f in edited.facts], [fact.id])

    def test_status_counts(self):
        gkgs = self.session.query(Gkg).all()[:2]
        analysis1 = Analysis(gkg=gkgs[0], status=Status.NEW)
        self.session.add(analysis1)
        self.session.commit()

        self.assertEqual(Analysis.status_counts(self.session),
                         {Status.NEW: 1})

        analysis1.create_new_version(Status.SCRAPING)

        self.assertEqual(Analysis.status_counts(self.session),
                         {Status.SCRAPING: 1})

        analysis2 = Analysis(gkg=gkgs[1], status=Status.NEW)
        self.session.add(analysis2)
        self.session.commit()

        self.assertEqual(Analysis.status_counts(self.session),
                         {Status.NEW: 1,
                          Status.SCRAPING: 1})

        analysis2.create_new_version(Status.SCRAPING)

        self.assertEqual(Analysis.status_counts(self.session),
                         {Status.SCRAPING: 2})

        analysis2.create_new_version(Status.SCRAPED)

        self.assertEqual(Analysis.status_counts(self.session),
                         {Status.SCRAPED: 1,
                          Status.SCRAPING: 1})

    def test_country_term(self):
        mmr = Country(iso3="MMR", preferred_term="Myanmar")
        myanmar = CountryTerm(term="Myanmar", country=mmr)
        burma = CountryTerm(term="Burma", country=mmr)
        yangon = Location(location_name="Yangon",
                          location_type=LocationType.CITY,
                          country=mmr,
                          latlong="16°51′N 96°11′E")

        self.assertEqual(yangon.country, myanmar.country)
        self.assertEqual(yangon.country, burma.country)
