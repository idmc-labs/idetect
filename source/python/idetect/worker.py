import logging
import os
import signal
import time

from idetect.model import Article, UnexpectedArticleStatusException, Session

logger = logging.getLogger(__name__)


class Worker:
    def __init__(self, status, working_status, success_status, failure_status, function, engine):
        """
        Create a Worker that looks for Articles with a given status. When it finds one, it marks it with 
        working_status and runs a function. If the function returns without an exception, it advances the Article to 
        success_status. If the function raises an exception, it advances the Article to failure_status. 
        """
        self.status = status
        self.working_status = working_status
        self.success_status = success_status
        self.failure_status = failure_status
        self.function = function
        self.engine = engine
        self.session = None
        self.terminated = False
        signal.signal(signal.SIGINT, self.terminate)
        signal.signal(signal.SIGTERM, self.terminate)

    def terminate(self, signum, frame):
        print(f"Worker {os.getpid()} terminated")
        self.terminated = True

    def work(self):
        """
        Look for articles in the given session and run function on them
        if any are found, managing status appropriately. Return True iff some Articles were processed (successfully or not)
        """
        try:
            if self.session is None:
                self.engine.dispose()  # each Worker must have its own session, made in-Process
                Session.configure(bind=self.engine)
                self.session = Session()
            claimed_one = False
            article = None
            while not claimed_one:
                try:
                    article = self.session.query(Article).filter(Article.status == self.status) \
                        .order_by(Article.updated).first()  # choose the least-recently-updated article with this status
                    if article is None:
                        return False  # no work to be done
                    article.update_status(self.working_status)
                    self.session.commit()
                    logger.info(f"Worker claimed Article {article.id} in status {self.status}")
                    claimed_one = True
                except UnexpectedArticleStatusException:
                    pass  # another worker claimed this article before we could, try again
            try:
                self.function(article)
                logger.info(f"Worker processed Article {article.id} {self.status} -> {self.success_status}")
                article.update_status(self.success_status)
                self.session.commit()
            except Exception as e:
                logger.warn(f"Worker failed to process Article {article.id} {self.status} -> {self.failure_status}",
                            exc_info=e)
                article.update_status(self.failure_status)
                self.session.commit()
            return True
        finally:
            if self.session is not None:
                self.session.rollback()

    def work_all(self):
        """Work repeatedly until there is no work to do. Return a count of the number of units of work done"""
        count = 0
        while self.work() and not self.terminated:
            count += 1
        return count

    def work_indefinitely(self, max_sleep=60):
        """While there is work to do, do it. If there's no work to do, take increasingly long naps until there is."""
        sleep = 1
        while not self.terminated:
            if self.work_all() > 0:
                sleep = 1
            else:
                time.sleep(sleep)
                sleep = min(max_sleep, sleep * 2)
