import gensim
import numpy as np
import pandas as pd
from nltk.stem import PorterStemmer
from nltk.tokenize import WordPunctTokenizer
from sklearn.base import BaseEstimator, TransformerMixin

from idetect.model import Relevance
from idetect.nlp_models.base_model import DownloadableModel


class RelevanceModel(DownloadableModel):
    def __init__(self, model_path='relevance.pkl',
            model_url='https://s3-us-west-2.amazonaws.com/idmc-idetect/relevance_models/relevance.pkl'):
        self.model = self.load_model(model_path, model_url)

    def predict(self, text):
        try:
            relevance = self.model.transform(pd.Series(text))[0]
            if relevance == 'yes':
                return Relevance.DISPLACEMENT
            else:
                return Relevance.NOT_DISPLACEMENT
        except ValueError:
            # error can occur if empty text is passed to model
            raise


class Tokenizer(TransformerMixin):
    def __init__(self, stop_words=None):
        self.stop_words = stop_words
        self.tokenizer = WordPunctTokenizer()

    def prepare_tokens(self, text, stop_words):
        tokens = self.tokenizer.tokenize(text)
        tokens = [t for t in tokens if len(t) > 2]
        tokens = [t.lower() for t in tokens]
        tokens = [t for t in tokens if t not in stop_words]
        tokens = [t for t in tokens if not t.isdigit()]
        return tokens

    def fit(self, X, *args):
        return self

    def transform(self, X, *args):
        X = X.map(lambda x: self.prepare_tokens(x, self.stop_words))
        return X


class Stemmer(TransformerMixin):
    def __init__(self, stop_words):
        self.stop_words = stop_words
        self.tokenizer = WordPunctTokenizer()
        self.stemmer = PorterStemmer()

    def prepare_stems(self, text, stop_words):
        tokens = self.tokenizer.tokenize(text)
        tokens = [t for t in tokens if len(t) > 2]
        tokens = [t.lower() for t in tokens]
        tokens = [t for t in tokens if t not in stop_words]
        stems = [self.stemmer.stem(t) for t in tokens]
        stems = [s for s in stems if not s.isdigit()]
        return stems

    def fit(self, X, *args):
        return self

    def transform(self, X, *args):
        X = X.map(lambda x: self.prepare_stems(x, self.stop_words))
        return X


class TfidfTransformer(TransformerMixin):
    def __init__(self, no_below=5, no_above=0.5):
        self.no_below = no_below
        self.no_above = no_above

    def set_dictionary(self, texts):
        self.dictionary = gensim.corpora.Dictionary(texts)
        if self.no_below or self.no_above:
            self.dictionary.filter_extremes(no_below=self.no_below,
                                            no_above=self.no_above)

    def make_corpus(self, texts):
        corpus = [self.dictionary.doc2bow(text) for text in texts]
        return corpus

    def set_tfidf_model(self, corpus):
        self.tfidf_model = gensim.models.TfidfModel(corpus, normalize=True)

    def fit(self, texts, y=None):
        self.set_dictionary(texts)
        corpus = self.make_corpus(texts)
        self.set_tfidf_model(corpus)
        return self

    def transform(self, texts):
        corpus = self.make_corpus(texts)
        return self.tfidf_model[corpus]


class LsiTransformer(TransformerMixin):
    def __init__(self, n_dimensions=100, no_below=5, no_above=0.5):
        self.n_dimensions = n_dimensions
        self.no_below = no_below
        self.no_above = no_above

    def lsi_to_vecs(self, corpus_lsi):
        lsi_vecs = []
        for c in corpus_lsi:
            vec = [x[1] for x in c]
            lsi_vecs.append(vec)
        return np.array(lsi_vecs)

    def make_tfidf(self, texts):
        self.tfidf_transformer = TfidfTransformer(no_below=self.no_below,
                                                  no_above=self.no_above)
        self.tfidf_transformer.fit(texts)
        corpus_tfidf = self.tfidf_transformer.transform(texts)
        dictionary = self.tfidf_transformer.dictionary
        return corpus_tfidf, dictionary

    def make_corpus(self, corpus_tfidf):
        lsi_corpus = self.lsi_model[corpus_tfidf]
        return lsi_corpus

    def set_lsi_model(self, texts):
        corpus_tfidf, dictionary = self.make_tfidf(texts)
        self.lsi_model = gensim.models.LsiModel(corpus_tfidf,
                                                id2word=dictionary,
                                                num_topics=self.n_dimensions)

    def fit(self, texts, *args, **kwargs):
        self.set_lsi_model(texts)
        self.corpus_lsi = self.lsi_model[self.corpus_tfidf]
        return self

    def transform(self, texts):
        corpus_tfidf = self.tfidf_transformer.transform(texts)
        corpus_lsi = self.make_corpus(corpus_tfidf)
        return self.lsi_to_vecs(corpus_lsi)


class RelevanceKeyWordClassifier(BaseEstimator):
    def __init__(self):
        self.stemmer = PorterStemmer()
        self.create_keywords()

    def create_keywords(self):
        displacement_tokens = ['evacuated', 'evacuee', 'displaced', 'displacement', 'fled', 'stranded', 'homeless',
                  'flee', 'rescued', 'trapped', 'shelter', 'camp', 'escape', 'forced', 'migrant', 'run', 'ran']
        self.displacement_stems = [self.stemmer.stem(token) for token in displacement_tokens]
        return self

    def tag_by_stem(self, texts, displacement_stems):
        is_displacement = []
        for text in texts:
            mentions = 0
            for stem in self.displacement_stems:
                mentions += text.count(stem)
            if mentions > 0:
                is_displacement.append('yes')
            else:
                is_displacement.append('no')
        return is_displacement

    def fit(self, *args):
        return self

    def transform(self, X, *args):
        y = self.tag_by_stem(X, self.displacement_stems)
        return y

    def predict(self, X, y=None):
        y = self.tag_by_stem(X, self.displacement_stems)


class Combiner(BaseEstimator, TransformerMixin):
    def __init__(self, ml_model, kw_model):
        self.ml_model = ml_model
        self.kw_model = kw_model

    def combine_relevance_tags(self, classified, keyword_tagged):
        combined = []
        for classifier, keyword in zip(classified, keyword_tagged):
            if keyword == 'no' and classifier == 'no':
                tag = 'no'
            elif keyword == 'yes' and classifier == 'yes':
                tag = 'yes'
            elif keyword == 'no' and classifier == 'yes':
                tag = 'yes'
            elif keyword == 'yes' and classifier == 'no':
                tag = 'yes'
            combined.append(tag)
        return combined

    def fit(self, X, y=None):
        return self

    def transform(self, X, *args):
        ml_tagged = self.ml_model.predict(X)
        kw_tagged = self.kw_model.transform(X)
        combined = self.combine_relevance_tags(ml_tagged, kw_tagged)
        return combined