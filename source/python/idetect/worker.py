import errno
import logging
import os
import random
import signal
import time
from multiprocessing import Process

from idetect.model import Analysis, Session, Gkg, Status

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class Worker:
    def __init__(self, filter_function, working_status, success_status, failure_status, function, engine,
                 max_sleep=60, timeout_seconds=300):
        """
        Create a Worker that looks for Analyses with a given status. When it finds one, it marks it with
        working_status and runs a function. If the function returns without an exception, it advances the Analysis to
        success_status. If the function raises an exception, it advances the Analysis to failure_status.
        """
        self.filter_function = filter_function
        self.working_status = working_status
        self.success_status = success_status
        self.failure_status = failure_status
        self.function = function
        self.engine = engine
        self.terminated = False
        self.max_sleep = max_sleep
        self.timeout_seconds = timeout_seconds
        signal.signal(signal.SIGINT, self.terminate)
        signal.signal(signal.SIGTERM, self.terminate)
        signal.signal(signal.SIGALRM, self.timeout)

    def terminate(self, signum, frame):
        logger.warning("Worker {} terminated".format(os.getpid()))
        self.terminated = True

    def timeout(self, signum, frame):
        logger.warning("Worker {} timed out".format(os.getpid()))
        raise TimeoutError(os.strerror(errno.ETIME))

    def work(self):
        """
        Look for analyses in the given session and run function on them
        if any are found, managing status appropriately. Return True iff some Analyses were processed (successfully or not)
        """
        # start a new session for each job
        session = Session()
        try:
            # Get an analysis
            # ... and lock it for updates
            # ... that meets the conditions specified in the filter function
            # ... sort by updated date
            # ... pick the first (oldest)
            analysis = self.filter_function(session.query(Analysis)) \
                .with_for_update() \
                .order_by(Analysis.updated) \
                .first()
            if analysis is None:
                return False  # no work to be done
            analysis_status = analysis.status
            analysis.create_new_version(self.working_status)
            logger.info("Worker {} claimed Analysis {} in status {}".format(
                os.getpid(), analysis.gkg_id, analysis_status))
        finally:
            # make sure to release a FOR UPDATE lock, if we got one
            session.rollback()

        start = time.time()
        try:
            # set a timeout so if this worker stalls, we recover
            signal.alarm(self.timeout_seconds)
            # actually run the work function on this analysis
            self.function(analysis)
            delta = time.time() - start
            logger.info("Worker {} processed Analysis {} {} -> {} {}s".format(
                os.getpid(), analysis.gkg_id, analysis_status, self.success_status, delta))
            analysis.error_msg = None
            analysis.processing_time = delta
            analysis.create_new_version(self.success_status)
        except Exception as e:
            delta = time.time() - start
            logger.warning("Worker {} failed to process Analysis {} {} -> {}".format(
                os.getpid(), analysis.gkg_id, analysis_status, self.failure_status),
                exc_info=e)
            analysis.error_msg = str(e)
            analysis.processing_time = delta
            analysis.create_new_version(self.failure_status)
            session.commit()
        finally:
            # clear the timeout
            signal.alarm(0)
            if session is not None:
                session.rollback()
                session.close()
        return True

    def work_all(self):
        """Work repeatedly until there is no work to do. Return a count of the number of units of work done"""
        count = 0
        while self.work() and not self.terminated:
            count += 1
        return count

    def work_indefinitely(self):
        """While there is work to do, do it. If there's no work to do, take increasingly long naps until there is."""
        logger.info("Worker {} working indefinitely".format(os.getpid()))
        time.sleep(random.randrange(self.max_sleep))  # stagger start times
        sleep = 1
        while not self.terminated:
            if self.work_all() > 0:
                sleep = 1
            else:
                time.sleep(sleep)
                sleep = min(self.max_sleep, sleep * 2)

    @staticmethod
    def start_processes(num, status, working_status, success_status, failure_status, function, engine, max_sleep=60):
        processes = []
        engine.dispose()  # each Worker must have its own session, made in-Process
        for i in range(num):
            worker = Worker(status, working_status, success_status, failure_status, function, engine, max_sleep)
            process = Process(target=worker.work_indefinitely, daemon=True)
            processes.append(process)
            process.start()
        return processes


class Initiator(Worker):
    def __init__(self, engine, max_sleep=60):
        """
        Create a Worker that looks for Documents that have no Analysis. When if finds one, it creates
        an Analysis with Status.NEW
        """
        self.engine = engine
        self.terminated = False
        self.max_sleep = max_sleep
        signal.signal(signal.SIGINT, self.terminate)
        signal.signal(signal.SIGTERM, self.terminate)

    def work(self):
        """
        Look for Documents in the given session Return for which no Analysis exists and
        creates one with Status.New. Returns True iff some Analyses were created
        """
        # start a new session for each job
        session = Session()
        try:
            # Get a Document
            # ... for which no Analysis exists
            # ... and lock it for updates
            # ... sort by created date
            # ... pick the first (oldest)
            gkgs = session.query(Gkg) \
                .filter(~session.query(Analysis).filter(Gkg.id == Analysis.gkg_id).exists()) \
                .with_for_update() \
                .order_by(Gkg.date) \
                .limit(1000).all()
            if len(gkgs) == 0:
                return False  # no work to be done
            for gkg in gkgs:
                analysis = Analysis(gkg=gkg, status=Status.NEW)
                session.add(analysis)
                session.commit()
                logger.info("Worker {} created Analysis {} in status {}".format(
                    os.getpid(), analysis.gkg_id, analysis.status))
        finally:
            # make sure to release a FOR UPDATE lock, if we got one
            if session is not None:
                session.rollback()
                session.close()

        return True
