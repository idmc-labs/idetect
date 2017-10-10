"""
One-time setup script to download classifier models and pre-populate database with data neccessary for fact extraction.
"""

from sqlalchemy import create_engine
from idetect.model import db_url, Base, Session, Country, FactKeyword
from idetect.load_data import load_countries, load_terms
import re
import string
import numpy as np
import pandas as pd
from idetect.nlp_models.category import * 
from idetect.nlp_models.relevance import * 
from idetect.nlp_models.base_model import CustomSklLsiModel

if __name__ == "__main__":

    # Create the Database
    engine = create_engine(db_url())
    Session.configure(bind=engine)
    Base.metadata.create_all(engine)

    session = Session()
    # Load the Countries data if necessary
    countries = session.query(Country).all()
    if len(countries) == 0:
        load_countries(session)

    # Load the Keywords if neccessary
    keywords = session.query(FactKeyword).all()
    if len(keywords) == 0:
        load_terms(session)

    session.close()

    # Load the Classifier models once to ensure they are downloaded
    # CategoryModel()
    # RelevanceModel()
