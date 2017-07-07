#!/Users/simonbedford/anaconda3/bin/python

from flask import Flask
import spacy
import requests
import schedule
import time
from threading import Thread


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
def scrape():
    # Query Database for list of URLs

    # For each URL, try and access and scrape

    # If successful, save contents & metadata & change status

    # If unsuccessful, save metadata

    # Save date scraped and increase attempts by 1
    pass


@app.route('/classify', methods=['GET'])
def classify():
    # Query Database for scraped content

    # For each piece of content run relevance classifier

    # For relevant content run category classifier

    # Update metadata columns in URL table
    pass


@app.route('/extract', methods=['GET'])
def extract():
    # Query URL Database for relevant content

    # For each piece of content, run fact extraction

    # Save extracted facts in Fact Database
    pass


@app.route('/geo_info', methods=['GET'])
def geo_info():
    '''This exposes the internal geo tagging functionality.
    In fact extraction, the geo tagging solution can be internal or external.
    '''

    # Receive place name + context

    # Return JSON of geo data such as lat/long, country, state etc.
    pass


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
