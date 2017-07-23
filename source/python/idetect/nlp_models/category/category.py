import os
import requests
import gensim
import pandas as pd
import numpy as np
from nltk.tokenize import WordPunctTokenizer
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.pipeline import Pipeline
from sklearn.ensemble import RandomForestClassifier
from sklearn.externals import joblib

from idetect.model import Category

class CategoryModel(object):
    def __init__(self, model_path=None):
        self.model = self.load_model(model_path=model_path)

    def load_model(self, model_path=None):
        if model_path and os.path.isfile(model_path):
            clf = joblib.load(model_path)
        else:
            default_model_path = 'category.pkl'
            if os.path.isfile(default_model_path):
                clf = joblib.load(default_model_path)
            else:
                url = 'https://s3-us-west-2.amazonaws.com/idmc-idetect/category_models/category.pkl'
                r = requests.get(url, stream=True)
                if not os.path.isfile(default_model_path):
                    try:
                        os.makedirs(os.path.dirname(default_model_path))
                    except OSError as exc: # Guard against race condition
                        if exc.errno != errno.EEXIST:
                            raise
                with open(default_model_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=1024):
                        if chunk:  # filter out keep-alive new chunks
                            f.write(chunk)
                clf = joblib.load(default_model_path)
        return clf

    def predict(self, text):
        try:
            category = self.model.predict(pd.Series(text))[0]
        except:
            # if error occurs, classify as most likely category
            category = 'disaster'

        if category == 'disaster':
            return Category.DISASTER
        elif category == 'conflict':
            return Category.CONFLICT
        else:
            return Category.OTHER

class Tokenizer(TransformerMixin):
    def __init__(self, stop_words=None):
        self.stop_words = stop_words
        self.tokenizer = WordPunctTokenizer()
        
    def prepare_tokens(self, text, stop_words):
        tokens = self.tokenizer.tokenize(text)
        tokens = [t for t in tokens if len(t) > 2]
        tokens = [t for t in tokens if t not in stop_words]
        tokens = [t.lower() for t in tokens]
        tokens = [t for t in tokens if not t.isdigit()]
        return tokens
    
    def fit(self, X, *args):
        return self
    
    def transform(self, X, *args):
        X = X.map(lambda x: self.prepare_tokens(x, self.stop_words))
        return X

class TfidfTransformer(TransformerMixin):
    def __init__(self, no_below=5, no_above=0.5, tfidf_model=None, dictionary=None):
        self.dictionary = dictionary
        self.tfidf_model = tfidf_model
        self.no_below = no_below
        self.no_above = no_above
    
    def make_dictionary(self, texts):
        if not self.dictionary:
            self.dictionary = gensim.corpora.Dictionary(texts)
            if self.no_below or self.no_above:
                self.dictionary.filter_extremes(no_below=self.no_below, no_above=self.no_above)
        return self
    
    def tfidf_transform(texts, dictionary=None, tfidf_model=None):
        if not dictionary:
            dictionary = gensim.corpora.Dictionary(texts)
        corpus = [dictionary.doc2bow(text) for text in texts]
        if not tfidf_model:
            tfidf_model = gensim.models.TfidfModel(corpus)
        corpus_tfidf = tfidf_model[corpus]
        return corpus_tfidf, dictionary, tfidf_model
    
    def make_corpus(self, texts):
        corpus = [self.dictionary.doc2bow(text) for text in texts]
        return corpus
    
    def make_tfidf_model(self, corpus):
        if not self.tfidf_model:
            self.tfidf_model = gensim.models.TfidfModel(corpus)
        return self
    
    def fit(self, texts, y=None):
        self.make_dictionary(texts)
        self.corpus = self.make_corpus(texts)
        self.make_tfidf_model(self.corpus)
        
    def transform(self, texts):
        corpus = self.make_corpus(texts)
        return self.tfidf_model[corpus]

class LsiTransformer(TransformerMixin):
    def __init__(self, n_dimensions=100, no_below=5, no_above=0.5, lsi_model=None):
        self.lsi_model = lsi_model
        self.n_dimensions = n_dimensions
        self.no_below = no_below
        self.no_above = no_above
    
    def build_tfidf(self, texts):
        self.tfidf_transformer = TfidfTransformer(no_below=self.no_below, no_above=self.no_above)
        self.tfidf_transformer.fit(texts)
        corpus_tfidf = self.tfidf_transformer.transform(texts)
        dictionary = self.tfidf_transformer.dictionary
        return corpus_tfidf, dictionary
    
    def lsi_to_vecs(self, corpus_lsi):
        lsi_vecs = []
        for c in corpus_lsi:
            vec = [x[1] for x in c]
            lsi_vecs.append(vec)
        return np.array(lsi_vecs)
    
    def make_lsi_model(self, texts):    
        self.corpus_tfidf, self.dictionary = self.build_tfidf(texts)
        if not self.lsi_model:
            self.lsi_model = gensim.models.LsiModel(self.corpus_tfidf, 
                                                    id2word=self.dictionary, 
                                                    num_topics=self.n_dimensions)
        return self
    
    def make_corpus(self, corpus_tfidf):
        lsi_corpus = self.lsi_model[corpus_tfidf]
        return lsi_corpus
    
    def fit(self, texts, *args, **kwargs):
        self.make_lsi_model(texts)
        self.corpus_lsi = self.lsi_model[self.corpus_tfidf]
        return self
    
    def transform(self, texts):
        corpus_tfidf = self.tfidf_transformer.transform(texts)
        corpus_lsi = self.make_corpus(corpus_tfidf)
        return self.lsi_to_vecs(corpus_lsi)
        