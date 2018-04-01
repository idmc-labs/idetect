import logging
from hashlib import sha1

from sqlalchemy import Column, Integer, String, Date,  ForeignKey, text
from sqlalchemy import insert

from idetect.model import Base, Analysis, Gkg, Fact, Location, analysis_fact, fact_location

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


# This class defines a TEMP table that provides hooks for filtering
class ApiFiltered(Base):
    __tablename__ = 'temp_api_filtered'
    __table_args__ = {'prefixes': ['TEMPORARY']}

    gkg_id = Column(Integer,
                    ForeignKey('gkg.id'),
                    primary_key=True)
    fact_id = Column(Integer,
                     ForeignKey('idetect_facts.id'),
                     primary_key=True)
    location_id = Column(Integer,
                         ForeignKey('idetect_locations.id'),
                         primary_key=True)

    category = Column(String)
    source_common_name = Column(String)
    unit = Column(String)
    term = Column(String)
    iso3 = Column(String)
    specific_reported_figure = Column(Integer)

    content_id = Column(Integer, ForeignKey('idetect_document_contents.id'))

def get_class_by_table_name(table_name):
  for c in Base._decl_class_registry.values():
    if hasattr(c, '__tablename__') and c.__tablename__ == table_name:
      return c

def create_day_range_location_table(engine, session, from_date, to_date, locations=None):
    table_id = ','.join([str(x) for x in [from_date, to_date] + sorted(set(locations))])
    table_hash = sha1(table_id.encode('ascii')).hexdigest()
    table_name = 'idetect_cache_' + table_hash

    table = get_class_by_table_name(table_name)
    if not table:
        table = type(table_name, (Base,),
                 {
                     '__tablename__': table_name,
                     'gkg_id': Column(Integer,
                                      ForeignKey('gkg.id'),
                                      primary_key=True),
                     'fact_id': Column(Integer,
                                       ForeignKey('idetect_facts.id'),
                                       primary_key=True),
                     'location_id': Column(Integer,
                                           ForeignKey('idetect_locations.id'),
                                           primary_key=True),

                     'category': Column(String),
                     'source_common_name': Column(String),
                     'unit': Column(String),
                     'term': Column(String),
                     'iso3': Column(String),
                     'specific_reported_figure': Column(Integer),

                     'content_id': Column(Integer, ForeignKey('idetect_document_contents.id'))
                 })

    # create the table if it doesn't exist
    if not engine.dialect.has_table(engine, table_name):
        table.__table__.create(engine)

    # populate its rows if it's empty
    if session.query(table).count() == 0:
        select = (session.query(
            Fact.id,
            Gkg.id,
            Location.id,
            Analysis.category,
            'gkg.source_common_name',
            Fact.unit,
            Fact.term,
            Fact.iso3,
            Fact.specific_reported_figure,
            Analysis.content_id)
                  .join(analysis_fact)
                  .join(Analysis)
                  .join(Gkg)
                  .join(fact_location)
                  .join(Location)
                  .filter(Gkg.date.between(from_date, to_date))
                  )
        # locations is optional
        if locations:
            select = select.filter(Location.id.in_(locations))

        # force this query to use indexes
        session.execute(text("SET LOCAL enable_seqscan=FALSE;"))
        # populate the table with the query
        session.execute(insert(table).from_select(
            (
                table.fact_id,
                table.gkg_id,
                table.location_id,
                table.category,
                table.source_common_name,
                table.unit,
                table.term,
                table.iso3,
                table.specific_reported_figure,
                table.content_id
            ),
            select))
        session.execute(text("SET LOCAL enable_seqscan=TRUE;"))
    return table_name


# This function populates the TEMP table
def create_temp_filters_table(
        session, from_date, to_date,
        # filters below
        locations=None,
        category=None,
        source_common_name=None,
        unit=None,
        term=None,
        iso3=None,
        specific_reported_figure=None):
    # Create the temporary table. SQLAlchemy doesn't have a nice way to do this
    session.execute(text("""
    DROP TABLE IF EXISTS temp_api_filtered;
    CREATE TEMPORARY TABLE temp_api_filtered (
        gkg_id INTEGER NOT NULL, 
        fact_id INTEGER NOT NULL, 
        location_id INTEGER NOT NULL, 
        category VARCHAR, 
        source_common_name VARCHAR, 
        unit VARCHAR, 
        term VARCHAR, 
        iso3 VARCHAR, 
        specific_reported_figure INTEGER, 
        content_id INTEGER, 
        PRIMARY KEY (gkg_id, fact_id, location_id)
    ) ON COMMIT DROP;
"""))

    # Query to populate the temp table
    select = (session.query(
        Fact.id,
        Gkg.id,
        Location.id,
        Analysis.category,
        'gkg.source_common_name',
        Fact.unit,
        Fact.term,
        Fact.iso3,
        Fact.specific_reported_figure,
        Analysis.content_id)
              .join(analysis_fact)
              .join(Analysis)
              .join(Gkg)
              .join(fact_location)
              .join(Location)
              .filter(Gkg.date.between(from_date, to_date))
              )

    # add filters
    if locations:
        select = select.filter(Location.id.in_(locations))
    if category:
        select = select.filter(Analysis.category == category)
    if source_common_name:
        select = select.filter('gkg.source_common_name' == source_common_name)
    if unit:
        select = select.filter(Fact.unit == unit)
    if term:
        select = select.filter(Fact.term == term)
    if iso3:
        select = select.filter(Fact.iso3 == iso3)
    if specific_reported_figure:
        select = select.filter(Fact.specific_reported_figure == specific_reported_figure)

    # force this query to use indexes
    session.execute(text("SET LOCAL enable_seqscan=FALSE;"))
    # populate the table with the query
    session.execute(insert(ApiFiltered).from_select(
        (
            ApiFiltered.fact_id,
            ApiFiltered.gkg_id,
            ApiFiltered.location_id,
            ApiFiltered.category,
            ApiFiltered.source_common_name,
            ApiFiltered.unit,
            ApiFiltered.term,
            ApiFiltered.iso3,
            ApiFiltered.specific_reported_figure,
            ApiFiltered.content_id
        ),
        select))
    session.execute(text("SET LOCAL enable_seqscan=TRUE;"))


def int_or_None(str):
    if str.lower() in ('none', 'null'):
        return None
    return int(str)


def filter_params(form):
    locations = form.get('location_ids')
    if locations:
        locations = [int_or_None(n) for n in locations.replace(' ', '').split(',')]
    return {
        'locations': locations,
        'category': form.get('category'),
        'source_common_name': form.get('source_common_name'),
        'unit': form.get('unit'),
        'term': form.get('term'),
        'iso3': form.get('iso3'),
        'specific_reported_figure': form.get('specific_reported_figure'),
    }
