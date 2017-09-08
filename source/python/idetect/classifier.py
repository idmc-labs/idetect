from sqlalchemy.orm import object_session


'''Method(s) for running classifier on extracted content.
'''

def classify(analysis, category_model, relevance_model):
    """
    Classify article into category & relevance and save results to database
    :params article: An Article instance
    :return: None
    """
    session = object_session(analysis)
    content = analysis.content.content
    category = category_model.predict(content)
    relevance = relevance_model.predict(content)
    analysis.category = category
    analysis.relevance = relevance
    session.commit()
