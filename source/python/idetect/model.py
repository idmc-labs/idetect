import os

from sqlalchemy import Column, Integer, String, DateTime, Boolean, Numeric, ForeignKey, Table
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, object_session, relationship
from sqlalchemy.orm.exc import NoResultFound
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
            "Expected article {} to be in state {}, but was in state {}".format(article.id, expected, actual))
        self.expected = expected
        self.actual = actual


article_content = Table(
    'article_content', Base.metadata,
    Column('article', ForeignKey('article.id'), primary_key=True),
    Column('content', ForeignKey('content.id'), primary_key=True)
)


class Article(Base):
    __tablename__ = 'article'

    id = Column(Integer, primary_key=True)
    url_id = Column(Integer)
    url = Column(String)
    domain = Column(String)
    status = Column(String)
    title = Column(String)
    authors = Column(String)
    language = Column(String(2))
    relevance = Column(Boolean)
    category = Column(String)
    accuracy = Column(Numeric)
    analyzer = Column(String)
    response_code = Column(Integer)
    retrieval_attempts = Column(Integer, default=0)
    completion = Column(Numeric)
    publication_date = Column(DateTime(timezone=True))
    retrieval_date =Column(DateTime(timezone=True), server_default=func.now())
    created = Column(DateTime(timezone=True), server_default=func.now())
    updated = Column(DateTime(timezone=True), onupdate=func.now())
    content = relationship(
        'Content', secondary=article_content, back_populates='article')
    reports = relationship('Report')

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
            try:
                updated = session.query(Article).filter(
                    Article.id == self.id).one()
                raise UnexpectedArticleStatusException(
                    self, expected_status, updated.status)
            except NoResultFound:
                raise UnexpectedArticleStatusException(
                    self, expected_status, None)


class Content(Base):
    __tablename__ = 'content'

    id = Column(Integer, primary_key=True)
    article = relationship(
        'Article', secondary=article_content, back_populates='content')
    content = Column(String)
    content_type = Column(String)


class ReportUnit:
    PEOPLE = 'people'
    HOUSEHOLDS = 'households'


class ReportTerm:
    DISPLACED = 'displaced'
    EVACUATED = 'evacuated'
    FLED = 'forced to flee'
    HOMELESS = 'homeless'
    CAMP = 'in relief camp'
    SHELTERED = 'sheltered'
    RELOCATED = 'relocated'
    DESTROYED = 'destroyed housing'
    DAMAGED = 'partially destroyed housing'
    UNINHABITABLE = 'uninhabitable housing'


report_location = Table(
    'report_location', Base.metadata,
    Column('report', Integer, ForeignKey('report.id')),
    Column('location', Integer, ForeignKey('location.id'))
)


class Report(Base):
    __tablename__ = 'report'

    id = Column(Integer, primary_key=True, unique=True)
    article_id = Column('article', Integer, ForeignKey(
        'article.id'))
    article = relationship('Article', back_populates='reports')
    sentence_start = Column(Integer)
    sentence_end = Column(Integer)
    reporting_unit = Column(String)
    reporting_term = Column(String)
    specific_displacement_figure = Column(Integer)
    vague_displacement_figure = Column(String)
    tag_locations = Column(String)
    analyzer = Column(String)
    accuracy = Column(Numeric)
    analysis_date = Column(DateTime)
    locations = relationship(
        'Location', secondary=report_location, back_populates='reports')


class Country(Base):
    __tablename__ = 'country'

    code = Column(String(3), primary_key=True)
    preferred_term = Column(String)


class CountryTerm(Base):
    __tablename__ = 'country_term'

    term = Column(String, primary_key=True)
    country = Column(String(3), ForeignKey(Country.code))


class LocationType:
    ADDRESS = 'address'
    NEIGHBORHOOD = 'neighborhood'
    CITY = 'city'
    SUBDIVISION = 'subdivision'
    COUNTRY = 'country'
    UNKNOWN = 'unknown'


class Location(Base):
    __tablename__ = 'location'

    id = Column(Integer, primary_key=True, unique=True)
    description = Column(String)
    location_type = Column(String)
    country_code = Column('country', ForeignKey(Country.code))
    country = relationship(Country)
    latlong = Column(String)
    reports = relationship(
        'Report', secondary=report_location, back_populates='locations')
