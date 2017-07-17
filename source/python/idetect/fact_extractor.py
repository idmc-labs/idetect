'''Method(s) for extracting facts from relevant content.

How to ensure has access to pre-loaded models?
'''
from flask import Blueprint, render_template

extractor_api = Blueprint('extractor_api', __name__)

@extractor_api.route('/extract', methods=['GET'])
def extract():
    # Query URL Database for relevant content

    # For each piece of content, run fact extraction

    # Save extracted facts in Fact Database
    return render_template('success.html', endpoint=__name__)


def extract_facts(content):
    pass