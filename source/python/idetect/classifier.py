from sqlalchemy.orm import object_session


'''Method(s) for running classifier on extracted content.
'''

def classify(analysis, category_model, relevance_model):
    """
    Tag and categorize analysis using its content.
    
    :params analysis: An Analysis instance
    :return: None
    """
    session = object_session(analysis)
    content = analysis.content.content
    category = category_model.predict(content)
    content_clean = analysis.content.content_clean
    relevance = relevance_model.predict(content_clean)
    analysis.category = category
    analysis.relevance = relevance
    session.commit()
