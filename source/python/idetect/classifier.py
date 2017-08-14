from sqlalchemy.orm import object_session

'''Method(s) for running classifier on extracted content.
'''

def classify(article, category_model, relevance_model):
    """
    Classify article into category & relevance and save results to database
    :params article: An Article instance
    :return: None
    """
    session = object_session(article)
    content = article.content.content
    category = category_model.predict(content)
    relevance = relevance_model.transform(content)
    article.category = category
    article.relevance = relevance
    session.commit()
