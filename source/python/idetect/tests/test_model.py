import os
from datetime import datetime
from unittest import TestCase

import sqlalchemy
from sqlalchemy import create_engine

from idetect.model import Base, Session, Status, Article, UnexpectedArticleStatusException


class TestModel(TestCase):
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

    def test_status_update(self):
        article = Article(url='http://example.com',
                          status=Status.NEW)
        self.session.add(article)
        self.session.commit()

        article.update_status(Status.FETCHING)
        self.session.commit()
        self.assertEqual(article.status, Status.FETCHING)

        # meanwhile, some other process changed the status of this...
        self.session.execute("UPDATE article SET status = :status WHERE id = :id",
                             { 'status': Status.FETCHING_FAILED, 'id': article.id})

        with self.assertRaises(UnexpectedArticleStatusException):
            article.update_status(Status.FETCHED)