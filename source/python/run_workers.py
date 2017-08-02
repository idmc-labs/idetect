import logging
import sys
from math import ceil
from multiprocessing import cpu_count, active_children
from time import sleep

from sqlalchemy import create_engine

from idetect.model import db_url, Base, Session, Status
from idetect.worker import Worker

from idetect.scraper import scrape

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.root.addHandler(logging.StreamHandler(sys.stderr))

engine = create_engine(db_url())
Session.configure(bind=engine)
Base.metadata.create_all(engine)


def do_nothing(article):
    sleep(60)


if __name__ == "__main__":
    # Start workers
    n_workers = ceil(cpu_count() / 2)
    Worker.start_processes(n_workers, Status.NEW, Status.SCRAPING, Status.SCRAPED, Status.SCRAPING_FAILED,
                           scrape, engine)
    # replace do_nothing with the actual work functions...
    Worker.start_processes(n_workers, Status.SCRAPED, Status.PROCESSING, Status.PROCESSED, Status.PROCESSING_FAILED,
                           do_nothing, engine)

    # run until all children are finished
    for child in active_children():
        child.join()
