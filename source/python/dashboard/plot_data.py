import inspect
import pandas as pd
from sqlalchemy import create_engine

from idetect.model import db_url,  Status, Analysis


def db_connect():
    engine = create_engine(db_url())
    return engine

def fetch_statuses(session):
    query = session.query(Analysis).with_entities(Analysis.status)
    df = pd.read_sql(query.statement, query.session.bind)
    return df

def fetch_model_categories(model):
    attributes = inspect.getmembers(model, lambda a:not(inspect.isroutine(a)))
    attrs = [a[1] for a in attributes if not(a[0].startswith('__') and 
                                             a[0].endswith('__'))]
    return attrs
