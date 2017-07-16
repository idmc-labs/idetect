import sqlalchemy
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base


import os

from sqlalchemy import Table, text
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean, Numeric
from sqlalchemy.orm import sessionmaker, relationship, object_session
from datetime import datetime
from sqlalchemy.sql import func

Base = declarative_base()
Session = sessionmaker()

def db_url():
    """Return the database URL based on environment variables"""
    return 'postgresql://{user}:{passwd}@{db_host}/{db}'.format(
        user=os.environ.get('DB_USER'),
        passwd=os.environ.get('DB_PASSWORD'),
        db_host=os.environ.get('DB_HOST'),
        db=os.environ.get('DB_NAME'))


class Status:
    NEW = 'new'
    FETCHING = 'fetching'
    FETCHED = 'fetched'
    PROCESSING = 'processing'
    PROCESSED = 'processed'
    FETCHING_FAILED = 'fetching failed'
    PROCESSING_FAILED = 'processing failed'


class UnexpectedArticleStatusException(Exception):
    def __init__(self, article, expected, actual):
        super(UnexpectedArticleStatusException, self).__init__(
            "Expected article {id} to be in state {expected}, but was in state {actual}".format(
                id=article.id, expected=expected, actual=actual
            ))
        self.expected = expected
        self.actual = actual


class Article(Base):
    __tablename__ = 'article'

    id = Column(Integer, primary_key=True)
    url = Column(String)
    status = Column(String)
    created = Column(DateTime(timezone=True), server_default=func.now())
    updated = Column(DateTime(timezone=True), onupdate=func.now())

    def update_status(self, new_status):
        """
        Atomically Update the status of this Article from to new_status.
        If something changed the status of this article since it was loaded, raise.
        """
        session = object_session(self)
        if not session:
            raise RuntimeError("Object has not been persisted in a session.")

        expected_status = self.status
        result = session.query(Article).filter(Article.id == self.id, Article.status == self.status) \
            .update(
            {
                Article.status: new_status
            })
        if result != 1:
            updated = session.query(Article).filter(Article.id == self.id).one()
            raise UnexpectedArticleStatusException(self, expected_status, updated.status)