from sqlalchemy import Column, Integer, String, Date, ForeignKey, text, column, insert, func

from idetect.model import Base
from idetect.values import values


class FactApi(Base):
    __tablename__ = 'idetect_fact_api'

    document_identifier = Column(String)
    source_common_name = Column(String)
    gdelt_day = Column(Date)
    fact = Column(Integer,
                  ForeignKey('idetect_facts.id'),
                  primary_key=True)
    unit = Column(String)
    term = Column(String)
    specific_reported_figure = Column(Integer)
    vague_reported_figure = Column(String)
    iso3 = Column(String)

    location = Column(Integer,
                      ForeignKey('idetect_locations.id'),
                      primary_key=True)

    gkg_id = Column(Integer,
                    ForeignKey('idetect_analyses.gkg_id'),
                    primary_key=True)
    category = Column(String)
    content_id = Column(Integer, ForeignKey('idetect_document_contents.id'))


class TempFactApiFiltered(Base):
    __tablename__ = 'temp_fact_api_filtered'

    document_identifier = Column(String)
    source_common_name = Column(String)
    gdelt_day = Column(Date)
    fact = Column(Integer,
                  ForeignKey('idetect_facts.id'),
                  primary_key=True)
    unit = Column(String)
    term = Column(String)
    specific_reported_figure = Column(Integer)
    vague_reported_figure = Column(String)
    iso3 = Column(String)

    location = Column(Integer,
                      ForeignKey('idetect_locations.id'),
                      primary_key=True)

    gkg_id = Column(Integer,
                    ForeignKey('idetect_analyses.gkg_id'),
                    primary_key=True)
    category = Column(String)
    content_id = Column(Integer, ForeignKey('idetect_document_contents.id'))

    @staticmethod
    def populate_from_select(query):
        session = query.session
        # Create the temporary table. SQLAlchemy doesn't have a nice way to do this
        session.execute(text("""
            DROP TABLE IF EXISTS temp_fact_api_filtered;
            CREATE TEMPORARY TABLE temp_fact_api_filtered 
            (LIKE idetect_fact_api)
            ON COMMIT DROP;
        """))
        # populate the table with the query
        session.execute(insert(TempFactApiFiltered).from_select(
            TempFactApiFiltered.__table__.c,
            query))


def filter_by_locations(query, locations):
    loctuples = [(l,) for l in set(locations)]
    locs = values(
        [column('location_id', Integer)],
        *loctuples,
        alias_name='locs'
    )
    return query.filter(FactApi.location == locs.c.location_id)


def add_filters(query, fromdate=None, todate=None, locations=None,
                categories=None, units=None, sources=None,
                terms=None, iso3s=None, figures=None):
    if fromdate:
        query = query.filter(FactApi.gdelt_day >= fromdate)
    if todate:
        query = query.filter(FactApi.gdelt_day <= todate)
    if locations:
        query = filter_by_locations(query, locations)
    if categories:
        query = query.filter(FactApi.category.in_(categories))
    if units:
        query = query.filter(FactApi.unit.in_(units))
    if sources:
        query = query.filter(FactApi.source_common_name.in_(sources))
    if terms:
        query = query.filter(FactApi.term.in_(terms))
    if iso3s:
        query = query.filter(FactApi.iso3.in_(iso3s))
    if figures:
        query = query.filter(FactApi.specific_reported_figure.in_(figures))
    return query


def get_filter_counts(session, **filters):
    filter_counts = []
    for filter_column in ('category', 'unit', 'source_common_name', 'term', 'iso3', 'specific_reported_figure'):
        column = FactApi.__table__.c[filter_column]
        query = add_filters(session.query(func.count(FactApi.fact), column), **filters).group_by(column)
        for count, value in query.all():
            filter_counts.append({'count': count, 'value': value, 'filter_type': filter_column})
    return filter_counts
