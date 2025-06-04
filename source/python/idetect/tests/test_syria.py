import logging
import os
import time
from datetime import date
from unittest import TestCase, skip

from sqlalchemy import create_engine, func
from tabulate import tabulate

from idetect.fact_api import FactApi, add_filters, get_filter_counts, get_timeline_counts, get_histogram_counts, \
    get_wordcloud, get_urllist, get_count, get_urllist_grouped
from idetect.model import Session, DocumentContent

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logging.basicConfig(format="%(asctime)s %(message)s")


class TestSyriaYear(TestCase):
    syria_location_ids = [127, 270, 281, 284, 307, 332, 372, 412, 429, 431, 531, 591, 612, 618, 644, 671,
                          764, 807, 905, 958, 996, 1018, 1019, 1188, 1190, 1212, 1352, 1357, 1524, 1678,
                          1898, 1981, 1990, 2058, 2060, 2272, 2378, 2735, 2933, 3262, 3323, 3327, 3372,
                          3391, 3404, 3660, 3708, 3725, 3834, 3915, 3924, 4069, 4172, 4399, 4509, 4648,
                          4824, 4890, 5017, 5285, 5833, 6053, 6070, 6270, 6760, 6832, 7121, 7122, 7151,
                          7222, 7244, 7248, 7641, 7723, 7749, 7757, 7827, 7919, 7970, 8078, 8107, 8131,
                          8166, 8176, 8210, 8222, 8240, 8254, 8367, 8442, 8659, 8660, 8730, 8788, 8793,
                          8941, 9045, 9167, 9285, 9370, 9531, 9606, 9775, 9909, 9913, 9916, 9917, 9933,
                          10136, 10312, 10464, 10532, 10795, 10971, 11052, 11076, 11174, 11194, 11216,
                          11250, 11311, 11501, 11703, 11727, 11916, 11933, 12242, 12387, 12990, 13126,
                          13130, 13142, 13171, 13348, 13531, 13659, 13722, 14225, 14718, 14732, 14737,
                          14917, 14930, 14988, 15215, 15257, 15984, 15993, 16188, 17034, 17090, 17373,
                          17404, 17873, 18019, 18131, 18267, 18396, 18403, 18578, 19550, 19641, 19721,
                          20180, 21339, 21894, 22003, 22022, 22162, 22201, 22850, 23189, 23414, 23532,
                          23875, 24851, 25171, 25415, 25894, 25927, 26024, 26283, 26458, 26545, 26909,
                          27027, 27393, 27507, 28185, 28626, 28628, 29703, 29704, 29754, 29942, 30210,
                          30286, 30302, 30442, 30993, 31492, 31743]

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

    def test_categories(self):
        syr_year_by_category = add_filters(
            self.session.query(func.count(FactApi.fact), FactApi.category),
            fromdate=self.start_date,
            todate=self.plus_1_yr,
            location_ids=self.syria_location_ids
        ).group_by(FactApi.category)

        t0 = time.time()
        result = {category: count for count, category in syr_year_by_category.all()}
        t1 = time.time()
        # print(result)
        self.assertEqual(set(result.keys()), {'Conflict', 'Disaster', 'Other'})
        # print(explain_text(self.session, syr_year_by_category))
        print(t1 - t0)
        self.assertLess(t1 - t0, 1.0)

    def test_filter_counts(self):
        f_c = get_filter_counts(self.session,
                                fromdate=self.start_date,
                                todate=self.plus_1_yr,
                                location_ids=self.syria_location_ids)
        # print(f_c)
        self.assertGreater(len(f_c), 1000)

    def test_filter_counts_speed(self):
        for end_date in (self.plus_1_mo, self.plus_3_mo, self.plus_6_mo):
            # Adding this usually fails: , self.plus_1_yr):
            t0 = time.time()
            f_c = get_filter_counts(self.session,
                                    fromdate=self.start_date,
                                    todate=end_date,
                                    location_ids=self.syria_location_ids)
            t1 = time.time()
            print('{} - {}: {}s'.format(self.start_date, end_date, t1 - t0))
            self.assertLess(t1 - t0, 1.0, 'Calculating filter counts {} - {} took too long'.format(
                self.start_date, end_date))

    def test_timeline(self):
        t0 = time.time()
        counts = get_timeline_counts(self.session,
                                     fromdate=self.start_date,
                                     todate=self.plus_1_yr,
                                     location_ids=self.syria_location_ids)
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
        counts = get_histogram_counts(self.session,
                                      fromdate=self.start_date,
                                      todate=self.plus_1_yr,
                                      location_ids=self.syria_location_ids)
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
                              self.engine,
                              fromdate=self.start_date,
                              todate=self.plus_1_yr,
                              location_ids=self.syria_location_ids)
        t1 = time.time()
        print(t1 - t0)
        print(len(terms))
        print(tabulate(terms))
        self.assertLess(t1 - t0, 5.0, 'Calculating wordcloud {} - {} took too long'.format(
            self.start_date, self.plus_1_yr
        ))

    def test_none_location(self):
        # TODO this isn't about Syria, move it somewhere else
        counts = get_filter_counts(self.session, location_ids=['NULL'])
        self.assertGreater(len(counts), 1000)

        self.assertEqual(counts, get_filter_counts(self.session, location_ids=['null']))
        self.assertEqual(counts, get_filter_counts(self.session, location_ids=[None]))

        counts2 = get_filter_counts(self.session, location_ids=['NULL', 1])
        self.assertGreater(len(counts2), len(counts))

    def test_none_specific_reported_figure_1(self):
        # TODO this isn't about Syria, move it somewhere else
        counts = get_filter_counts(self.session, specific_reported_figures=['NULL'])
        srf_counts = [c for c in counts if c['filter_type'] == 'specific_reported_figure']
        self.assertEqual(len(srf_counts), 1)
        self.assertTrue([c for c in srf_counts if c['value'] is None])

        self.assertEqual(counts, get_filter_counts(self.session, specific_reported_figures=['null']))
        self.assertEqual(counts, get_filter_counts(self.session, specific_reported_figures=[None]))

    def test_none_specific_reported_figure_2(self):
        # TODO this isn't about Syria, move it somewhere else
        counts = get_filter_counts(self.session, specific_reported_figures=['NULL', 1])
        srf_counts = [c for c in counts if c['filter_type'] == 'specific_reported_figure']
        self.assertEqual(len(srf_counts), 2)
        self.assertTrue([c for c in srf_counts if c['value'] is None])
        self.assertTrue([c for c in srf_counts if c['value'] == 1])

    def test_none_specific_reported_figure_3(self):
        # TODO this isn't about Syria, move it somewhere else
        counts = get_filter_counts(self.session, specific_reported_figures=['NULL', 1, 1000])
        srf_counts = [c for c in counts if c['filter_type'] == 'specific_reported_figure']
        self.assertGreater(len(srf_counts), 2)
        self.assertTrue([c for c in srf_counts if c['value'] is None])
        self.assertTrue([c for c in srf_counts if c['value'] == 1])

    def test_specific_reported_figure(self):
        # TODO this isn't about Syria, move it somewhere else
        counts = get_filter_counts(self.session, specific_reported_figures=[1, 1000])
        srf_counts = [c for c in counts if c['filter_type'] == 'specific_reported_figure']
        self.assertGreater(len(srf_counts), 2)
        self.assertFalse([c for c in srf_counts if c['value'] is None])
        self.assertTrue([c for c in srf_counts if c['value'] == 1])

    def test_filter_ts(self):
        t0 = time.time()
        query = add_filters(self.session.query(FactApi.content_id, DocumentContent.content_clean),
                            fromdate=self.start_date,
                            todate=self.plus_1_yr,
                            location_ids=self.syria_location_ids,
                            ts='Jordan'
                            ).order_by(FactApi.gdelt_day).limit(32)
        results = query.all()
        t1 = time.time()
        print(t1 - t0)
        for id, content_clean in results:
            self.assertTrue('jordan' in content_clean.lower())

    @skip("Too slow in practice")
    def test_filter_ts_exhaustive(self):
        # make sure that the query found everything that it was supposed to
        t0 = time.time()
        query = add_filters(self.session.query(FactApi.content_id, DocumentContent.content_clean, FactApi.gdelt_day),
                            fromdate=self.start_date,
                            todate=self.plus_1_yr,
                            location_ids=self.syria_location_ids,
                            ts='Jordan'
                            ).order_by(FactApi.gdelt_day).limit(32)
        results = query.all()
        t1 = time.time()
        print(t1 - t0)
        matched = set()
        max_day = date.min
        for id, content_clean, gdelt_day in results:
            self.assertTrue('jordan' in content_clean.lower())
            matched.add(id)
            max_day = max(max_day, gdelt_day)

        t2 = time.time()
        query = add_filters(self.session.query(FactApi.content_id, DocumentContent.content_clean),
                            fromdate=self.start_date,
                            todate=self.plus_1_yr,
                            location_ids=self.syria_location_ids
                            ).filter(FactApi.gdelt_day <= max_day)
        results = query.all()
        t3 = time.time()
        print(t2 - t3)
        print(len(results))
        for id, content_clean in results:
            self.assertEqual(id in matched, 'jordan' in content_clean.lower())

    def test_urllist(self):
        t0 = time.time()
        result1 = get_urllist(self.session,
                              fromdate=self.start_date,
                              todate=self.plus_1_yr,
                              location_ids=self.syria_location_ids)
        t1 = time.time()
        print(t1 - t0)
        self.assertEqual(32, len(list(result1)))
        t2 = time.time()
        result2 = get_urllist(self.session,
                              offset=32,
                              limit=100,
                              fromdate=self.start_date,
                              todate=self.plus_1_yr,
                              location_ids=self.syria_location_ids)
        t3 = time.time()
        print(t3 - t2)
        self.assertEqual(100, len(list(result2)))
        for r1 in result1:
            # print(r1)
            for r2 in result2:
                self.assertLessEqual((r1['gdelt_day'], r1['gkg_id']), (r2['gdelt_day'], r2['gkg_id']), )
        self.assertIn('display_color', result1[0])

    def test_urllist_unique_fact_id(self):
        t0 = time.time()
        result1 = get_urllist(self.session,
                              fromdate=self.start_date,
                              todate=self.plus_1_yr,
                              limit=1000000,
                              location_ids=self.syria_location_ids)
        t1 = time.time()
        print(t1 - t0)
        ids = [f['fact_id'] for f in result1]
        self.assertGreater(len(ids),1000)
        self.assertEqual(len(ids), len(set(ids)))

    def test_urllist_ts(self):
        t0 = time.time()
        result1 = get_urllist(self.session,
                              fromdate=self.start_date,
                              todate=self.plus_1_yr,
                              location_ids=self.syria_location_ids,
                              ts='Jordan')
        t1 = time.time()
        print(t1 - t0)
        self.assertEqual(32, len(list(result1)))
        t2 = time.time()
        result2 = get_urllist(self.session,
                              offset=32,
                              limit=100,
                              fromdate=self.start_date,
                              todate=self.plus_1_yr,
                              location_ids=self.syria_location_ids,
                              ts='Jordan')
        t3 = time.time()
        print(t3 - t2)
        self.assertEqual(100, len(list(result2)))
        for r1 in result1:
            # print(r1)
            for r2 in result2:
                self.assertLessEqual((r1['gdelt_day'], r1['gkg_id']), (r2['gdelt_day'], r2['gkg_id']), )

    def test_count_ts(self):
        t0 = time.time()
        c = get_count(self.session,
                      fromdate=self.start_date,
                      todate=self.plus_1_yr,
                      location_ids=self.syria_location_ids,
                      ts='Jordan'
                      )
        t1 = time.time()
        print(t1 - t0)
        self.assertGreater(c, 5000)
        self.assertLess(c, 10000)

    def test_urllist_grouped(self):
        t0 = time.time()
        result = get_urllist_grouped(self.session,
                                     fromdate=self.start_date,
                                     todate=self.plus_1_yr,
                                     location_ids=self.syria_location_ids,
                                     limit=100
                                     )
        t1 = time.time()
        print(t1 - t0)
        self.assertEqual(100, len(result))
        for entry in result:
            for fact in entry['entry']:
                self.assertEqual(entry['specific_reported_figure'], fact['specific_reported_figure'])
                self.assertEqual(entry['unit'], fact['unit'])
                self.assertEqual(entry['term'], fact['term'])
                self.assertGreater(len(fact['content_clean']), 0)
            fact_ids = [f['fact'] for f in entry['entry']]
            self.assertEqual(len(fact_ids), len(set(fact_ids)), "fact repeated")
