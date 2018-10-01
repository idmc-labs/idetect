import time
import datetime
import re


from sqlalchemy import Column, Integer, String, Date, ForeignKey, column, func, or_, text, literal_column, ARRAY, desc, over

from idetect.model import Base, Gkg, DocumentContent, Analysis, Location, Country, Fact, Status
from idetect.values import values

class FactApiLocations(Base):
    __tablename__ = 'idetect_fact_api_locations'

    fact = Column(Integer,
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
    location_ids_num = Column(Integer)

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
        figures = [l for l in figures if l not in [None,'NULL','null']]
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
    filters['location_ids_num'] = data.get('location_ids_num')
    return filters


def add_filters(query,
                fromdate=None, todate=None, location_ids=None,
                categories=None, units=None, source_common_names=None,
                terms=None, iso3s=None, specific_reported_figures=None,
                ts=None,location_ids_num=None):
    '''Add some of the known filters to the query'''  
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
    # by default we exclude specific reported figures unless it is specifically added in specific_reported_figures
    else: query = query.filter(FactApi.specific_reported_figure != None)
    # TODO make sure we do full text search only after all the other filters have been applied
    if ts:
        query = (
            query
                .join(DocumentContent, DocumentContent.id == FactApi.content_id)
                .filter(DocumentContent.content_ts.match(ts, postgresql_regconfig='simple_english'))
        )
    if location_ids_num:
        query = query.filter(FactApi.location_ids_num == location_ids_num)
    return query


def get_filter_counts(session, **filters):
    filter_counts = []
    for filter_column in ('category', 'unit', 'source_common_name', 'term', 'iso3', 'specific_reported_figure'):
        column = FactApi.__table__.c[filter_column]
        query = (add_filters(session.query(func.count(FactApi.fact), column), **filters)
        .distinct()
        ).group_by(column)
        for count, value in query.all():
            filter_counts.append({'count': count, 'value': value, 'filter_type': filter_column})
    return filter_counts


def get_timeline_counts(session, **filters):
    query = (
        add_filters(session.query(func.count(FactApi.fact),
                                  FactApi.gdelt_day,
                                  FactApi.category),
                    **filters)
            .distinct()
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
            .distinct()
            .group_by(FactApi.unit, FactApi.specific_reported_figure)
            .order_by(FactApi.unit, FactApi.specific_reported_figure)
    )
    return [{"count": count, "unit": unit, "specific_reported_figure": specific_reported_figure}
            for count, unit, specific_reported_figure in query.all()]


def get_wordcloud(session, engine, sample=1000, **filters):
    # select a random sampling of matching facts
    sample = (
        add_filters(session.query(FactApi.content_id), **filters)
            .distinct()
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
    return (add_filters(session.query(FactApi.fact), **filters)
    .distinct(FactApi.fact)
    .order_by(FactApi.fact)).count()

def get_group_count(session, **filters):
    ngroups = (add_filters(session.query(FactApi.fact), **filters)
    .distinct(FactApi.specific_reported_figure,FactApi.location_ids_num,FactApi.term,FactApi.unit)).count()
    return ngroups

def get_urllist(session, limit=32, offset=0, **filters):
    # select the facts that match the filters
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
        ), **filters)
            .distinct(FactApi.fact)
            .order_by(FactApi.fact,FactApi.gdelt_day)
            .join(FactApiLocations,FactApi.fact == FactApiLocations.fact)
            .join(Analysis, FactApi.gkg_id == Analysis.gkg_id)
            .join(Fact, FactApi.fact == Fact.id)
            .outerjoin(Validation, FactApi.fact == Validation.fact_id)
            .outerjoin(ValidationValues, Validation.status == ValidationValues.idetect_validation_key_value)
            
    )
    # if we filter by text this is already joined and SQLAlchemy return an error
    if filters['ts'] is None:
        facts=facts.join(DocumentContent, FactApi.content_id == DocumentContent.id)
    # limit and offset must be applied after all the joins
    facts=facts.limit(limit).offset(offset)
    return [dict(r.items()) for r in session.execute(facts)]


def get_urllist_grouped(session, limit=32, offset=0, **filters):
     # select facts according to the filter without selecting content_clean    
    facts = (add_filters(
        session.query(
            # FactApi.fact.label('fact_id'),
            FactApi.specific_reported_figure.label('specific_reported_figure'),
            FactApi.term.label('term'),
            FactApi.unit.label('unit'),
            FactApi.location_ids_num.label('location_ids_num'),
            FactApiLocations.location_names.label('location_names'),
            ), **filters)
            .distinct(FactApi.fact)
            .join(FactApiLocations,FactApi.fact==FactApiLocations.fact)
            .subquery().alias('fact')
    )
    
    fact_groups = (
        session.query(
            facts.c.specific_reported_figure.label('specific_reported_figure'),
            facts.c.term.label('term'),
            facts.c.unit.label('unit'),
            facts.c.location_ids_num.label('location_ids_num'),
            func.min(facts.c.location_names).label('location_names'),
            func.count(1).label('nfacts'),
        )
        .group_by(
        facts.c.specific_reported_figure,
        facts.c.term,
        facts.c.unit,
        facts.c.location_ids_num)
        # getting the most reported figure first
        .order_by(desc(func.count(1)))
        .limit(limit)
        .offset(offset)
    )
    print(fact_groups)
    return [dict(r.items()) for r in session.execute(fact_groups)]

def get_map_week(session):
    query = text("SELECT * FROM idetect_map_week_mview")
    return [{'entries': session.execute(query).first()[0]}]

def work(session, analysis, working_status, success_status, failure_status, function):
    analysis.create_new_version(working_status)
    session.commit()
    start = time.time()
    try:
        analysis.create_new_version(working_status)
        function(analysis)
        delta = time.time() - start
        analysis.error_msg = None
        analysis.processing_time = delta
        analysis.create_new_version(success_status)
        session.commit()
    except Exception as e:
        delta = time.time() - start
        analysis.error_msg = str(e)
        analysis.processing_time = delta
        analysis.create_new_version(failure_status)
        session.commit()
        return e
    return True

def get_scn_from_url(url):
    try:
        return re.search('(?<=www.).*?(?=\/)',url).group(0)
    except:
        try:
            return  re.search('(?<=\/\/).*?(?=\/)',url).group(0)
        except: return None  

def create_new_analysis_from_url(session,url):
    scn=get_scn_from_url(url)
    now=datetime.datetime.now()
    gkg_date=('{:04d}{:02d}{:02d}{:02d}{:02d}{:02d}'.format(now.year,now.month,now.day,now.hour,now.minute,now.second))
    article = Gkg(document_identifier=url,date=gkg_date,source_common_name=scn)
    analysis=Analysis(gkg=article, status=Status.NEW,retrieval_attempts=0)
    session.add(analysis)
    session.commit()
    return analysis

def get_document(session, gkg_id=None):
    # select the facts that match the filters
    document = (
        session.query(
            Gkg.id.label('gkg_id'),
            Gkg.date.label('gkg_date'),
            Gkg.source_common_name.label('source_common_name'),
            Gkg.document_identifier.label('document_identifier'),
            Analysis.title.label('document_title'),
            Analysis.publication_date.label('publication_date'),
            Analysis.category.label('category'),
            DocumentContent.content_clean.label('content_clean')
        )
        .join(Analysis)
        .join(DocumentContent)
        .filter(Analysis.gkg_id == gkg_id)
    )
    return [dict(r.items()) for r in session.execute(document)]
    

def get_facts_for_document(session, gkg_id=None):
    # select the facts that match the filters
    facts = (
        session.query(
            Fact.id.label('fact_id'),
            Fact.excerpt_start.label('excerpt_start'),
            Fact.excerpt_end.label('excerpt_end'),
            Fact.unit.label('unit'),
            Fact.term.label('term'),
            Fact.specific_reported_figure.label('specific_reported_figure'),
            Fact.vague_reported_figure.label('vague_reported_figure'),
            Fact.iso3.label('iso3'),
            Fact.tag_locations.label('tags'),
        func.array_agg(
            func.json_build_object(
                'location_name',Location.location_name,
                'location_type',Location.location_type,
                'iso3',Country.iso3,
                'country_name',Country.preferred_term,
                'latlong',Location.latlong)
            ).label('locations')
        )
        .join(Fact,Analysis.facts)
        .join(Location,Fact.locations)
        .join(Country,Location.country)
        .group_by(Fact)
        .filter(Analysis.gkg_id == gkg_id)
    )
    return [dict(r.items()) for r in session.execute(facts)]