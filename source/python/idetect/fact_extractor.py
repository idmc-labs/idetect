'''Method(s) for extracting facts from relevant content.

How to ensure has access to pre-loaded models?
'''
import spacy
from interpreter import Interpreter, person_reporting_terms, structure_reporting_terms, person_reporting_units, \
    structure_reporting_units, relevant_article_terms

nlp = spacy.load("en")
print("Loaded Spacy English Language NLP Models.")


def extract_facts(content):
    # Get rules-based facts along with sentence numbers
    interpreter = Interpreter(nlp, person_reporting_terms, structure_reporting_terms, person_reporting_units,
                              structure_reporting_units, relevant_article_terms)
    reports = interpreter.process_article_new(content)
    return reports
