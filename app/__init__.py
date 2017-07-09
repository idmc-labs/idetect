from flask import Flask
import json


app = Flask(__name__)


with open('data/cities_to_countries.json', "r") as f:
    cities_to_countries = json.load(f)

## Load Spacy English language model
## TODO: Load pre-trained classifiers