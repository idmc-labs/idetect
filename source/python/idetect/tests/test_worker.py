import os
from datetime import datetime
from unittest import TestCase
import random
import time

import sqlalchemy
from sqlalchemy import create_engine

from idetect.model import Base, Session, Status, Article, UnexpectedArticleStatusException
from idetect.worker import Worker


class TestWorker(TestCase):
    def setUp(self):
        db_host = os.environ.get('DB_HOST')
        db_url = 'postgresql://{user}:{passwd}@{db_host}/{db}'.format(
            user='tester', passwd='tester', db_host=db_host, db='idetect_test')
        engine = create_engine(db_url)
        Session.configure(bind=engine)
        Base.metadata.create_all(engine)
        self.session = Session()

    def tearDown(self):
        self.session.rollback()
        version = sqlalchemy.__version__
        self.session.query(Article).filter(Article.url =='http://example.com').delete()
        self.session.commit()

    @staticmethod
    def nap_fn(article):
        time.sleep(random.randrange(1))

    def test_work_one(self):
        worker = Worker(Status.NEW, Status.FETCHING, Status.FETCHED, Status.FETCHING_FAILED, TestWorker.nap_fn)
        article = Article(url='http://example.com', status=Status.NEW)
        self.session.add(article)
        self.session.commit()
        self.assertTrue(worker.work(self.session), "Worker didn't find work")

        article2 = self.session.query(Article).get(article.id)
        self.assertEqual(article2.status, Status.FETCHED)

        self.assertFalse(worker.work(self.session), "Worker found work")

    @staticmethod
    def err_fn(article):
        raise RuntimeError("Nope")

    def test_work_failure(self):
        worker = Worker(Status.NEW, Status.FETCHING, Status.FETCHED, Status.FETCHING_FAILED, TestWorker.err_fn)
        article = Article(url='http://example.com', status=Status.NEW)
        self.session.add(article)
        self.session.commit()
        self.assertTrue(worker.work(self.session), "Worker didn't find work")

        article2 = self.session.query(Article).get(article.id)
        self.assertEqual(article2.status, Status.FETCHING_FAILED)

        self.assertFalse(worker.work(self.session), "Worker found work")

    def test_work_chain(self):
        worker1 = Worker(Status.NEW, Status.FETCHING, Status.FETCHED, Status.FETCHING_FAILED, TestWorker.nap_fn)
        worker2 = Worker(Status.FETCHED, Status.PROCESSING, Status.PROCESSED, Status.PROCESSING_FAILED, TestWorker.nap_fn)
        article = Article(url='http://example.com', status=Status.NEW)
        self.session.add(article)
        self.session.commit()
        self.assertFalse(worker2.work(self.session), "Worker2 found work")
        self.assertTrue(worker1.work(self.session), "Worker didn't find work")
        self.assertTrue(worker2.work(self.session), "Worker didn't find work")

        article2 = self.session.query(Article).get(article.id)
        self.assertEqual(article2.status, Status.PROCESSED)

        self.assertFalse(worker1.work(self.session), "Worker1 found work")
        self.assertFalse(worker2.work(self.session), "Worker2 found work")

    def test_work_all(self):
        worker = Worker(Status.NEW, Status.FETCHING, Status.FETCHED, Status.FETCHING_FAILED, TestWorker.nap_fn)
        n = 3
        for i in range(n):
            article = Article(url='http://example.com', status=Status.NEW)
            self.session.add(article)
            self.session.commit()
        self.assertEqual(worker.work_all(self.session), 3)

        self.assertEqual(self.session.query(Article).filter(Article.status==Status.NEW).count(), 0)
        self.assertEqual(self.session.query(Article).filter(Article.status==Status.FETCHED).count(), n)

