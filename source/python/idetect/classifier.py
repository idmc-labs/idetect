import gensim
import pandas as pd
import numpy as np
import sklearn
import operator
from nltk.tokenize import WordPunctTokenizer
from nltk.stem import PorterStemmer

'''Method(s) for running classifier on extracted content.

How to ensure has access to pre-loaded models?
'''

## Load Spacy English language model
## Uncomment this once using NLP
# nlp = spacy.load('en')
# print("Loaded Spacy english language models.")

## TODO: Load pre-trained classifiers

class Category(object):
    def __init__(self):
        pass

    conflict_tokens = ['war', 'conflict', 'military', 'ceasefire', 'terrorism', 'fighting', 'militia', 'rebels', 
                  'violence', 'violent', 'clash', 'insurgent', 'besiege', 'bomb', 'gun', 'combat', 'siege',
                  'battle', 'battleground', 'explode', 'explosive', 'peace', 'truce', 'airstrike']
    conflict_stems = [stemmer.stem(token) for token in conflict_tokens]
    disaster_tokens = ['flood', 'wildfire', 'fire', 'earthquake', 'mudslide', 'landslide', 'washed', 'hurricane',
                      'storm', 'rain', 'rainfall', 'river', 'sea', 'disaster', 'volcano', 'typhoon', 'blaze',
                     'tremor', 'drought', 'disease', 'malnutrition', 'virus', 'health', 'tornado', 'forest', 'snow']
    disaster_stems = [stemmer.stem(token) for token in disaster_tokens]
     
    def prepare_text(self, text, stop_words):
        tokenizer = WordPunctTokenizer()
        stemmer = PorterStemmer()    
        tokens = tokenizer.tokenize(text)
        tokens = [t for t in tokens if len(t) > 2]
        tokens = [t for t in tokens if t not in stop_words] 
        stems = [stemmer.stem(t) for t in tokens]
        stems = [s.lower() for s in stems]
        stems = [s for s in stems if not s.isdigit()]
        return stems

    def load_models(self, model_path=''):
        pass

    def load_stop_words(self, stop_words_path=''):
        pass

    def load_vocabularies(self, vocab_path=''):
        pass

    def tag_by_stem(self, texts, conflict_stems, disaster_stems):
        equals = []
        categories = []
        tag_dicts = []
        for text in texts:
            tag_dictionary = {'conflict': 0, 'disaster': 0}
            for stem in conflict_stems:
                tag_dictionary['conflict'] = tag_dictionary['conflict'] + text.count(stem)
            for stem in disaster_stems:
                tag_dictionary['disaster'] = tag_dictionary['disaster'] + text.count(stem)
            
            if tag_dictionary['conflict'] == 0 and tag_dictionary['disaster'] == 0:
                category = 'other'
                e = True
            elif tag_dictionary['conflict'] == tag_dictionary['disaster']:
                category = 'unknown'
                e = True
            else:
                category = max(tag_dictionary, key=tag_dictionary.get)
                e = False
            categories.append(category)
            tag_dicts.append(tag_dictionary)
            equals.append(e)
        return categories

    def classify(self, article):
        # Query Database for scraped content

        # For each piece of content run relevance classifier

        # For relevant content run category classifier

        # Update metadata columns in URL table
        return True
