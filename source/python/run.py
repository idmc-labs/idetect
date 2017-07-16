#!/Users/simonbedford/anaconda3/bin/python

import time
from threading import Thread

import requests
import schedule
from idetect import app
from idetect.classifier import classifier_api
from idetect.fact_extractor import extractor_api
from idetect.geotagger import geo_api
from idetect.scraper import scraper_api


# Background functions for performing activties every X time

def run_scraper():
    requests.get("http://0.0.0.0:5000/scrape")


def run_classifier():
    requests.get("http://0.0.0.0:5000/classify")


def run_fact_extraction():
    requests.get("http://0.0.0.0:5000/extract")


def run_schedule():
    while True:
        schedule.run_pending()
        time.sleep(1)


app.register_blueprint(scraper_api)
app.register_blueprint(classifier_api)
app.register_blueprint(extractor_api)
app.register_blueprint(geo_api)

if __name__ == "__main__":
    schedule.every(60).seconds.do(run_scraper)
    schedule.every(60).seconds.do(run_classifier)
    schedule.every(60).seconds.do(run_fact_extraction)
    t = Thread(target=run_schedule)
    t.start()
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)
