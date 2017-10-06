import logging
import sys

from sqlalchemy import create_engine

from idetect.classifier import classify
from idetect.nlp_models.category import CategoryModel, Tokenizer, TfidfTransformer, LsiTransformer, Stemmer
from idetect.nlp_models.relevance import RelevanceModel, PhraseProcessor, POSProcessor, CleaningProcessor
from idetect.nlp_models.base_model import CustomSklLsiModel
from idetect.model import db_url, Base, Session, Status, Analysis
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

    worker = Worker(lambda query: query.filter(Analysis.status == Status.SCRAPED), Status.CLASSIFYING,
                    Status.CLASSIFIED, Status.CLASSIFYING_FAILED,
                    lambda article: classify(article, c_m, r_m), engine)
    logger.info("Starting worker...")
    worker.work_indefinitely()
    logger.info("Worker stopped.")
