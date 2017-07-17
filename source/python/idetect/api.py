from flask import Flask, render_template, abort, request, redirect, url_for
from sqlalchemy import create_engine

from idetect.model import db_url, Base, Article, Session, Status
from idetect.classifier import classify
from idetect.scraper import Scraper

import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Flask(__name__)

engine = create_engine(db_url())
Session.configure(bind=engine)
Base.metadata.create_all(engine)

@app.route('/')
def homepage():
    return render_template('index.html')

@app.route('/add_url', methods=['POST'])
def add_url():
    url = request.form['url']
    logger.info("Scraping by url: {url}".format(url=url))
    if url is None:
        return redirect(url_for('/'))
    article = Article(url=url, status=Status.NEW)
    session = Session()
    session.add(article)
    session.commit()
    result = None # because the below doesn't work
    # result = Scraper().scrape(article.url)
    return render_template('success.html', endpoint='scrape', article=article, result=result)

@app.route('/scrape/<int:article_id>', methods=['GET'])
def scrape(article_id):
    logger.info("Scraping by id: {article_id}".format(article_id=article_id))
    article = Session().query(Article).get(article_id)
    if article is None:
        abort(403)
    result = Scraper().scrape(article.url)
    return render_template('success.html', endpoint='scrape', article=article, result=result)

@app.route('/classify/<int:article_id>', methods=['GET'])
def classify(article_id):
    article = Session().query(Article).get(article_id)
    if article is None:
        abort(404)
    result = classify(article)
    return render_template('success.html', endpoint='classify', article=article, result=result)
