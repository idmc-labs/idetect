import errno
import fcntl
import os
import re

import pandas as pd
import requests
import spacy
from sklearn.externals import joblib
from sklearn.base import TransformerMixin, BaseEstimator
from scipy import sparse
from gensim import matutils, models
from gensim.sklearn_integration.sklearn_wrapper_gensim_lsimodel import SklLsiModel

from idetect.geotagger import strip_accents, compare_strings, strip_words, common_names, LocationType, subdivision_country_code, match_country_name, city_subdivision_country

class DownloadableModel(object):
    """A base class for loading pickeld scikit-learn models that may be stored
    locally or in online storage.

    Attributes:
        model (sklearn model): a scikit-learn Transformer, Estimator, or
            Pipeline, which has the "predict" method.
    """

#    def __init__(self, model_path, model_url):
#        self.model = self.load_model(model_path, model_url)

    def load_model(self, model_path, model_url):
        """Obtains and loads a pickled scikit-learn model. Checks to see if
        the model exists at the specified directory and if not, downloads it
        from a URL.

        Args:
            model_path (str): Path to a model's current location, or the
                location to which it should be downloaded.
            model_url (str): URL where a model lives in storage.

        Returns:
            model (sklearn model): An unpickled sklearn model (Transformer,
                Estimator, or Pipeline).
        """
        # Load users model if specified and exists
        if os.path.isfile(model_path):
            with open(model_path, 'rb') as f:
                # get exclusive lock in case currently being downloaded by
                # another worker
                try:
                    fcntl.flock(f, fcntl.LOCK_EX)
                    if os.path.getsize(model_path) > 0:
                        model = joblib.load(model_path)
                        return model
                except IOError as e:
                    if e.errno != errno.EAGAIN:
                        raise
                finally:
                    fcntl.flock(f, fcntl.LOCK_UN)
        # if file directory doesn't exist create it
        try:
            os.makedirs(os.path.dirname(model_path))
        except FileExistsError:
            if not os.path.isdir(os.path.dirname(model_path)):
                raise
        except FileNotFoundError:
            if os.path.dirname(model_path) == '':
                pass
        with open(model_path, 'wb+') as f:
            try:
                fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
                if os.path.getsize(model_path) == 0:
                    r = requests.get(model_url, stream=True)
                    for chunk in r.iter_content(chunk_size=1024):
                        if chunk:  # filter out keep-alive new chunks
                            f.write(chunk)
            except BlockingIOError as e:
                fcntl.flock(f, fcntl.LOCK_EX)
            finally:
                fcntl.flock(f, fcntl.LOCK_UN)
        model = joblib.load(model_path)
        return model

    def predict(self, text):
        """ This method should be overwritten to fit the specific case of the
        model being used """
        try:
            return self.model.transform(pd.Series(text))[0]
        except ValueError:
            raise


class CustomSklLsiModel(SklLsiModel):
    """Gensim's Lsi model with sklearn wrapper, modified to handle sparse matrices
    for both fit and transform. Makes the class compatible with sklearn's Tfidf and
    Count vectorizers.
    """

    def sparse_2_tupes(self, sparse):
        """Converts sparse matrix into manageable tuple format."""
        for t in t_skltfidf:
            cx = t.tocoo()
            tups = []
            for i, j in zip(cx.col, cx.data):
                tups.append((i, j))
        return tups

    def fit(self, X, y=None):
        """
        Fit the model according to the given training data.
        Calls gensim.models.LsiModel
        """
        if sparse.issparse(X):
            corpus = matutils.Sparse2Corpus(X, documents_columns=False)
        else:
            corpus = X

        self.gensim_model = models.LsiModel(corpus=corpus, num_topics=self.num_topics, id2word=self.id2word, chunksize=self.chunksize,
            decay=self.decay, onepass=self.onepass, power_iters=self.power_iters, extra_samples=self.extra_samples)
        return self

    def transform(self, docs):
        """
        Takes a list of documents as input ('docs').
        Returns a matrix of topic distribution for the given document bow, where a_ij
        indicates (topic_i, topic_probability_j).
        The input `docs` should be in BOW format and can be a list of documents like : [ [(4, 1), (7, 1)], [(9, 1), (13, 1)], [(2, 1), (6, 1)] ]
        or a single document like : [(4, 1), (7, 1)]
        """
        if self.gensim_model is None:
            raise NotFittedError("This model has not been fitted yet. Call 'fit' with appropriate arguments before using this method.")

        # The input as array of array
        # import pdb; pdb.set_trace()
        # check = lambda x: [x] if isinstance(x[0], tuple) else x
        # docs = check(docs)
        if sparse.issparse(docs):
            docs = matutils.Sparse2Corpus(docs, documents_columns=False)
        X = [[] for i in range(0, len(docs))];
        for k,v in enumerate(docs):
            doc_topics = self.gensim_model[v]
            probs_docs = list(map(lambda x: x[1], doc_topics))
            # Everything should be equal in length
            if len(probs_docs) != self.num_topics:
                probs_docs.extend([1e-12]*(self.num_topics - len(probs_docs)))
            X[k] = probs_docs
            probs_docs = []
        return np.reshape(np.array(X), (len(docs), self.num_topics))
