'''Method(s) for extracting facts from relevant content.

How to ensure has access to pre-loaded models?
'''
import json

import spacy
from sqlalchemy.orm import object_session

from idetect.geotagger import get_geo_info
from idetect.interpreter import Interpreter
from idetect.model import Fact, Location, Country

nlp = spacy.load("en_default")
print("Loaded Spacy English Language NLP Models.")


def extract_facts(article):
    '''Extract facts (facts) for given article
    :params article: instance of Article
    :return: None
    '''
    session = object_session(article)
    interpreter = Interpreter(session, nlp)
    content = article.content.content
    facts = interpreter.process_article_new(content)
    if len(facts) > 0:
        save_facts(article, facts, session)


def save_facts(article, facts, session):
    '''Loop through extracted facts and save them to database
    :params article: instance of Article
    :params facts: list of extracted facts
    :params session: session object corresponding to the article
    :return: None
    '''
    for r in facts:
        fact = Fact(article_id=article.id, reporting_unit=r.reporting_unit, reporting_term=r.reporting_term,
                    sentence_start=r.sentence_start, sentence_end=r.sentence_end,
                    specific_displacement_figure=r.quantity[0],
                    vague_displacement_figure=r.quantity[1],
                    tag_locations=json.dumps(r.tag_spans))
        session.add(fact)
        session.commit()

        # Loop over each extracted location and save to Database
        for location in r.locations:
            process_location(fact, location, session)


def process_location(fact, location, session):
    '''Get geo info for a given location and add the location to database
    :params fact: instance of Fact
    :params location: location name, a String
    :params session: session object corresponding to location
    :return: None
    '''
    loc = session.query(Location).filter_by(
        description=location).one_or_none()
    if loc:
        fact.locations.append(loc)
    else:
        loc_info = get_geo_info(location)
        if loc_info['flag'] != 'no-results':
            country = session.query(Country).filter_by(
                code=loc_info['country_code']).one_or_none()
            location = Location(description=loc_info['place_name'], location_type=loc_info['type'],
                                country_code=country.code,
                                country=country, latlong=loc_info['coordinates'])
            session.add(location)
            session.commit()
            fact.locations.append(location)
