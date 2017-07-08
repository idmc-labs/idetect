#!/Users/simonbedford/anaconda3/bin/python

from flask import Flask
import spacy
import requests
import schedule
import time
from threading import Thread
from app.scraper import scraper_api
from app.classifier import classifier_api
from app.fact_extractor import extractor_api
from app.geotagger import geo_api


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


app = Flask(__name__)
app.register_blueprint(scraper_api)
app.register_blueprint(classifier_api)
app.register_blueprint(extractor_api)
app.register_blueprint(geo_api)

# @app.route('/classify', methods=['GET'])
# classify()

# @app.route('/extract', methods=['GET'])
# extract()


if __name__ == "__main__":

    ## Load Spacy English language model
    # nlp = spacy.load("en")
    ## TODO: Load pre-trained classifiers

    # schedule.every(60).seconds.do(run_scraper)
    # schedule.every(60).seconds.do(run_classifier)
    # schedule.every(60).seconds.do(run_fact_extraction)
    # t = Thread(target=run_schedule)
    # t.start()

    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)
