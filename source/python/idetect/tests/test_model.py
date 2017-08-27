import os
from datetime import datetime, date
from unittest import TestCase

import dateutil.parser
from sqlalchemy import create_engine

from idetect.model import Base, Session, Status, Document, DocumentType, \
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
        document1 = Document(
            id=2749,
            name="Flooding, Water Shortage Expected After Regional Storms Disperse",
            serial_no="D2017-PDF-000575",
            type=DocumentType.PDF,
            publication_date=date(2017, 7, 31),
            url="https://www.cambodiadaily.com/news/flooding-water-shortage-expected-after-regional-storms-disperse-133048/",
            original_filename="Flooding, Water Shortage Expected After Regional Storms Disperse - The Cambodia Daily.pdf",
            filename="96512595-54ed-445b-8add-4df49ace2ee3.pdf",
            content_type='application/pdf',
            displacement_types=['Disaster'],
            countries=["Cambodia"],
            sources=["local authorities"],
            publishers=["The Cambodia Daily"],
            created_by="John.Doe",
            created_at=dateutil.parser.parse("2017-08-12 00:32:47.303859")
        )
        self.session.add(document1)

        document2 = Document(
            id=2743,
            name="OCHA: CAR Eastern Region weekly situation report #24 (18 June 2017)",
            serial_no="D2017-WEB-000274",
            type=DocumentType.PDF,
            publication_date=date(2017, 6, 18),
            url="http://reliefweb.int/sites/reliefweb.int/files/resources/18-06-2017_sous-bureau_de_bambari_rapport_hebdomadaire_vf_0.pdf",
            original_filename="18-06-2017_sous-bureau_de_bambari_rapport_hebdomadaire_vf_0.pdf",
            filename="e2675928-4462-4e27-9464-0f8f2a0a1eff.pdf",
            content_type='application/pdf',
            displacement_types=['Conflict'],
            countries=["Central African Republic"],
            sources=["OCHA"],
            publishers=["OCHA"],
            created_by="Giulia.Rossi",
            created_at=dateutil.parser.parse("2017-08-04 18:20:47"),
            modified_by="Giulia.Rossi",
            modified_at=dateutil.parser.parse("2017-08-04 18:23:00.57118")
        )
        self.session.add(document2)
        self.session.commit()

    def tearDown(self):
        self.session.rollback()
        for article in self.session.query(Document).all():
            self.session.delete(article)
        self.session.commit()

    def test_status_update(self):
        document = self.session.query(Document).first()
        analysis = Analysis(document=document, status=Status.NEW)
        self.session.add(analysis)
        self.session.commit()

        analysis.create_new_version(Status.SCRAPING)
        self.assertEqual(analysis.status, Status.SCRAPING)

        # meanwhile, some other process changed the status of this...
        session2 = Session()
        try:
            other = session2.query(Analysis).get(analysis.document_id)
            other.create_new_version(Status.SCRAPING_FAILED)
        finally:
            session2.rollback()

        with self.assertRaises(NotLatestException):
            analysis.create_new_version(Status.SCRAPED)

    def test_version_lifecycle(self):
        document = self.session.query(Document).first()
        analysis = Analysis(document=document, status=Status.NEW)
        self.session.add(analysis)
        self.session.commit()

        analysis.create_new_version(Status.SCRAPING)

        history = self.session.query(AnalysisHistory).filter(AnalysisHistory.document == document)
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
        documents = self.session.query(Document).all()[:2]
        analysis1 = Analysis(document=documents[0], status=Status.NEW)
        self.session.add(analysis1)
        self.session.commit()

        self.assertEqual(Analysis.status_counts(self.session),
                         {Status.NEW: 1})

        analysis1.create_new_version(Status.SCRAPING)

        self.assertEqual(Analysis.status_counts(self.session),
                         {Status.SCRAPING: 1})

        analysis2 = Analysis(document=documents[1], status=Status.NEW)
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
        mmr = Country(code="MMR", preferred_term="Myanmar")
        myanmar = CountryTerm(term="Myanmar", country=mmr)
        burma = CountryTerm(term="Burma", country=mmr)
        yangon = Location(description="Yangon",
                          location_type=LocationType.CITY,
                          country=mmr,
                          latlong="16°51′N 96°11′E")

        self.assertEqual(yangon.country, myanmar.country)
        self.assertEqual(yangon.country, burma.country)
