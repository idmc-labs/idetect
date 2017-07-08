#!/Users/simonbedford/anaconda3/bin/python

from flask import Flask
import spacy
import requests
import schedule
import time
from threading import Thread
from app.scraper import scrape
from app.classifier import classify
from app.fact_extractor import extract
from app.geotagger import geo_info


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


@app.route('/scrape', methods=['GET'])

@app.route('/classify', methods=['GET'])

@app.route('/extract', methods=['GET'])

@app.route('/geo_info', methods=['GET'])


if __name__ == "__main__":

    ## Load Spacy English language model
    nlp = spacy.load("en")
    ## TODO: Load pre-trained classifiers

    schedule.every(60).seconds.do(run_scraper)
    schedule.every(60).seconds.do(run_classifier)
    schedule.every(60).seconds.do(run_fact_extraction)
    t = Thread(target=run_schedule)
    t.start()

    app.run(host='0.0.0.0', port='5000', debug=True, threaded=True)
