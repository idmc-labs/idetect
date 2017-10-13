import numpy as np
import pandas as pd
import re
import string
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.pipeline import Pipeline, FeatureUnion
from sklearn.svm import LinearSVC
from spacy.tokens.token import Token

from idetect.model import Relevance
from idetect.nlp_models.base_model import DownloadableModel, CustomSklLsiModel
from idetect.fact_extractor import nlp
from idetect.geotagger import strip_accents, compare_strings, strip_words, common_names, LocationType, subdivision_country_code, match_country_name, city_subdivision_country


class RelevanceModel(DownloadableModel):
    def __init__(self, model_path='/home/idetect/python/idetect/nlp_models/relevance_classifier_svm_10132017.pkl',
            model_url='https://s3-us-west-2.amazonaws.com/idmc-idetect/relevance_models/relevance_classifier_svm_10132017.pkl'):
        self.model = self.load_model(model_path, model_url)

    def predict(self, text):
        try:
            relevance = self.model.predict(pd.Series(text))[0]
            if relevance == 1:
                return Relevance.DISPLACEMENT
            elif relevance == 0:
                return Relevance.NOT_DISPLACEMENT
        except ValueError:
            # error can occur if empty text is passed to model
            raise


class LocationProcessor(BaseEstimator, TransformerMixin):
    """Transformer that replaces all country and subdivisions
        mentioned in text with common names.
    """

    def tag_entities(self, text):
        tokens = []
        for token in text:
            if token.ent_type_ == 'GPE':
                if match_country_name(token.text)[0]:
                    tokens.append('Switzerland')
                elif city_subdivision_country(token.text):
                    tokens.append('Geneva')
                else:
                    tokens.append('Geneva')
            elif token.like_num:
                tokens.append('1000')
            elif token.like_url:
                continue
            elif token.like_email:
                continue
            else:
                tokens.append(token.text)
        return tokens

    def join_phrases(self, phrases):
        joined = []
        for phrase in phrases:
            tokens = []
            for token in phrase:
                if isinstance(token, Token):
                    tokens.append(token.lemma_)
                else:
                    tokens.append(token)
            if len(tokens) < 2:
                continue
            joined.append('_'.join(tokens))
        return joined

    def single_string(self, texts):
        strings = [' '.join(t) for t in texts]
        return strings

    def fit(self, texts, *args):
        return self

    def transform(self, texts, *args):
        texts = [nlp(t) for t in texts]
        texts = [self.tag_entities(t) for t in texts]
        texts = self.single_string(texts)
        return texts


class PhraseProcessor(BaseEstimator, TransformerMixin):
    """Transformer that creates phrases from documents.

    Parameters
    ----------
    pos_tags : bool, required
        Whether to tag words with their part of speech labels.
    lemmatize : bool, required
        Whether to lemmatize tokens.
    stop_words : book, required
        Whether to remove stop words.
    """

    def __init__(self, stop_words):
        self.stop_words = stop_words

    def parse_phrases(self, doc):
        '''Return a list of lists, with each sublist containing a token from the text,
        it's parent token and it's grandparent token. Does not return any repeat tokens
        in each phrase.'''
        phrases = []
        for d in doc:
            if not d.is_punct:
                if d.head != d:
                    if d.head.head != d.head:
                        phrases.append([d, d.head, d.head.head])
                    else:
                        phrases.append([d, d.head])
        return phrases

    def join_phrases(self, phrases):
        joined = []
        for phrase in phrases:
            tokens = []
            for token in phrase:
                if isinstance(token, Token):
                    tokens.append(token.lemma_)
                else:
                    tokens.append(token)
            if len(tokens) < 2:
                continue
            joined.append('_'.join(tokens))
        return joined

    def single_string(self, texts):
        strings = [' '.join(t) for t in texts]
        return strings

    def fit(self, texts, *args):
        return self

    def transform(self, texts, *args):
#         import pdb; pdb.set_trace()
        docs = [nlp(t) for t in texts]
        phrases = [self.parse_phrases(d) for d in docs]
        joined = [self.join_phrases(p) for p in phrases]
        text = self.single_string(joined)
        return text


class POSProcessor(BaseEstimator, TransformerMixin):
    """Transformer that labels tokens in a document with their
    part of speech tags.

    Parameters
    ----------
    pos_tags : bool, required
        Whether to tag words with their part of speech labels.
    lemmatize : bool, required
        Whether to lemmatize tokens.
    stop_words : book, required
        Whether to remove stop words.
    """

    def __init__(self, stop_words, pos_tags=True,
                rejoin=True):
        self.stop_words = stop_words
        self.pos_tags = pos_tags
        self.rejoin = rejoin

    def tag_pos(self, text):
        return [(t, t.pos_) for t in text]

    def get_lemmas(self, text):
        return [t[0].lemma_ for t in text]

    def remove_noise(self, text):
        noise_tags = ['DET', 'NUM', 'SYM']
        text = [t for t in text if t[0].text not in self.stop_words]
        text = [t for t in text if len(t[0]) > 2]
        text = [t for t in text if t[1] not in noise_tags]
        text = [t for t in text if ~t[0].like_num]
        return text

    def join_pos_lemmas(self, pos, lemmas):
        return ['{}_{}'.format(l, p[1]).lower() for p, l
                in zip(pos, lemmas)]

    def fit(self, texts, *args):
        return self

    def single_string(self, texts):
        strings = [' '.join(t) for t in texts]
        return strings

    def transform(self, texts, *args):
        docs = [nlp(sent) for sent in texts]
        docs = [self.tag_pos(d) for d in docs]
        docs = [self.remove_noise(d) for d in docs]
        lemmas = [self.get_lemmas(d) for d in docs]
        if self.pos_tags:
            docs = [self.join_pos_lemmas(d, l) for d, l
                    in zip(docs, lemmas)]
        if self.rejoin:
            docs = self.single_string(docs)
        return docs
