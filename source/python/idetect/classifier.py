from idetect.nlp_models.category import CategoryModel
from idetect.nlp_models.relevance import RelevanceModel
from sqlalchemy.orm import object_session

'''Method(s) for running classifier on extracted content.
'''

def classify(article):
    """
    Classify article into category & relevance and save results to database
    :params article: An Article instance
    :return: None
    """
    session = object_session(article)
    content = article.content.content
    category = CategoryModel().predict(content)
    relevance = RelevanceModel().transform(content)
    article.category = category
    article.relevance = relevance
    session.commit()
