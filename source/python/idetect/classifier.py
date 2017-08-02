from idetect.nlp_models.category import CategoryModel
from idetect.nlp_models.relevance import RelevanceModel
from idetect.fact_extractor import extract_reports
from idetect.model import Category, Relevance

'''Method(s) for running classifier on extracted content.

How to ensure has access to pre-loaded models?
'''

## Load Spacy English language model
## Uncomment this once using NLP
# nlp = spacy.load('en')
# print("Loaded Spacy english language models.")

## TODO: Load pre-trained classifiers

class Classifier(object):
    def __init__(self, article):
        self.category_model = CategoryModel()
        self.relevance_model = RelevanceModel()
        self.article = article

    def classify(self, article):
        content = self.article.content
        category = self.category_model.predict(content)
        relevance = self.relevance_model.transform(content)
        if relevance == Relevance.DISPLACEMENT:
            reports = extract_reports(self.article)
        return relevance, category, reports
