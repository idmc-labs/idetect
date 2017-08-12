import os

from sqlalchemy import Column, Integer, String, DateTime, Boolean, Numeric, ForeignKey, Table, desc, Index
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, object_session, relationship
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.sql import func

Base = declarative_base()
Session = sessionmaker()

from sqlalchemy.schema import DropTable
from sqlalchemy.ext.compiler import compiles


@compiles(DropTable, "postgresql")
def _compile_drop_table(element, compiler, **kwargs):
    return compiler.visit_drop_table(element) + " CASCADE"


def db_url():
    """Return the database URL based on environment variables"""
    return 'postgresql://{user}:{passwd}@{db_host}/{db}'.format(
        user=os.environ.get('DB_USER'),
        passwd=os.environ.get('DB_PASSWORD'),
        db_host=os.environ.get('DB_HOST'),
        db=os.environ.get('DB_NAME'))


class Status:
    NEW = 'new'
    SCRAPING = 'scraping'
    SCRAPED = 'scraped'
    CLASSIFYING = 'classifying'
    CLASSIFIED = 'classified'
    EXTRACTING = 'extracting'
    EXTRACTED = 'extracted'
    SCRAPING_FAILED = 'scraping failed'
    CLASSIFYING_FAILED = 'classifying failed'
    EXTRACTING_FAILED = 'extracting failed'
    EDITING = 'editing'
    EDITED = 'edited'


class Category:
    OTHER = 'other'
    DISASTER = 'disaster'
    CONFLICT = 'conflict'


class Relevance:
    DISPLACEMENT = 'displacement'
    NOT_DISPLACEMENT = 'not displacement'


class NotLatestException(Exception):
    pass


article_report = Table(
    'article_report', Base.metadata,
    Column('article', ForeignKey('article.id', ondelete="CASCADE"), primary_key=True),
    Column('report', ForeignKey('report.id', ondelete="CASCADE"), primary_key=True)
)

article_history_report = Table(
    'article_history_report', Base.metadata,
    Column('article_history', ForeignKey('article_history.id', ondelete="CASCADE"), primary_key=True),
    Column('report', ForeignKey('report.id', ondelete="CASCADE"), primary_key=True)
)


class Article(Base):
    __tablename__ = 'article'

    id = Column(Integer, primary_key=True)
    url_id = Column(String, nullable=False)
    url = Column(String, nullable=False)
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
    retrieval_date = Column(DateTime(timezone=True))
    created = Column(DateTime(timezone=True), server_default=func.now())
    updated = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    reports = relationship('Report', secondary=article_report, back_populates='article')
    content_id = Column('content', Integer, ForeignKey('content.id'))
    content = relationship('Content', back_populates='article')
    error_msg = Column(String)
    processing_time = Column(Numeric)

    def __str__(self):
        return "<Article {} {} {}>".format(self.id, self.url_id, self.url)

    def get_updated_version(self):
        """Return the most recent version of this article"""
        return object_session(self).query(Article).filter(Article.id == self.id).one()

    def create_new_version(self, new_status):
        """
        Try to create a new version of this article with the new status.
        If this is not the most recent version for this
        url_id, this will raise NotLatestException.
        """
        session = object_session(self)
        try:
            if not session:
                raise RuntimeError("Object has not been persisted in a session.")

            try:
                latest = session.query(Article) \
                    .filter(Article.id == self.id) \
                    .filter(Article.status == self.status) \
                    .with_for_update().one()
            except NoResultFound:
                raise NotLatestException(self)

            dict = {c.name: self.__getattribute__(c.name) for c in Article.__table__.columns}
            dict['article_id'] = dict['id']
            del dict['id']
            history = ArticleHistory(**dict)
            history.reports = self.reports
            session.add(history)

            self.updated = None  # force the DB to update the updated timestamp
            self.status = new_status
            session.commit()
        finally:
            session.rollback()  # make sure we release the FOR UPDATE lock

    @classmethod
    def status_counts(cls, session):
        """Returns a dictonary of status to the count of the Articles that have that status as their latest value"""
        status_counts = session.query(Article.status, func.count(Article.status)) \
            .group_by(Article.status).all()
        return dict(status_counts)

status_updated_index = Index('status_updated', Article.status, Article.updated)

class ArticleHistory(Base):
    __tablename__ = 'article_history'

    id = Column(Integer, primary_key=True)
    article_id = Column(Integer, ForeignKey(Article.id, ondelete="CASCADE"))
    article = relationship(Article)
    url_id = Column(String, nullable=False)
    url = Column(String, nullable=False)
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
    retrieval_date = Column(DateTime(timezone=True))
    created = Column(DateTime(timezone=True), server_default=func.now())
    updated = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    reports = relationship('Report', secondary=article_history_report)
    content_id = Column('content', Integer, ForeignKey('content.id'))
    content = relationship('Content')
    error_msg = Column(String)
    processing_time = Column(Numeric)


class Content(Base):
    __tablename__ = 'content'

    id = Column(Integer, primary_key=True)
    article = relationship('Article', back_populates='content')
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
    article = relationship('Article', secondary=article_report, back_populates='reports')
    sentence_start = Column(Integer)
    sentence_end = Column(Integer)
    reporting_unit = Column(String)
    reporting_term = Column(String)
    specific_displacement_figure = Column(Integer)
    vague_displacement_figure = Column(String)
    tag_locations = Column(String)
    analyzer = Column(String)
    accuracy = Column(Numeric)
    analysis_date = Column(DateTime(timezone=True), server_default=func.now())
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


class KeywordType:
    PERSON_TERM = 'person_term'
    PERSON_UNIT = 'person_unit'
    STRUCTURE_TERM = 'structure_term'
    STRUCTURE_UNIT = 'structure_unit'
    ARTICLE_KEYWORD = 'article_keyword'


class ReportKeyword(Base):
    __tablename__ = 'report_keyword'

    id = Column(Integer, primary_key=True)
    description = Column(String)
    keyword_type = Column(String)


def create_indexes(engine):
    url_id_status_index = Index('url_id_status', Article.url_id, Article.status, Article.updated)
    try:
        url_id_status_index.create(engine)
    except ProgrammingError as exc:
        if "already exists" not in str(exc):
            raise