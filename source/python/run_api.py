import logging

from flask import Flask, render_template, abort, request, redirect, url_for
from sqlalchemy import create_engine, desc

from idetect.classifier import classify
from idetect.model import db_url, Base, Analysis, Session, Status, Document, DocumentType
from idetect.scraper import scrape

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Flask(__name__,
            static_folder="/home/idetect/web/static",
            template_folder="/home/idetect/web/templates")

engine = create_engine(db_url())
Session.configure(bind=engine)
Base.metadata.create_all(engine)


@app.route('/')
def homepage():
    session = Session()
    articles = session.query(Analysis).order_by(desc(Analysis.updated)).limit(10).all()
    counts = Analysis.status_counts(session)
    return render_template('index.html', articles=articles, counts=counts)


@app.route('/add_url', methods=['POST'])
def add_url():
    url = request.form['url']
    logger.info("Scraping by url: {url}".format(url=url))
    if url is None:
        return redirect(url_for('/'))
    article = Document(url=url, name="New Document", type=DocumentType.WEB)
    session = Session()
    session.add(article)
    session.commit()
    return render_template('success.html', endpoint='add_url', article=article)

if __name__ == "__main__":
    # Start flask app
    app.run(host='0.0.0.0', port=5001, debug=True, threaded=True)
