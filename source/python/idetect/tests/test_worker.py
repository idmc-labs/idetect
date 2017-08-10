import logging
import os
import random
import time
from datetime import datetime
from unittest import TestCase

from sqlalchemy import create_engine

from idetect.model import Base, Session, Status, Article, create_indexes
from idetect.worker import Worker

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class TestWorker(TestCase):
    def setUp(self):
        worker_logger = logging.getLogger("idetect.worker")
        worker_logger.setLevel(logging.INFO)

        db_host = os.environ.get('DB_HOST')
        db_url = 'postgresql://{user}:{passwd}@{db_host}/{db}'.format(
            user='tester', passwd='tester', db_host=db_host, db='idetect_test')
        self.engine = create_engine(db_url)
        Session.configure(bind=self.engine)
        Base.metadata.create_all(self.engine)
        create_indexes(self.engine)
        self.session = Session()
        self.processes = []
        logging.basicConfig()

    def tearDown(self):
        for process in self.processes:
            logger.debug("Terminating {}".format(process))
            process.terminate()
        self.session.rollback()
        if self.session.query(Article).filter(Article.url == 'http://example.com').delete() > 0:
            self.session.commit()

    @staticmethod
    def nap_fn(article):
        time.sleep(random.randrange(1))

    def test_work_one(self):
        worker = Worker(Status.NEW, Status.SCRAPING, Status.SCRAPED, Status.SCRAPING_FAILED,
                        TestWorker.nap_fn, self.engine)
        article = Article(url='http://example.com', url_id=1, status=Status.NEW)
        self.session.add(article)
        self.session.commit()
        self.assertTrue(worker.work(), "Worker didn't find work")

        article2 = article.get_updated_version()
        self.assertEqual(article2.status, Status.SCRAPED)

        self.assertFalse(worker.work(), "Worker found work")

    @staticmethod
    def err_fn(article):
        raise RuntimeError("Nope")

    def test_work_failure(self):
        worker = Worker(Status.NEW, Status.SCRAPING, Status.SCRAPED, Status.SCRAPING_FAILED,
                        TestWorker.err_fn, self.engine)
        article = Article(url='http://example.com', url_id=1, status=Status.NEW)
        self.session.add(article)
        self.session.commit()
        self.assertTrue(worker.work(), "Worker didn't find work")

        article2 = article.get_updated_version()
        self.assertEqual(article2.status, Status.SCRAPING_FAILED)

        self.assertFalse(worker.work(), "Worker found work")

    def test_work_chain(self):
        worker1 = Worker(Status.NEW, Status.SCRAPING, Status.SCRAPED, Status.SCRAPING_FAILED,
                         TestWorker.nap_fn, self.engine)
        worker2 = Worker(Status.SCRAPED, Status.EXTRACTING, Status.EXTRACTED, Status.EXTRACTING_FAILED,
                         TestWorker.nap_fn, self.engine)
        article = Article(url='http://example.com', url_id=1, status=Status.NEW)
        self.session.add(article)
        self.session.commit()
        self.assertFalse(worker2.work(), "Worker2 found work")
        self.assertTrue(worker1.work(), "Worker didn't find work")
        self.assertTrue(worker2.work(), "Worker didn't find work")

        article2 = article.get_updated_version()
        self.assertEqual(article2.status, Status.EXTRACTED)

        self.assertFalse(worker1.work(), "Worker1 found work")
        self.assertFalse(worker2.work(), "Worker2 found work")

    def test_work_all(self):
        worker = Worker(Status.NEW, Status.SCRAPING, Status.SCRAPED, Status.SCRAPING_FAILED,
                        TestWorker.nap_fn, self.engine)
        n = 3
        for i in range(n):
            article = Article(url='http://example.com', url_id=i, status=Status.NEW)
            self.session.add(article)
            self.session.commit()
        self.assertEqual(worker.work_all(), 3)

        self.assertEqual(Article.select_latest_version(self.session).filter(Article.status == Status.NEW).count(), 0)
        self.assertEqual(Article.select_latest_version(self.session).filter(Article.status == Status.SCRAPED).count(), n)

    def test_work_parallel(self):
        n = 100
        for i in range(n):
            article = Article(url='http://example.com', url_id=i, status=Status.NEW)
            self.session.add(article)
            self.session.commit()
        remaining = Article.select_latest_version(self.session).filter(Article.status == Status.NEW).count()
        self.assertEqual(remaining, n)
        self.processes += Worker.start_processes(4, Status.NEW, Status.SCRAPING, Status.SCRAPED, Status.SCRAPING_FAILED,
                                                 TestWorker.nap_fn, self.engine)
        self.engine.dispose()
        self.session = Session()
        start = datetime.now()
        max_seconds = int(n / len(self.processes))  # shouldn't take longer than this...
        for i in range(max_seconds):
            remaining = Article.select_latest_version(self.session).filter(Article.status == Status.NEW).count()
            if remaining == 0:
                logger.info("Processing took {}".format(datetime.now() - start))
                break
            logger.info("{} remain after {}".format(remaining, datetime.now() - start))
            time.sleep(1)
        else:
            logger.info("Processing took {} seconds!.".format(datetime.now() - start))
            self.fail("Did not complete work after {} seconds".format(max_seconds))
        time.sleep(1)
