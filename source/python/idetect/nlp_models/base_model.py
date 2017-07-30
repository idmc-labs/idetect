import fcntl
import os
import errno
import requests
import pandas as pd
from sklearn.externals import joblib


class DownloadableModel(object):

    """Summary

    Attributes:
        model (sklearn model): a
    """

    def __init__(self, model_path, model_url):
        self.model = self.load_model(model_url, model_path)

    def load_model(self, model_url, model_path):
        """Obtains and loads a pickled scikit-learn model. Checks to see if
        the model exists at the specified directory and if not, downloads it
        from a URL.

        Args:
            model_path (str): Path to a model's current location, or the
                location to which it should be downloaded.
            model_url (str): URL where a model lives in storage.

        Returns:
            clf (sklearn model): An unpickled sklearn model (Transformer,
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
                        clf = joblib.load(model_path)
                except IOError as e:
                    if e.errno != errno.EAGAIN:
                        raise
                finally:
                    fcntl.flock(f, fcntl.LOCK_UN)
        else:  # download file
            # if file directory doesn't exist create it
            if not os.path.dirname(model_path):
                try:
                    os.makedirs(os.path.dirname(model_path))
                except OSError as exc:  # Guard against rare condition
                    if exc.errno != errno.EEXIST:
                        raise
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
            clf = joblib.load(model_path)
        return clf

    def predict(self, text):
        """ This method should be overwritten to fit the specific case of the
        model being used """
        return self.model.transform(pd.Series(text))[0]
