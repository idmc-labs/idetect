import logging
import sys
from datetime import timedelta

from sqlalchemy import create_engine, func

from idetect.model import db_url, Base, Session, Status
from idetect.scraper import scrape
from idetect.worker import Worker


MAX_RETRIEVAL_ATTEMPTS = 3
TIME_BETWEEN_ATTEMPTS = 12


# Filter function for identifying analyses to scrape
def scraping_filter(query):
    # Choose either New analyses OR
    # Analyses where Scraping Failed &
    # less than 3 scraping attempts &
    # last scraping attempt greater than 12 hours ago
    return query.filter((Analysis.status == Status.NEW) |
                        ((Analysis.status == Status.SCRAPING_FAILED) &
                         (Analysis.retrieval_attempts < MAX_RETRIEVAL_ATTEMPTS) &
                         (func.now() > Analysis.retrieval_date + timedelta(hours=TIME_BETWEEN_ATTEMPTS))))


if __name__ == "__main__":
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
    logger.root.addHandler(handler)

    engine = create_engine(db_url())
    Session.configure(bind=engine)
    Base.metadata.create_all(engine)

    worker = Worker(scraping_filter, Status.SCRAPING, Status.SCRAPED, Status.SCRAPING_FAILED,
                    scrape, engine)
    logger.info("Starting worker...")
    worker.work_indefinitely()
    logger.info("Worker stopped.")
