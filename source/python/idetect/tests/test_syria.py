import os
import logging
from unittest import TestCase
import time
from sqlalchemy import create_engine, func, column, Integer
from idetect.explain import explain_text

from idetect.fact_api import FactApi, add_filters, get_filter_counts
from idetect.model import Session

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logging.basicConfig(format="%(asctime)s %(message)s")


class TestSyriaYear(TestCase):
    syria_locations = [127, 270, 281, 284, 307, 332, 372, 412, 429, 431, 531, 591, 612, 618, 644, 671,
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

    fromdate = '2017-01-01'
    todate = '2018-01-01'

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
        self.engine = create_engine(db_url)  #, echo=True)
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
            fromdate=self.fromdate,
            todate=self.todate,
            locations=self.syria_locations
        ).group_by(FactApi.category)

        t0 = time.time()
        result = {category: count for count, category in syr_year_by_category.all()}
        t1 = time.time()
        print(result)
        self.assertTrue({'Conflict', 'Disaster', 'Other'} == set(result.keys()))
        # print(explain_text(self.session, syr_year_by_category))
        print(t1 - t0)
        self.assertLess(t1 - t0, 1.0)

    def test_filter_counts(self):
        f_c = get_filter_counts(self.session,
            fromdate=self.fromdate,
            todate=self.todate,
            locations=self.syria_locations)
        print(f_c)