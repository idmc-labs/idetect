import os
import sys
import logging
import watchtower

from sqlalchemy import create_engine

from idetect.model import db_url, Base, Session
from idetect.worker import Worker, Initiator

USE_CLOUDWATCH_LOGS = os.environ.get('USE_CLOUDWATCH_LOGS', 'False').lower() == 'true'
CLOUDWATCH_LOG_GROUP = os.environ.get('CLOUDWATCH_LOG_GROUP', 'idetect')


def get_logger(name):
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    if USE_CLOUDWATCH_LOGS:
        handler = watchtower.CloudWatchLogHandler(log_group=CLOUDWATCH_LOG_GROUP)
        handler.setFormatter(logging.Formatter("%(levelname)s - %(message)s"))
    else:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    logging.root.addHandler(handler)
    return logger


logger = get_logger(__name__)


class Command():
    def __init__(self, name, args, is_initiator=False, kwargs={}):
        self.name = name
        self.args = args
        self.kwargs = kwargs
        self.is_initiator = is_initiator

        # Setup db engine
        engine = create_engine(db_url())
        Session.configure(bind=engine)
        Base.metadata.create_all(engine)
        self.engine = engine

    def _run(self, is_single_run=False):
        worker = (Worker if not self.is_initiator else Initiator)(*self.args, self.engine, **self.kwargs)
        if is_single_run:
            logger.info(f"Starting worker ({self.name})...")
            worker.work_all()
        else:
            logger.info("Starting worker indefinitely ({self.name})...")
            worker.work_indefinitely()
        logger.info(f"Worker stopped ({self.name}).")

    def run(self, *args, **kwargs):
        try:
            return self._run(*args, **kwargs)
        except Exception:
            logger.error(f'Failed to run command {self.name}', exc_info=True)
