from idetect.nlp_models.category import CategoryModel

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
        # TODO
        # relevance_model = RelevanceModel()
        self.article = article

    def classify(self, article):
        content = self.article.content
        category = self.category_model.predict(content)
        return category