from sqlalchemy import Column, Integer, String, Date, ForeignKey, column, func, or_, text, literal_column, ARRAY

from idetect.model import Base, DocumentContent, Analysis, Location, fact_location
from idetect.values import values

class FactApiLocations(Base):
    __tablename__ = 'idetect_fact_api_locations'

    fact = Column(Integer,
                  ForeignKey('idetect_fact_locations.fact'),
                  primary_key=True)
    location_ids = Column(ARRAY(Integer))
    location_names = Column(ARRAY(String))
    location_ids_idx = Column(Integer)
    

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
    location_ids_idx = Column(Integer,
                    ForeignKey('idetect_fact_api_locations.fact'),
                    primary_key=True)

class Validation(Base):
    __tablename__ = 'idetect_validation'
    fact_id = Column(Integer,
                     ForeignKey('idetect_facts.id'),
                     primary_key=True)
    status = Column(String)
    missing = Column(String)
    wrong = Column(String)
    assigned_to = Column(String)
    created_by = Column(String)
    created_at = Column(Date)


class ValidationValues(Base):
    __tablename__ = 'idetect_validation_values'
    idetect_validation_key_id = Column(Integer)
    idetect_validation_key_value = Column(String)
    status = Column(String, primary_key=True)
    missing = Column(String)
    wrong = Column(String)
    display_color = Column(String)


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


def filter_by_specific_reported_figures(query, figures):
    filters = []
    if None in figures or 'NULL' in figures or 'null' in figures:
        filters.append(FactApi.specific_reported_figure == None)
        figures = [l for l in figures if isinstance(l, int)]
    if figures:
        # figures are typically passed in as all values in a range
        # it's more efficient to just test the endpoints of the range
        least = min(figures)
        greatest = max(figures)
        filters.append(FactApi.specific_reported_figure.between(least, greatest))
    return query.filter(or_(*filters))


def parse_list(array_string):
    '''Turn "{Item1,Item2}" string into list'''
    if array_string is None:
        return None
    return array_string.strip().lstrip('{').rstrip('}').split(',')


def filter_params(data):
    filters = {p: parse_list(data.get(p)) for p in [
        "location_ids",
        "specific_reported_figures",
        "categories",
        "units",
        "iso3s",
        "terms",
        "source_common_names"
    ]}
    filters['fromdate'] = data.get('fromdate')
    filters['todate'] = data.get('todate')
    filters['ts'] = data.get('text_in_content')
    return filters


def add_filters(query,
                fromdate=None, todate=None, location_ids=None,
                categories=None, units=None, source_common_names=None,
                terms=None, iso3s=None, specific_reported_figures=None,
                ts=None):
    '''Add some of the known filters to the query'''
    # if there are multiple facts for a single analysis, we only want one row
    query = query.distinct()
    if fromdate:
        query = query.filter(FactApi.gdelt_day >= fromdate)
    if todate:
        query = query.filter(FactApi.gdelt_day <= todate)
    if location_ids:
        query = filter_by_locations(query, location_ids)
    if categories:
        query = query.filter(FactApi.category.in_(categories))
    if units:
        query = query.filter(FactApi.unit.in_(units))
    if source_common_names:
        query = query.filter(FactApi.source_common_name.in_(source_common_names))
    if terms:
        query = query.filter(FactApi.term.in_(terms))
    if iso3s:
        query = query.filter(FactApi.iso3.in_(iso3s))
    if specific_reported_figures:
        query = filter_by_specific_reported_figures(query, specific_reported_figures)
    if ts:
        query = (
            query
                .join(DocumentContent, DocumentContent.id == FactApi.content_id)
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


def get_wordcloud(session, engine, sample=1000, **filters):
    # select a random sampling of matching facts
    sample = (
        add_filters(session.query(FactApi.content_id), **filters)
            .order_by(func.random())
            .limit(sample)
    ).subquery()
    query = (
        session.query(DocumentContent.content_ts)
            .join(sample, sample.c.content_id == DocumentContent.id)
    )
    literal_query = query.statement.compile(engine, compile_kwargs={"literal_binds": True})
    ts_stat = text('''SELECT * FROM ts_stat($${}$$)
                          ORDER BY nentry DESC, ndoc DESC, word
                          LIMIT 100'''.format(literal_query))
    return [{"word": r.word, "nentry": r.nentry, "ndoc": r.ndoc} for r in session.execute(ts_stat)]


def get_count(session, **filters):
    return add_filters(session.query(FactApi), **filters).count()


def get_urllist(session, limit=32, offset=0, **filters):
    # select the facts that match the filters
    facts = (
        add_filters(session.query(
            FactApi.document_identifier,
            FactApi.fact,
            FactApi.gdelt_day,
            FactApi.iso3,
            FactApi.source_common_name,
            FactApi.specific_reported_figure,
            FactApi.term,
            FactApi.unit,
            FactApi.vague_reported_figure,
            FactApi.category,
            FactApi.gkg_id,
        ), **filters)
            .order_by(FactApi.gdelt_day, FactApi.gkg_id)
            .limit(limit)
            .offset(offset)
            .subquery()
    )

    # find all of the locations for the matching facts. this can't be done in the
    # query above because there may be some location filters that interfere
    # note: location names and ids are not always in the same order
    facts_locations = (
        session.query(facts,
                      func.sort(func.array_agg(Location.id)).label('location_ids'),
                      func.array_agg(Location.location_name).label('location_names'))
            .join(fact_location, facts.c.fact == fact_location.c.fact)
            .join(Location, fact_location.c.location == Location.id)
            .group_by(facts)
            .subquery()
    )

    query = (
        session.query(
            facts_locations.c.document_identifier.label('document_identifier'),
            facts_locations.c.fact.label('fact_id'),
            facts_locations.c.gdelt_day.label('gdelt_day'),
            facts_locations.c.iso3.label('iso3'),
            facts_locations.c.source_common_name.label('source_common_name'),
            facts_locations.c.specific_reported_figure.label('specific_reported_figure'),
            facts_locations.c.term.label('term'),
            facts_locations.c.unit.label('unit'),
            facts_locations.c.vague_reported_figure.label('vague_reported_figure'),
            facts_locations.c.category.label('category'),
            facts_locations.c.gkg_id.label('gkg_id'),
            facts_locations.c.location_ids.label('location_ids'),
            facts_locations.c.location_names.label('location_names'),
            Analysis.authors.label('authors'),
            Analysis.title.label('title'),
            Validation.assigned_to.label('assigned_to'),
            Validation.missing.label('missing'),
            Validation.status.label('status'),
            Validation.wrong.label('wrong'),
            ValidationValues.display_color.label('display_color'),
        )
            .join(Analysis, facts_locations.c.gkg_id == Analysis.gkg_id)
            .outerjoin(Validation, facts_locations.c.fact == Validation.fact_id)
            .outerjoin(ValidationValues, Validation.status == ValidationValues.idetect_validation_key_value)
    )
    return [dict(r.items()) for r in session.execute(query)]


def get_urllist_grouped(session, limit=32, offset=0, **filters):
    # select the things we want to group on: SRF, term, unit
    facts = (
        add_filters(session.query(
            FactApi.fact,
            FactApi.specific_reported_figure,
            FactApi.term,
            FactApi.unit
        ), **filters)
            .subquery()
    )

    # find all of the locations for the matching facts. this can't be done in the
    # query above because there may be some location filters that interfere
    # note: location names and ids are not always in the same order
    facts_locations = (
        session.query(facts,
                      func.sort(func.array_agg(Location.id)).label('location_ids'),
                      func.array_agg(Location.location_name).label('location_names'))
            .join(fact_location, facts.c.fact == fact_location.c.fact)
            .join(Location, fact_location.c.location == Location.id)
            .group_by(facts.c.fact,
                      facts.c.specific_reported_figure,
                      facts.c.term,
                      facts.c.unit)
            .subquery()
    )

    # join in the validation information for each fact
    fact_validation = (
        session.query(FactApi,
                      Validation.assigned_to.label('assigned_to'),
                      Validation.missing.label('missing'),
                      Validation.status.label('status'),
                      Validation.wrong.label('wrong'),
                      ValidationValues.display_color.label('display_color'))
            .distinct(FactApi.fact)
            .outerjoin(Validation, FactApi.fact == Validation.fact_id)
            .outerjoin(ValidationValues, Validation.status == ValidationValues.idetect_validation_key_value)
            .subquery().alias('fact')
    )

    # form each of the groups
    facts_grouped = (
        session.query(
            facts_locations.c.specific_reported_figure.label('specific_reported_figure'),
            facts_locations.c.term.label('term'),
            facts_locations.c.unit.label('unit'),
            facts_locations.c.location_ids.label('location_ids'),
            func.min(facts_locations.c.location_names).label('location_names'),
            func.json_agg(literal_column('fact.*')).label('entry'),
            func.count(1).label('nfacts')
        )
            .join(fact_validation, facts_locations.c.fact == fact_validation.c.fact)
            .group_by(facts_locations.c.specific_reported_figure,
                      facts_locations.c.term,
                      facts_locations.c.unit,
                      facts_locations.c.location_ids)

            .order_by(facts_locations.c.specific_reported_figure)
            .limit(limit)
            .offset(offset)
    )
    return [dict(r.items()) for r in session.execute(facts_grouped)]


def get_map_week(session):
    query = text("SELECT * FROM idetect_map_week_mview")
    return [{'entries': session.execute(query).first()[0]}]
