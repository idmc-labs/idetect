import logging
import sys

from sqlalchemy import create_engine

from idetect.fact_extractor import extract_facts
from idetect.load_data import load_countries, load_terms
from idetect.model import db_url, Base, Session, Status, Analysis, Country, FactKeyword
from idetect.worker import Worker

if __name__ == "__main__":
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
    logger.root.addHandler(handler)

    engine = create_engine(db_url())
    Session.configure(bind=engine)
    Base.metadata.create_all(engine)

    # Check necessary data exists prior to fact extraction
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

    worker = Worker(lambda query: query.filter(Analysis.status == Status.CLASSIFIED),
                    Status.EXTRACTING, Status.EXTRACTED, Status.EXTRACTING_FAILED,
                    extract_facts, engine)
    logger.info("Starting worker...")
    worker.work_indefinitely()
    logger.info("Worker stopped.")
