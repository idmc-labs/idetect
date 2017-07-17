import logging
import sys
from math import ceil
from multiprocessing import cpu_count
from time import sleep

from sqlalchemy import create_engine

from idetect.api import app
from idetect.model import db_url, Base, Session, Status
from idetect.worker import Worker

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.root.addHandler(logging.StreamHandler(sys.stderr))

engine = create_engine(db_url())
Session.configure(bind=engine)
Base.metadata.create_all(engine)

# with open('data/cities_to_countries.json', "r") as f:
cities_to_countries = {}  # json.load(f)
print("Loaded cities_to_countries dictionary.")


## Load Spacy English language model
## Uncomment this once using NLP
# nlp = spacy.load('en')
# print("Loaded Spacy english language models.")

## TODO: Load pre-trained classifiers

def do_nothing(article):
    sleep(60)


if __name__ == "__main__":
    # Start workers
    n_workers = ceil(cpu_count() / 2)
    # replace do_nothing with the actual work functions...
    Worker.start_processes(n_workers, Status.NEW, Status.FETCHING, Status.FETCHED, Status.FETCHING_FAILED,
                           do_nothing, engine)
    Worker.start_processes(n_workers, Status.FETCHED, Status.PROCESSING, Status.PROCESSED, Status.PROCESSING_FAILED,
                           do_nothing, engine)

    # Start flask app
    app.run(host='0.0.0.0', port=5001, debug=True, threaded=True)
