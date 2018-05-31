import json
import logging
import os
import time
from unittest import TestCase

from sqlalchemy import create_engine
from tabulate import tabulate

from idetect.fact_api import FactApi, get_timeline_counts, get_histogram_counts, \
    get_wordcloud, get_map_week
from idetect.model import Session

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logging.basicConfig(format="%(asctime)s %(message)s")


class TestManager(TestCase):
    start_date = '2017-01-01'
    plus_1_yr = '2018-01-01'
    plus_6_mo = '2017-07-01'
    plus_3_mo = '2017-04-01'
    plus_1_mo = '2017-02-01'

    def setUp(self):
        logger.debug("setUp")
        worker_logger = logging.getLogger("idetect.worker")
        worker_logger.setLevel(logging.INFO)

        logger.debug("Connecting to DB")
        db_host = os.environ.get('DB_HOST')
        db_port = os.environ.get('DB_PORT', 5432)
        db_user = os.environ.get('DB_USER', 'tester')
        db_pass = os.environ.get('DB_PASSWORD', 'tester')

        db_url = 'postgresql://{user}:{passwd}@{db_host}:{db_port}/{db}'.format(
            user=db_user, passwd=db_pass, db_host=db_host, db_port=db_port, db='idetect')
        self.engine = create_engine(db_url, echo=False)
        Session.configure(bind=self.engine)
        self.session = Session()
        self.session.query(FactApi).count()
        logger.debug("setUp complete")

    def tearDown(self):
        logger.debug("tearDown")
        self.session.rollback()
        logger.debug("sessions rolled back")
        logger.debug("tearDown complete")

    def test_timeline(self):
        t0 = time.time()
        counts = get_timeline_counts(self.session)
        t1 = time.time()

        days = {t['gdelt_day'] for t in counts}
        self.assertGreater(len(days), 180)

        categories = {t['category'] for t in counts}
        self.assertEqual(categories, {'Conflict', 'Disaster', 'Other'})

        print(t1 - t0)
        self.assertLess(t1 - t0, 1.0, 'Calculating timeline counts {} - {} took too long'.format(
            self.start_date, self.plus_1_yr
        ))

    def test_histogram(self):
        t0 = time.time()
        counts = get_histogram_counts(self.session)
        t1 = time.time()
        print(len(counts))

        figures = {t['specific_reported_figure'] for t in counts if t['specific_reported_figure']}
        self.assertLess(min(figures), 10)
        self.assertGreater(max(figures), 1000000)

        units = {t['unit'] for t in counts}
        self.assertEqual(units, {'Household', 'Person'})

        print(t1 - t0)
        self.assertLess(t1 - t0, 1.0,
                        'Calculating histogram counts {} - {} took too long'.format(
                            self.start_date, self.plus_1_yr))

    def test_wordcloud(self):
        t0 = time.time()
        terms = get_wordcloud(self.session,
                              self.engine)
        t1 = time.time()
        print(t1 - t0)
        print(len(terms))
        print(tabulate(terms))
        self.assertLess(t1 - t0, 5.0, 'Calculating wordcloud {} - {} took too long'.format(
            self.start_date, self.plus_1_yr
        ))

    def test_timeline_year(self):
        t0 = time.time()
        counts = get_timeline_counts(self.session,
                                     fromdate=self.start_date,
                                     todate=self.plus_1_yr)
        t1 = time.time()

        days = {t['gdelt_day'] for t in counts}
        self.assertGreater(len(days), 180)

        categories = {t['category'] for t in counts}
        self.assertEqual(categories, {'Conflict', 'Disaster', 'Other'})

        print(t1 - t0)
        self.assertLess(t1 - t0, 1.0, 'Calculating timeline counts {} - {} took too long'.format(
            self.start_date, self.plus_1_yr
        ))

    def test_histogram_year(self):
        t0 = time.time()
        counts = get_histogram_counts(self.session,
                                      fromdate=self.start_date,
                                      todate=self.plus_1_yr)
        t1 = time.time()
        print(len(counts))

        figures = {t['specific_reported_figure'] for t in counts if t['specific_reported_figure']}
        self.assertLess(min(figures), 10)
        self.assertGreater(max(figures), 1000000)

        units = {t['unit'] for t in counts}
        self.assertEqual(units, {'Household', 'Person'})

        print(t1 - t0)
        self.assertLess(t1 - t0, 1.0,
                        'Calculating histogram counts {} - {} took too long'.format(
                            self.start_date, self.plus_1_yr))

    def test_wordcloud_year(self):
        t0 = time.time()
        terms = get_wordcloud(self.session,
                              self.engine,
                              fromdate=self.start_date,
                              todate=self.plus_1_yr)
        t1 = time.time()
        print(t1 - t0)
        print(len(terms))
        print(tabulate(terms))
        self.assertLess(t1 - t0, 5.0, 'Calculating wordcloud {} - {} took too long'.format(
            self.start_date, self.plus_1_yr
        ))

    def test_map_week(self):
        print("hello")
        t0 = time.time()
        entries = get_map_week(self.session)
        t1 = time.time()
        print(t1 - t0)
        # print(json.dumps(entries, indent=2))
        self.assertEqual(len(entries), 1)
        self.assertIsNotNone(entries[0].get('entries'))