import logging
import os
import random
import time
from datetime import datetime, timedelta
from unittest import TestCase

from sqlalchemy import create_engine, func

from idetect.model import Base, Session, Status, Document, Analysis, DocumentType
from idetect.worker import Worker, Initiator, 

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logging.basicConfig(format="%(asctime)s %(message)s")


# Filter function for identifying analyses to scrape
def scraping_filter(query):
    return query.filter((Analysis.status == Status.NEW) |
                        ((Analysis.status == Status.SCRAPING_FAILED) &
                         (Analysis.retrieval_attempts < 3) &
                         (func.now() > Analysis.retrieval_date + timedelta(hours=12))))


class TestWorker(TestCase):
    def setUp(self):
        logger.debug("setUp")
        worker_logger = logging.getLogger("idetect.worker")
        worker_logger.setLevel(logging.INFO)

        logger.debug("Connecting to DB")
        db_host = os.environ.get('DB_HOST')
        db_url = 'postgresql://{user}:{passwd}@{db_host}/{db}'.format(
            user='tester', passwd='tester', db_host=db_host, db='idetect_test')
        self.engine = create_engine(db_url)
        Session.configure(bind=self.engine)
        logger.debug("Creating")
        Base.metadata.create_all(self.engine)
        self.session = Session()
        self.processes = []
        logger.debug("setUp complete")

    def tearDown(self):
        logger.debug("tearDown")
        for process in self.processes:
            logger.debug("Terminating {}".format(process))
            process.terminate()
        logger.debug("processes terminated")
        self.session.rollback()
        logger.debug("sessions rolled back")
        if self.session.query(Document).delete() > 0:
            self.session.commit()
        logger.debug("tearDown complete")

    @staticmethod
    def nap_fn(analysis):
        time.sleep(random.randrange(1))

    def test_work_one(self):
        worker = Worker(scraping_filter, Status.SCRAPING, Status.SCRAPED, Status.SCRAPING_FAILED,
                        TestWorker.nap_fn, self.engine)
        document = Document(
            type=DocumentType.WEB,
            name="Hurricane Katrina Fast Facts",
            url="http://www.cnn.com/2013/08/23/us/hurricane-katrina-statistics-fast-facts/index.html")
        analysis = Analysis(document=document, status=Status.NEW)
        self.session.add(analysis)
        self.session.commit()
        self.assertTrue(worker.work(), "Worker didn't find work")

        analysis2 = analysis.get_updated_version()
        self.assertEqual(analysis2.status, Status.SCRAPED)
        self.assertIsNotNone(analysis2.processing_time)

        self.assertFalse(worker.work(), "Worker found work")

    @staticmethod
    def err_fn(analysis):
        raise RuntimeError("Nope")

    def test_work_failure(self):
        worker = Worker(scraping_filter, Status.SCRAPING, Status.SCRAPED, Status.SCRAPING_FAILED,
                        TestWorker.err_fn, self.engine)
        document = Document(
            type=DocumentType.WEB,
            name="Hurricane Katrina Fast Facts",
            url="http://www.cnn.com/2013/08/23/us/hurricane-katrina-statistics-fast-facts/index.html")
        analysis = Analysis(document=document, status=Status.NEW)
        self.session.add(analysis)
        self.session.commit()
        self.assertTrue(worker.work(), "Worker didn't find work")

        analysis2 = analysis.get_updated_version()
        self.assertEqual(analysis2.status, Status.SCRAPING_FAILED)
        self.assertIn("Nope", analysis2.error_msg)
        self.assertIsNotNone(analysis2.processing_time)

        self.assertFalse(worker.work(), "Worker found work")

    def test_work_chain(self):
        worker1 = Worker(scraping_filter, Status.SCRAPING, Status.SCRAPED, Status.SCRAPING_FAILED,
                         TestWorker.nap_fn, self.engine)
        worker2 = Worker(Status.SCRAPED, Status.EXTRACTING, Status.EXTRACTED, Status.EXTRACTING_FAILED,
                         TestWorker.nap_fn, self.engine)
        document = Document(
            type=DocumentType.WEB,
            name="Hurricane Katrina Fast Facts",
            url="http://www.cnn.com/2013/08/23/us/hurricane-katrina-statistics-fast-facts/index.html")
        analysis = Analysis(document=document, status=Status.NEW)
        self.session.add(analysis)
        self.session.commit()
        self.assertFalse(worker2.work(), "Worker2 found work")
        self.assertTrue(worker1.work(), "Worker didn't find work")
        self.assertTrue(worker2.work(), "Worker didn't find work")

        analysis2 = analysis.get_updated_version()
        self.assertEqual(analysis2.status, Status.EXTRACTED)

        self.assertFalse(worker1.work(), "Worker1 found work")
        self.assertFalse(worker2.work(), "Worker2 found work")

    def test_work_all(self):
        worker = Worker(scraping_filter, Status.SCRAPING, Status.SCRAPED, Status.SCRAPING_FAILED,
                        TestWorker.nap_fn, self.engine)
        n = 3
        for i in range(n):
            document = Document(
                type=DocumentType.WEB,
                name="Hurricane Katrina Fast Facts",
                url="http://www.cnn.com/2013/08/23/us/hurricane-katrina-statistics-fast-facts/index.html")
            analysis = Analysis(document=document, status=Status.NEW)
            self.session.add(analysis)
            self.session.commit()
        self.assertEqual(worker.work_all(), 3)

        self.assertEqual(self.session.query(Analysis).filter(Analysis.status == Status.NEW).count(), 0)
        self.assertEqual(self.session.query(Analysis).filter(Analysis.status == Status.SCRAPED).count(), n)

    def test_work_parallel(self):
        n = 100
        for i in range(n):
            document = Document(
                type=DocumentType.WEB,
                name="Hurricane Katrina Fast Facts",
                url="http://www.cnn.com/2013/08/23/us/hurricane-katrina-statistics-fast-facts/index.html")
            analysis = Analysis(document=document, status=Status.NEW)
            self.session.add(analysis)
            self.session.commit()
        remaining = self.session.query(Analysis).filter(Analysis.status == Status.NEW).count()
        self.assertEqual(remaining, n)
        self.processes += Worker.start_processes(4, scraping_filter, Status.SCRAPING, Status.SCRAPED, Status.SCRAPING_FAILED,
                                                 TestWorker.nap_fn, self.engine, max_sleep=1)
        self.engine.dispose()
        self.session = Session()
        start = datetime.now()
        max_seconds = int(n / len(self.processes))  # shouldn't take longer than this...
        for i in range(max_seconds):
            remaining = self.session.query(Analysis).filter(Analysis.status == Status.NEW).count()
            if remaining == 0:
                logger.info("Processing took {}".format(datetime.now() - start))
                break
            logger.info("{} remain after {}".format(remaining, datetime.now() - start))
            time.sleep(1)
        else:
            logger.info("Processing took {} seconds!.".format(datetime.now() - start))
            self.fail("Did not complete work after {} seconds".format(max_seconds))
        time.sleep(1)

    def test_initiator(self):
        n = 3
        for i in range(n):
            document = Document(
                type=DocumentType.WEB,
                name="Hurricane Katrina Fast Facts",
                url="http://www.cnn.com/2013/08/23/us/hurricane-katrina-statistics-fast-facts/index.html")
            self.session.add(document)
            self.session.commit()
        initiator = Initiator(self.engine)

        self.assertEqual(self.session.query(Analysis).count(), 0)
        self.assertEqual(initiator.work_all(), 3)
        self.assertEqual(self.session.query(Analysis).filter(Analysis.status == Status.NEW).count(), 3)
