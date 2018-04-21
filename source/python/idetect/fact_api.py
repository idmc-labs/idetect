from sqlalchemy import Column, Integer, String, Date, ForeignKey, column, func, or_, text

from idetect.model import Base, DocumentContent
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


def filter_by_locations(query, locations):
    '''Because the location list is typically quite large, this does a VALUES query instead of an IN'''
    null = False
    if None in locations or 'NULL' in locations or 'null' in locations:
        null = True
        locations = [l for l in locations if isinstance(l, int)]

    if locations:
        loctuples = [(l,) for l in set(locations)]
        locs = values(
            [column('location_id', Integer)],
            *loctuples,
            alias_name='locs'
        )

        if null:
            # Both the NULL location and some actual locations
            return query.filter(or_(FactApi.location == None, FactApi.location == locs.c.location_id))
        return query.filter(FactApi.location == locs.c.location_id)
    if null:
        # Specifically looking for the NULL location only
        return query.filter(FactApi.location == None)
    # No locations to select
    return query


def add_filters(query,
                fromdate=None, todate=None, locations=None,
                categories=None, units=None, sources=None,
                terms=None, iso3s=None, figures=None, ts=None):
    '''Add some of the known filters to the query'''
    query = query.distinct()
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
        # figures are typically passed in as all values in a range
        # it's more efficient to just test the endpoints of the range
        least = min(figures)
        greatest = max(figures)
        query = query.filter(FactApi.specific_reported_figure.between(least, greatest))
    if ts:
        query = (
            query
                .filter(DocumentContent.id == FactApi.content_id)
                .filter(DocumentContent.content_ts.match(ts, postgresql_regconfig='simple_english'))
        )
    return query


def get_filter_counts(session, **filters):
    filter_counts = []
    for filter_column in ('category', 'unit', 'source_common_name', 'term', 'iso3', 'specific_reported_figure'):
        column = FactApi.__table__.c[filter_column]
        query = add_filters(session.query(func.count(FactApi.fact), column), **filters).group_by(column)
        for count, value in query.all():
            filter_counts.append({'count': count, 'value': value, 'filter_type': filter_column})
    return filter_counts


def get_timeline_counts(session, **filters):
    query = (
        add_filters(session.query(func.count(FactApi.fact),
                                  FactApi.gdelt_day,
                                  FactApi.category),
                    **filters)
            .group_by(FactApi.gdelt_day, FactApi.category)
            .order_by(FactApi.gdelt_day, FactApi.category)
    )
    return [{"count": count, "category": category, "gdelt_day": day}
            for count, day, category in query.all()]


def get_histogram_counts(session, **filters):
    query = (
        add_filters(session.query(func.count(FactApi.fact),
                                  FactApi.unit,
                                  FactApi.specific_reported_figure),
                    **filters)
            .group_by(FactApi.unit, FactApi.specific_reported_figure)
            .order_by(FactApi.unit, FactApi.specific_reported_figure)
    )
    return [{"count": count, "unit": unit, "specific_reported_figure": specific_reported_figure}
            for count, unit, specific_reported_figure in query.all()]


def get_wordcloud(session, engine, **filters):
    query = add_filters(session.query(DocumentContent.content_ts).join(FactApi),
                        **filters)
    literal_query = query.statement.compile(engine, compile_kwargs={"literal_binds": True})
    ts_stat = text('''SELECT * FROM ts_stat($${}$$)
                      ORDER BY nentry DESC, ndoc DESC, word
                      LIMIT 20'''.format(literal_query))
    return [{"word": r.word, "nentry": r.nentry, "ndoc": r.ndoc} for r in session.execute(ts_stat)]


def get_urllist(session, limit=32, offset=0, **filters):
    query = (
        add_filters(session.query(FactApi), **filters)
        .order_by(FactApi.gdelt_day, FactApi.gkg_id)
        .limit(limit)
        .offset(offset)
    )
    return query.all()