import os
import ast
import re
import string

from sqlalchemy import Column, BigInteger, Integer, String, Date, DateTime, Boolean, Numeric, ForeignKey, Table, Index
from sqlalchemy.dialects import postgresql
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


class DisplacementType:
    OTHER = 'Other'
    DISASTER = 'Disaster'
    CONFLICT = 'Conflict'


class Relevance:
    DISPLACEMENT = True
    NOT_DISPLACEMENT = False


class NotLatestException(Exception):
    pass


class DocumentType:
    WEB = 'WEB'
    EML = 'EML'
    PDF = 'PDF'
    EXL = 'EXL'


class Document(Base):
    __tablename__ = 'documents'

    id = Column(Integer, primary_key=True)
    legacy_id = Column(BigInteger)
    idx = Column(BigInteger)
    name = Column(String, nullable=False)  # Document title
    serial_no = Column(String)  # eg. D2016-PDF-000005
    type = Column(String, nullable=False)  # DocumentType, eg. WEB
    publication_date = Column(Date)
    comment = Column(String)
    url = Column(String)
    original_filename = Column(String)  # filename
    filename = Column(String)  # uuid based filename
    content_type = Column(String)  # eg. application/pdf
    displacement_types = Column(postgresql.ARRAY(String))  # eg. {Conflict, Disaster}
    countries = Column(postgresql.ARRAY(String))  # eg. {Haiti,Bahamas,"United States of America"}
    sources = Column(postgresql.ARRAY(String))  # eg. {IOM,"CCCM Cluster",WFP,"Local Authorities"}
    publishers = Column(postgresql.ARRAY(String))  # eg. {REDLAC,"Radio La Primerísima"}
    confidential = Column(Boolean)
    created_by = Column(String)  # eg. First.Last
    created_at = Column(DateTime(timezone=False), server_default=func.now())
    modified_by = Column(String)  # eg. First.Last
    modified_at = Column(DateTime(timezone=False), server_default=func.now())


analysis_fact = Table(
    'idetect_analysis_facts', Base.metadata,
    Column('analysis', ForeignKey('idetect_analyses.document_id', ondelete="CASCADE"), primary_key=True),
    Column('fact', ForeignKey('idetect_facts.id', ondelete="CASCADE"), primary_key=True)
)

analysis_history_fact = Table(
    'idetect_analysis_history_facts', Base.metadata,
    Column('analysis_history', ForeignKey('idetect_analysis_histories.id', ondelete="CASCADE"), primary_key=True),
    Column('fact', ForeignKey('idetect_facts.id', ondelete="CASCADE"), primary_key=True)
)


def cleanup(text):
    """
    Cleanup text based on commonly encountered errors.
    param: text     A string
    return: A cleaned string
    """
    text = re.sub(r'([a-zA-Z0-9])(IMPACT|RESPONSE)', r'\1. \2', text)
    text = re.sub(r'(IMPACT|RESPONSE)([a-zA-Z0-9])', r'\1. \2', text)
    text = re.sub(r'([a-zA-Z])(\d)', r'\1. \2', text) 
    text = re.sub(r'(\d)\s(\d)', r'\1\2', text)
    text = text.replace('\s+', ' ')
    text = text.replace("peole", "people")
    output = ''.join([c for c in text if c in string.printable])
    return output


class Analysis(Base):
    __tablename__ = 'idetect_analyses'

    document_id = Column(Integer,
                         ForeignKey('documents.id', ondelete="CASCADE"),
                         primary_key=True)
    document = relationship('Document')
    status = Column(String, nullable=False)
    title = Column(String)
    publication_date = Column(DateTime(timezone=True))
    authors = Column(String)
    language = Column(String(2))
    relevance = Column(Boolean)
    category = Column(String)
    accuracy = Column(Numeric)
    analyzer = Column(String)
    response_code = Column(Integer)
    retrieval_attempts = Column(Integer, default=0)
    completion = Column(Numeric)
    retrieval_date = Column(DateTime(timezone=True))
    created = Column(DateTime(timezone=True), server_default=func.now())
    updated = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    facts = relationship('Fact', secondary=analysis_fact, back_populates='analysis')
    content_id = Column(Integer, ForeignKey('idetect_document_contents.id'))
    content = relationship('DocumentContent', back_populates='analysis')
    error_msg = Column(String)
    processing_time = Column(Numeric)  # time it took to process to bring it to the current status

    def __str__(self):
        return "<DocumentAnalysis {} {} {}>".format(self.document_id, self.document.url)

    def get_updated_version(self):
        """Return the most recent version of this article"""
        # can't just use get() because that will use the cache instead of running a query
        return object_session(self).query(Analysis) \
            .filter(Analysis.document_id == self.document_id).one()

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
                latest = session.query(Analysis) \
                    .filter(Analysis.document_id == self.document_id) \
                    .filter(Analysis.status == self.status) \
                    .with_for_update().one()
            except NoResultFound:
                raise NotLatestException(self)

            dict = {c.name: self.__getattribute__(c.name) for c in Analysis.__table__.columns}
            history = AnalysisHistory(**dict)
            history.facts = self.facts
            session.add(history)

            self.updated = func.now()
            self.status = new_status
            session.commit()
        finally:
            session.rollback()  # make sure we release the FOR UPDATE lock

    def tagged_text(self):
        # Add tags to article content for display purposes
        spans = self.get_unique_tag_spans()
        text = self.content.content_clean
        text_blocks = []
        text_start_point = 0
        for span in spans:
                text_blocks.append(text[text_start_point : span['start']])

                tagged_text = '<mark data-entity="{}">'.format(span['type'].lower())
                tagged_text += text[span['start'] : span['end']]
                tagged_text += '</mark>'
                text_blocks.append(tagged_text)
                text_start_point = span['end']
        text_blocks.append(text[text_start_point : ])
        return("".join(text_blocks))

    def get_unique_tag_spans(self):
        '''Get a list of unique token spans
        for visualizing a complete article along
        with all extracted facts.
        Each extracted report has its own list of spans
        which may in some cases overlap, particularly
        for date and location tags.
        '''
        ### need to deal with overlapping spans
        all_spans = []
        for fact in self.facts:
            all_spans.extend(ast.literal_eval(fact.tag_locations))
        unique_spans = list({v['start']: v for v in all_spans}.values())
        unique_spans = sorted(unique_spans, key=lambda k: k['start'])
        ### Check for no overlap
        non_overlapping_spans = []
        current_start = -1
        current_end = -1
        for span in unique_spans:
            if span['start'] > current_end:
                non_overlapping_spans.append(span)
                current_start, current_end = span['start'], span['end']
            else:
                # Create a new merged span and add it to the end of the result
                current_last_span = non_overlapping_spans[-1]
                new_span = {}
                new_span['type'] = ", ".join([current_last_span['type'], span['type']])
                new_span['start'] = current_last_span['start']
                new_span['end'] = max(current_last_span['end'], span['end'])
                non_overlapping_spans[-1] = new_span
                current_end = new_span['end']

        return non_overlapping_spans

    @classmethod
    def status_counts(cls, session):
        """Returns a dictonary of status to the count of the Articles that have that status as their latest value"""
        status_counts = session.query(Analysis.status, func.count(Analysis.status)) \
            .group_by(Analysis.status).all()
        return dict(status_counts)

    @classmethod
    def category_counts(cls, session):
        cat_counts = session.query(Analysis)\
                .filter(Analysis.relevance == True)\
                .with_entities(Analysis.category, func.count(Analysis.document_id))\
                .group_by(Analysis.category).all()
        cat_counts = dict(cat_counts)
        cat_counts['Not Relevant'] = session.query(Analysis)\
                .filter(Analysis.relevance == False)\
                .with_entities(func.count(Analysis.document_id)).first()[0]
        return cat_counts



status_updated_index = Index('document_analyses_status_updated', Analysis.status, Analysis.updated)


class AnalysisHistory(Base):
    __tablename__ = 'idetect_analysis_histories'

    id = Column(Integer, primary_key=True)
    document_id = Column(Integer, ForeignKey('documents.id', ondelete="CASCADE"))
    document = relationship('Document')
    status = Column(String, nullable=False)
    title = Column(String)
    publication_date = Column(DateTime(timezone=True))
    authors = Column(String)
    language = Column(String(2))
    relevance = Column(Boolean)
    category = Column(String)
    accuracy = Column(Numeric)
    analyzer = Column(String)
    response_code = Column(Integer)
    retrieval_attempts = Column(Integer, default=0)
    completion = Column(Numeric)
    retrieval_date = Column(DateTime(timezone=True))
    created = Column(DateTime(timezone=True), server_default=func.now())
    updated = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    facts = relationship('Fact', secondary=analysis_history_fact)
    content_id = Column(Integer, ForeignKey('idetect_document_contents.id'))
    content = relationship('DocumentContent')
    error_msg = Column(String)
    processing_time = Column(Numeric)  # time it took to process to bring it to the current status


class DocumentContent(Base):
    __tablename__ = 'idetect_document_contents'

    id = Column(Integer, primary_key=True)
    analysis = relationship('Analysis', back_populates='content')
    content = Column(String)
    content_clean = Column(String)
    content_type = Column(String)


class FactUnit:
    PEOPLE = 'Person'
    HOUSEHOLDS = 'Household'


class FactTerm:
    DISPLACED = 'Displaced'
    EVACUATED = 'Evacuated'
    FLED = 'Forced to Flee'
    HOMELESS = 'Homeless'
    CAMP = 'In Relief Camp'
    SHELTERED = 'Sheltered'
    RELOCATED = 'Relocated'
    DESTROYED = 'Destroyed Housing'
    DAMAGED = 'Partially Destroyed Housing'
    UNINHABITABLE = 'Uninhabitable Housing'
    OTHER = 'Multiple/Other'


fact_location = Table(
    'idetect_fact_locations', Base.metadata,
    Column('fact', Integer, ForeignKey('idetect_facts.id')),
    Column('location', Integer, ForeignKey('idetect_locations.id'))
)


class Fact(Base):
    __tablename__ = 'idetect_facts'

    id = Column(Integer, primary_key=True, unique=True)
    analysis = relationship('Analysis', secondary=analysis_fact, back_populates='facts')
    excerpt_start = Column(Integer)
    excerpt_end = Column(Integer)
    unit = Column(String)
    term = Column(String)
    start_date = Column(DateTime(timezone=True))
    end_date = Column(DateTime(timezone=True))
    specific_reported_figure = Column(Integer)
    vague_reported_figure = Column(String)
    iso3 = Column(String(3))
    qualifier = Column(String)
    tag_locations = Column(String)
    analyzer = Column(String)
    confidence_assessment = Column(Numeric)
    analysis_date = Column(DateTime(timezone=True), server_default=func.now())
    locations = relationship('Location', secondary=fact_location, back_populates='facts')


class Country(Base):
    __tablename__ = 'idetect_countries'

    iso3 = Column(String(3), primary_key=True)
    preferred_term = Column(String)


class CountryTerm(Base):
    __tablename__ = 'idetect_country_terms'

    term = Column(String, primary_key=True)
    country = Column(String(3), ForeignKey(Country.iso3))


class LocationType:
    ADDRESS = 'address'
    NEIGHBORHOOD = 'neighborhood'
    CITY = 'city'
    SUBDIVISION = 'subdivision'
    COUNTRY = 'country'
    UNKNOWN = 'unknown'


class Location(Base):
    __tablename__ = 'idetect_locations'

    id = Column(Integer, primary_key=True, unique=True)
    location_name = Column(String, unique=True)
    location_type = Column(String)
    country_iso3 = Column('country', ForeignKey(Country.iso3))
    country = relationship(Country)
    latlong = Column(String)
    facts = relationship('Fact', secondary=fact_location, back_populates='locations')


class KeywordType:
    PERSON_TERM = 'person_term'
    PERSON_UNIT = 'person_unit'
    STRUCTURE_TERM = 'structure_term'
    STRUCTURE_UNIT = 'structure_unit'
    ARTICLE_KEYWORD = 'article_keyword'


class FactKeyword(Base):
    __tablename__ = 'idetect_fact_keywords'

    id = Column(Integer, primary_key=True)
    description = Column(String)
    keyword_type = Column(String)
