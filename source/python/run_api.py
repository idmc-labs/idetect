import json
import logging
import sys

from flask import Flask, render_template, request, redirect, url_for, jsonify, flash
from sqlalchemy import create_engine, desc, func
import re
import string
import datetime

from idetect.fact_api import get_filter_counts, get_histogram_counts, get_timeline_counts, \
    get_urllist, get_wordcloud, filter_params, get_count, get_group_count, get_map_week, get_urllist_grouped
from idetect.model import db_url, Analysis, Session, Gkg, Status, Base
from idetect.scraper import scrape
from idetect.classifier import classify
from idetect.fact_extractor import extract_facts
from idetect.fact_extractor import extract_facts
from idetect.geotagger import process_locations
from idetect.nlp_models.category import * 
from idetect.nlp_models.relevance import * 
from idetect.nlp_models.base_model import CustomSklLsiModel


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Flask(__name__,
            static_folder="/home/idetect/web/static",
            template_folder="/home/idetect/web/templates")
app.secret_key = 'my unobvious secret key'

engine = create_engine(db_url())
Session.configure(bind=engine)

@app.route('/analyse_url', methods=['GET'])
def analyse_url():    
    session = Session()
    url = request.args.get('url')
    if url is None:
        return json.dumps({'success': False}), 422, {'ContentType': 'application/json'}
    print('getting gkg_id')
    gkg_id= session.query(func.max(Gkg.id)).scalar()
    print('gkg_id:',gkg_id)
    # source_common_name
    scn=re.search('(?<=www.).*?(?=\/)',url).group(0)
    now=datetime.datetime.now()
    gkg_date=('{:04d}{:02d}{:02d}{:02d}{:02d}{:02d}'.format(now.year,now.month,now.day,now.hour,now.minute,now.second))
    print(gkg_date)
    print(scn)
    article = Gkg(document_identifier=url,id=gkg_id+1,date=gkg_date,source_common_name=scn)
    try:
        analysis = Analysis(gkg=article, status=Status.NEW,retrieval_attempts=0)
        session.add(analysis)
        session.commit()
        scrape(analysis)
        analysis.create_new_version(Status.SCRAPED)
        # TODO add classification
        # c_m = CategoryModel()
        # r_m = RelevanceModel()
        # classify(analysis,c_m, r_m)
        analysis.create_new_version(Status.CLASSIFIED)
        extract_facts(analysis)
        analysis.create_new_version(Status.EXTRACTED)
        process_locations(analysis)
        analysis.create_new_version(Status.GEOTAGGED)
    except Exception as e:
        return json.dumps({'success': False, 'Exception':str(e)}), 422, {'ContentType': 'application/json'}
    finally:
        session.close()
    return json.dumps({'success': True}), 200, {'ContentType': 'application/json'}

@app.route('/')
def homepage():
    session = Session()
    try:
        articles = session.query(Analysis).order_by(
            desc(Analysis.updated)).limit(10).all()
        counts = Analysis.status_counts(session)
        cat_counts = Analysis.category_counts(session)
        return render_template('index.html', articles=articles, counts=counts, cat_counts=cat_counts)
    finally:
        session.close()


@app.route('/add_url', methods=['POST'])
def add_url():
    url = request.form['url']
    logger.info("Scraping by url: {url}".format(url=url))
    if url is None:
        flash(u'Something went wrong. Please try again.', 'danger')
        return redirect(url_for('/'))
    article = Gkg(document_identifier=url)
    session = Session()
    try:
        session.add(article)
        session.commit()
        flash(u"{} was successfully added".format(url), 'success')
        return redirect('/')
    finally:
        session.close()


@app.route('/article/<int:doc_id>', methods=['GET'])
def article(doc_id):
    session = Session()
    try:
        analysis = session.query(Analysis) \
            .filter(Analysis.gkg_id == doc_id).one()
        coords = {tuple(l.latlong.split(","))
                  for f in analysis.facts for l in f.locations if l.latlong is not None}
        return render_template('article.html', article=analysis, coords=list(coords))
    finally:
        session.close()


@app.route('/search_url', methods=['GET'])
def search_url():
    url = request.args.get('url')
    if url is None:
        return json.dumps({'success': False}), 422, {'ContentType': 'application/json'}
    session = Session()
    try:
        gkg = session.query(Gkg).filter(
            Gkg.document_identifier.like("%" + url + "%")).order_by(Gkg.date.desc()).first()
        if gkg:
            resp = jsonify({'doc_id': gkg.id})
            resp.status_code = 200
            return resp
        else:
            return json.dumps({'success': False}), 422, {'ContentType': 'application/json'}
    finally:
        session.close()



@app.context_processor
def utility_processor():
    def format_date(dt):
        return dt.strftime("%Y-%m-%d %H:%M")

    return dict(format_date=format_date)


@app.route('/filters', methods=['POST'])
def filters():
    session = Session()
    try:
        data = request.get_json(silent=True) or request.form
        filters = filter_params(data)
        result = get_filter_counts(session, **filters)
        resp = jsonify(result)
        resp.status_code = 200
        return resp
    finally:
        session.close()


@app.route('/timeline', methods=['POST'])
def timeline():
    session = Session()
    try:
        data = request.get_json(silent=True) or request.form
        filters = filter_params(data)
        result = get_timeline_counts(session, **filters)
        resp = jsonify(result)
        resp.status_code = 200
        return resp
    finally:
        session.close()


@app.route('/histogram', methods=['POST'])
def histogram():
    session = Session()
    try:
        data = request.get_json(silent=True) or request.form
        filters = filter_params(data)
        result = get_histogram_counts(session, **filters)
        resp = jsonify(result)
        resp.status_code = 200
        return resp
    finally:
        session.close()


@app.route('/wordcloud', methods=['POST'])
def wordcloud():
    session = Session()
    try:
        data = request.get_json(silent=True) or request.form
        filters = filter_params(data)
        result = get_wordcloud(session, engine, **filters)
        resp = jsonify(result)
        resp.status_code = 200
        return resp
    finally:
        session.close()


@app.route('/urllist', methods=['POST'])
def urllist():
    session = Session()
    try:
        data = request.get_json(silent=True) or request.form
        filters = filter_params(data)
        limit = data.get('limit', 32)
        offset = data.get('offset', 0)
        entries = get_urllist(session, limit=limit, offset=offset, **filters)
        count = get_count(session, **filters)
        resp = jsonify({'entries': entries, 'nentries': count})
        resp.status_code = 200
        return resp
    finally:
        session.close()


@app.route('/urllist_grouped', methods=['POST'])
def urllist_grouped():
    session = Session()
    try:
        data = request.get_json(silent=True) or request.form
        filters = filter_params(data)
        limit = data.get('limit', 32)
        offset = data.get('offset', 0)
        entries = get_urllist_grouped(session, limit=limit, offset=offset, **filters)
        # TODO for url_list grouped count should be the number of groups rather than the number of entries
        factcount = get_count(session, **filters)
        groupcount = get_group_count(session, **filters)
        resp = jsonify({'groups': entries, 'ngroups': groupcount,'tot_nfacts':factcount})
        resp.status_code = 200
        return resp
    finally:
        session.close()


@app.route('/map_week_mview', methods=['GET'])
def map_week_mview():
    session = Session()
    try:
        entries = get_map_week(session)
        resp = jsonify(entries)
        resp.status_code = 200
        return resp
    finally:
        session.close()


if __name__ == "__main__":
    # Start flask app
    app.run(host='0.0.0.0', port=5001, debug=True, threaded=True)
