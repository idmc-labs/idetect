'''Method(s) for extracting facts from relevant content.

How to ensure has access to pre-loaded models?
'''
from idetect.interpreter import Interpreter, person_reporting_terms, structure_reporting_terms, person_reporting_units, \
    structure_reporting_units, relevant_article_terms
import spacy
from idetect.model import Report, Location, Session, Base
from idetect.geotagger import get_geo_info
import json

nlp = spacy.load("en")
print("Loaded Spacy English Language NLP Models.")


def extract_reports(article):
    # Get rules-based facts along with sentence numbers
    interpreter = Interpreter(nlp, person_reporting_terms, structure_reporting_terms, person_reporting_units,
                              structure_reporting_units, relevant_article_terms)
    content = article.content[0].content
    reports = interpreter.process_article_new(content)
    if len(reports) > 0:
        save_reports(reports)


def save_reports(article, reports):
    for r in reports:
        report = Report(article_id=article.id, reporting_unit=r.reporting_unit, subject_term=r.reporting_term,
                        sentence_start=r.sentence_start, sentence_end=r.sentence_end,
                        specific_displacement_figure=r.quantity[
                            0], vague_displacement_figure=r.quantity[1],
                        tag_locations=json.dumps(r.tag_spans))
        session.add(report)
        session.commit()

        for location in r.locations:
            process_location(report, location)


def process_location(report, location):
    loc = session.query(Location).filter_by(
        description=location).one_or_none()
    if loc:
        report.locations.append(loc)
    else:
        loc_info = get_geo_info(location)
        if loc_info['flag'] != 'no-results':
            country = session.query(Country).filter_by(
                code=loc_info['country_code']).one_or_none()
            location = Location(description=loc_info['place_name'], location_type=loc_info['type'], country_code=country.code,
                                country=country, latlong=loc_info['coordinates'])
            session.add(location)
            session.commit()
            report.locations.append(location)
