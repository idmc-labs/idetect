from sqlalchemy import Column, Integer, String, Date, ForeignKey, column, func, or_, text, literal_column, ARRAY, desc, over

from idetect.model import Base, DocumentContent, Analysis, Location, Fact, fact_location
from idetect.values import values

class FactApiLocations(Base):
    __tablename__ = 'idetect_fact_api_locations'

    fact = Column(Integer,
                  ForeignKey('idetect_fact_locations.fact'),
                  primary_key=True)
    location_ids = Column(ARRAY(Integer))
    location_names = Column(ARRAY(String))
    location_ids_num = Column(Integer)
    

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
    location_ids_num = Column(Integer,ForeignKey('idetect_fact_api_locations.location_ids_num'))

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
                ts=None,distinct_on_fact=False):
    '''Add some of the known filters to the query'''
    # if there are multiple facts for a single analysis, we only want one row
    if(distinct_on_fact):
        query = query.distinct(FactApi.fact)
        query = query.order_by(FactApi.fact)
    else:
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
    # TODO make sure we do full text search only after all the other filters have been applied
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
    return add_filters(session.query(FactApi.fact), **filters,distinct_on_fact=True).count()


def get_urllist(session, limit=32, offset=0, **filters):
    # select the facts that match the filters
    # TODO add one step to verify how many rows are selected,
    # if the number is larger than a threshold (let's say 50000)
    # we process only 50000 rows of idetect_fact_api using TABLESAMPLE
    facts = (add_filters(
        session.query(
            FactApi.document_identifier.label('document_identifier'),
            FactApi.fact.label('fact_id'),
            FactApi.gdelt_day.label('gdelt_day'),
            FactApi.iso3.label('iso3'),
            FactApi.source_common_name.label('source_common_name'),
            FactApi.specific_reported_figure.label('specific_reported_figure'),
            FactApi.term.label('term'),
            FactApi.unit.label('unit'),
            FactApi.vague_reported_figure.label('vague_reported_figure'),
            FactApi.category.label('category'),
            FactApi.gkg_id.label('gkg_id'),
            FactApiLocations.location_ids.label('location_ids'),
            FactApiLocations.location_names.label('location_names'),
            Analysis.authors.label('authors'),
            Analysis.title.label('title'),
            DocumentContent.content_clean.label('content_clean'),
            Fact.tag_locations.label('tags'),
            Fact.excerpt_start.label('excerpt_start'),
            Fact.excerpt_end.label('excerpt_end'),
            Validation.assigned_to.label('assigned_to'),
            Validation.missing.label('missing'),
            Validation.status.label('status'),
            Validation.wrong.label('wrong'),
            ValidationValues.display_color.label('display_color'),
        ), **filters,distinct_on_fact=True)
            .outerjoin(FactApiLocations,FactApi.fact==FactApiLocations.fact)
            .outerjoin(Analysis, FactApi.gkg_id == Analysis.gkg_id)
            .outerjoin(Fact, FactApi.fact == Fact.id)
            .outerjoin(DocumentContent, FactApi.content_id == DocumentContent.id)
            .outerjoin(Validation, FactApi.fact == Validation.fact_id)
            .outerjoin(ValidationValues, Validation.status == ValidationValues.idetect_validation_key_value)
            .order_by(FactApi.gdelt_day)
            .limit(limit)
            .offset(offset)
    )
    # print(facts)
    return [dict(r.items()) for r in session.execute(facts)]


def get_urllist_grouped(session, limit=32, offset=0, **filters):
    # select facts according to the filter without selecting content_clean    
    facts = (add_filters(
        session.query(
            FactApi.document_identifier.label('document_identifier'),
            FactApi.fact.label('fact_id'),
            FactApi.gdelt_day.label('gdelt_day'),
            FactApi.iso3.label('iso3'),
            FactApi.source_common_name.label('source_common_name'),
            FactApi.specific_reported_figure.label('specific_reported_figure'),
            FactApi.term.label('term'),
            FactApi.unit.label('unit'),
            FactApi.vague_reported_figure.label('vague_reported_figure'),
            FactApi.category.label('category'),
            FactApi.gkg_id.label('gkg_id'),
            FactApi.content_id.label('content_id'),
            FactApiLocations.location_ids_num.label('location_ids_num'),
            FactApiLocations.location_ids.label('location_ids'),
            FactApiLocations.location_names.label('location_names'),
            Analysis.authors.label('authors'),
            Analysis.title.label('title'),
            Fact.tag_locations.label('tags'),
            Fact.excerpt_start.label('excerpt_start'),
            Fact.excerpt_end.label('excerpt_end'),
            Validation.assigned_to.label('assigned_to'),
            Validation.missing.label('missing'),
            Validation.status.label('status'),
            Validation.wrong.label('wrong'),
            ValidationValues.display_color.label('display_color'),
            over(func.row_number(),
            order_by=(FactApi.gdelt_day),
            partition_by=(FactApi.specific_reported_figure,FactApi.unit,FactApi.term,FactApi.location_ids_num))
            .label('row_number')
        ), **filters,distinct_on_fact=True)
            .outerjoin(FactApiLocations,FactApi.fact==FactApiLocations.fact)
            .outerjoin(Analysis, FactApi.gkg_id == Analysis.gkg_id)
            .outerjoin(Fact, FactApi.fact == Fact.id)
            .outerjoin(Validation, FactApi.fact == Validation.fact_id)
            .outerjoin(ValidationValues, Validation.status == ValidationValues.idetect_validation_key_value)
            .order_by(FactApi.gdelt_day)
            .subquery().alias('fact')
    )
    
    json_labels = ["'{}'".format(c.name) for c in facts.c]
    json_fields = ['fact.{}'.format(c.name) for c in facts.c]
    json_labels.append("'content_clean'")
    json_fields.append('{}.{}'.format(DocumentContent.__tablename__, DocumentContent.content_clean.name))
    json_zip = zip(json_labels, json_fields)
    json_build = ", ".join(["{}, {}".format(l, f) for l, f in json_zip])

    facts_grouped = (
        session.query(
            facts.c.specific_reported_figure.label('specific_reported_figure'),
            facts.c.term.label('term'),
            facts.c.unit.label('unit'),
            func.min(facts.c.location_names).label('location_names'),
            # TODO instert window function to get the true total number of facts
            func.max(facts.c.row_number).label('nfacts'),
            func.json_agg(func.json_build_object(literal_column(json_build))).label('entry'),
        )
        .group_by(
        facts.c.specific_reported_figure,
        facts.c.term,
        facts.c.unit,
        facts.c.location_ids_num)
        .outerjoin(DocumentContent, facts.c.content_id == DocumentContent.id)
        # getting the most reported figure first
        .order_by(desc(func.count(1)))
        # only report the first 50 rows to reduce data size
        #TODO this is probably not the best place to put this filter
        .filter(facts.c.row_number<=50)
        .limit(limit)
        .offset(offset)
    )
    return [dict(r.items()) for r in session.execute(facts_grouped)]

def get_map_week(session):
    query = text("SELECT * FROM idetect_map_week_mview")
    return [{'entries': session.execute(query).first()[0]}]
