from idetect.model import Article, UnexpectedArticleStatusException
import logging

logger = logging.getLogger(__name__)

class Worker:

    def __init__(self, status, working_status, success_status, failure_status, function):
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

    def work(self, session):
        """
        Look for articles in the given session and run function on them
        if any are found, managing status appropriately. Return True iff some Articles were processed (successfully or not)
        """
        claimed_one = False
        article = None
        while not claimed_one:
            try:
                article = session.query(Article).filter(Article.status==self.status)\
                    .order_by(Article.updated).first() # choose the least-recently-updated article with this status
                if article is None:
                    return False  # no work to be done
                article.update_status(self.working_status)
                session.commit()
                logger.info(f"Worker claimed Article {article.id} in status {self.status}")
                claimed_one = True
            except UnexpectedArticleStatusException:
                pass  # another worker claimed this article before we could, try again
        try:
            self.function(article)
            logger.info(f"Worker processed Article {article.id} {self.status} -> {self.success_status}")
            article.update_status(self.success_status)
            session.commit()
        except Exception as e:
            logger.warn(f"Worker failed to process Article {article.id} {self.status} -> {self.failure_status}",
                        exc_info=e)
            article.update_status(self.failure_status)
            session.commit()
        return True

    def work_all(self, session):
        """Work repeatedly until there is no work to do. Return a count of the number of units of work done"""
        count = 0
        while self.work(session):
            count += 1
        return count