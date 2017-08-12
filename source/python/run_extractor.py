import logging
import sys
from sqlalchemy import create_engine

from idetect.model import db_url, Base, Session, Status
from idetect.fact_extractor import extract_reports
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

    worker = Worker(Status.CLASSIFIED, Status.EXTRACTING, Status.EXTRACTED, Status.EXTRACTING_FAILED,
                    extract_reports, engine)
    logger.info("Starting worker...")
    worker.work_indefinitely()
    logger.info("Worker stopped.")