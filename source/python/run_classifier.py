import logging
import sys

from sqlalchemy import create_engine

from idetect.classifier import classify
from idetect.nlp_models.category.category import CategoryModel
from idetect.nlp_models.relevance.relevance import RelevanceModel
from idetect.model import db_url, Base, Session, Status
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

    c_m = CategoryModel()
    r_m = RelevanceModel()

    worker = Worker(Status.SCRAPED, Status.CLASSIFYING, Status.CLASSIFIED, Status.CLASSIFYING_FAILED,
                    lambda article: classify(article, c_m, r_m, engine))
    logger.info("Starting worker...")
    worker.work_indefinitely()
    logger.info("Worker stopped.")
