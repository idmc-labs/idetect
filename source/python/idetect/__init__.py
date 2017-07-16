from flask import Flask
import json
import spacy


app = Flask(__name__)


#with open('data/cities_to_countries.json', "r") as f:
cities_to_countries = {} # json.load(f)
print("Loaded cities_to_countries dictionary.")

## Load Spacy English language model
## Uncomment this once using NLP
# nlp = spacy.load('en')
# print("Loaded Spacy english language models.")

## TODO: Load pre-trained classifiers