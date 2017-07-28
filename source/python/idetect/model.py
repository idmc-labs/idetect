import os

from sqlalchemy import Column, Integer, String, DateTime, Boolean, Numeric, ForeignKey, Table, desc
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, object_session, relationship, make_transient
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


class NotLatestException(Exception):
    def __init__(self, ours, other):
        super(NotLatestException, self).__init__(
            "Tried to update {} ({}), but {} ({}) was the latest".format(ours, ours.updated, other, other.updated)
        )
        self.ours = ours
        self.other = other


article_content = Table(
    'article_content', Base.metadata,
    Column('article', ForeignKey('article.id', ondelete="CASCADE"), primary_key=True),
    Column('content', ForeignKey('content.id', ondelete="CASCADE"), primary_key=True)
)

article_report = Table(
    'article_report', Base.metadata,
    Column('article', ForeignKey('article.id', ondelete="CASCADE"), primary_key=True),
    Column('report', ForeignKey('report.id', ondelete="CASCADE"), primary_key=True)
)

class Article(Base):
    __tablename__ = 'article'

    id = Column(Integer, primary_key=True)
    url_id = Column(Integer, nullable=False)
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
    retrieval_attempts = Column(Integer)
    completion = Column(Numeric)
    publication_date = Column(DateTime)
    retrieval_date = Column(DateTime)
    created = Column(DateTime(timezone=True), server_default=func.now())
    updated = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    content = relationship(
        'Content', secondary=article_content, back_populates='article')
    reports = relationship('Report', secondary=article_report, back_populates='article')

    def __str__(self):
        return "<Article {} {} {}>".format(self.id, self.url_id, self.url)

    def get_updated_version(self):
        """Return the most recent version of this article by updated timestamp"""
        return Article.get_latest_version(object_session(self), self.url_id)

    @classmethod
    def get_latest_version(cls, session, url_id=None, url=None, lock=False):
        """
        Return the Article with the given url_id or url with the most recent updated timestamp.
        If lock is True, uses FOR UPDATE locking, so that other calls to get_latest_version will
        block until the transaction is committed or rolled back.
        """
        query = session.query(cls)
        if url_id is not None:
            query = query.filter(Article.url_id == url_id)
        if url is not None:
            query = query.filter(Article.url == url)
        # if neither url_id nor url is provided, this returns the most recent article overall
        if lock:
            # This prevents this being run again until the transaction is committed or rolled back
            query = query.with_for_update()
        return query.order_by(desc(Article.updated)).limit(1).first()

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

            # lock to prevent simultaneous updates
            latest = Article.get_latest_version(session, self.url_id, lock=True)
            if latest.id != self.id:
                raise NotLatestException(self, latest)

            reports = self.reports
            content = self.content

            make_transient(self)
            self.id = None
            self.updated = None
            self.status = new_status
            session.add(self)
            session.commit()
            self.reports = reports
            self.content = content
            session.add(self)
            session.commit()
        finally:
            session.rollback()  # make sure we release the FOR UPDATE lock

    @classmethod
    def select_latest_version(cls, session):
        """
        Returns a SELECT query that will only match the most recent versions of the articles it matches.
        You can further filter/order/limit the query.
        """
        sub = session.query(
            Article,
            func.row_number().over(
                partition_by=Article.url_id,
                order_by=desc(Article.updated)
            ).label("row_number")
        ).subquery("a")
        query = session.query(Article).select_entity_from(sub).filter(sub.c.row_number == 1)
        return query


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
    article = relationship('Article', secondary=article_report, back_populates='reports')
    sentence_start = Column(Integer)
    sentence_end = Column(Integer)
    reporting_unit = Column(String)
    reporting_term = Column(String)
    mentions_displacement_figure = Column(Boolean)
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
