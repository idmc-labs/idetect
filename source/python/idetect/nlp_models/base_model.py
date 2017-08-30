import errno
import fcntl
import os

import pandas as pd
import requests
from sklearn.externals import joblib


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
