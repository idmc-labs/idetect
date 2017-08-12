from flask import Flask, render_template, abort, request, redirect, url_for
from sqlalchemy import create_engine, desc

from idetect.model import db_url, Base, Article, Session, Status
from idetect.classifier import classify
from idetect.scraper import scrape

import logging

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
    articles = session.query(Article).order_by(desc(Article.updated)).limit(10).all()
    counts = Article.status_counts(session)
    return render_template('index.html', articles=articles, counts=counts)

@app.route('/add_url', methods=['POST'])
def add_url():
    url = request.form['url']
    url_id = request.form['url_id']
    logger.info("Scraping by url: {url}".format(url=url))
    if url is None or url_id is None:
        return redirect(url_for('/'))
    article = Article(url=url, url_id=url_id, status=Status.NEW)
    session = Session()
    session.add(article)
    session.commit()
    return render_template('success.html', endpoint='add_url', article=article)

@app.route('/scrape/<int:article_id>', methods=['GET'])
def scrape(article_id):
    logger.info("Scraping by id: {article_id}".format(article_id=article_id))
    article = Session().query(Article).get(article_id)
    if article is None:
        abort(403)
    result = scrape(article.url)
    return render_template('success.html', endpoint='scrape', article=article, result=result)

@app.route('/classify/<int:article_id>', methods=['GET'])
def classify(article_id):
    article = Session().query(Article).get(article_id)
    if article is None:
        abort(404)
    result = classify(article)
    return render_template('success.html', endpoint='classify', article=article, result=result)


if __name__ == "__main__":
    # Start flask app
    app.run(host='0.0.0.0', port=5001, debug=True, threaded=True)
