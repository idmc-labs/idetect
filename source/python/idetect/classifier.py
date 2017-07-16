'''Method(s) for running classifier on extracted content.

How to ensure has access to pre-loaded models?
'''
from flask import Blueprint


classifier_api = Blueprint('classifier_api', __name__)

@classifier_api.route('/classify', methods=['GET'])
def classify():
    # Query Database for scraped content

    # For each piece of content run relevance classifier

    # For relevant content run category classifier

    # Update metadata columns in URL table
    pass
