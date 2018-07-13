'''Method(s) for extracting facts from relevant content.

How to ensure has access to pre-loaded models?
'''
import json

import spacy
from itertools import groupby
from sqlalchemy.orm import object_session
from sqlalchemy.exc import IntegrityError

from idetect.interpreter import Interpreter
from idetect.model import Fact, Location, Country

nlp = spacy.load("en_default")
print("Loaded Spacy English Language NLP Models.")


def extract_facts(analysis):
    '''Extract facts (facts) for given instance of Analysis
    :params article: instance of Analysis
    :return: None
    '''
    session = object_session(analysis)
    interpreter = Interpreter(session, nlp)
    content = analysis.content.content_clean # Use the cleaned content field
    facts = interpreter.process_article_new(content)
    if len(facts) > 0:
        save_facts(analysis, facts, session)


def save_facts(analysis, facts, session):
    '''Loop through extracted facts and save them to database
    :params article: instance of Article
    :params facts: list of extracted facts
    :params session: session object corresponding to the article
    :return: None
    '''
    for f in facts:
        fact = Fact(unit=f.reporting_unit, term=f.reporting_term,
                    excerpt_start=f.sentence_start, excerpt_end=f.sentence_end,
                    specific_reported_figure=f.quantity[0],
                    vague_reported_figure=f.quantity[1],
                    tag_locations=json.dumps(f.tag_spans))
        session.add(fact)
        analysis.facts.append(fact)

        # Process the locations and add new ones to the locations table
        locations = { process_location(location, session) for location in f.locations }
        fact.locations.extend(locations)
        session.commit()


def process_location(location_name, session):
    '''Add location_name to database
    :params location: location name, a String
    :params session: session object corresponding to location
    :return: Locations
    '''
    #TODO here we should check that the iso is in the list
    location = session.query(Location).filter_by(
        location_name=location_name).one_or_none()
    if location:
        return location
    else:
        ## try and create a new location with the given location_name
        try:
            location = Location(location_name=location_name)
            session.add(location)
            session.commit()
            return location
        except IntegrityError as e:
            location = session.query(Location).filter_by(
                location_name=location_name).one_or_none()
            return location
