'''Method(s) for extracting facts from relevant content.

How to ensure has access to pre-loaded models?
'''
from flask import Blueprint
from app.interpreter import Interpreter, person_reporting_terms, structure_reporting_terms, person_reporting_units, \
    structure_reporting_units, relevant_article_terms
# from app import nlp

extractor_api = Blueprint('extractor_api', __name__)


@extractor_api.route('/extract', methods=['GET'])
def extract():
    # Query URL Database for relevant content

    # For each piece of content, run fact extraction

    # Save extracted facts in Fact Database
    pass


def extract_facts(content):
    # Get rules-based facts along with sentence numbers
    interpreter = Interpreter(nlp, person_reporting_terms, structure_reporting_terms, person_reporting_units,
                              structure_reporting_units, relevant_article_terms)
    rules_based_reports = interpreter.process_article_new(interpreter)
