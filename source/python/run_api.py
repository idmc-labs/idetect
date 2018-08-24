import json
import logging
import traceback

from flask import Flask, render_template, request, redirect, url_for, jsonify, flash
from sqlalchemy import create_engine, desc, func, asc

from idetect.fact_api import get_filter_counts, get_histogram_counts, get_timeline_counts, \
    get_urllist, get_wordcloud, filter_params, get_count, get_group_count, get_map_week, get_urllist_grouped, \
    create_new_analysis_from_url,work, get_document, get_facts_for_document
from idetect.model import db_url, Analysis, Session, Gkg, Status, Base
from idetect.scraper import scrape
from idetect.classifier import classify
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

c_m = None
def get_c_m():
    global c_m 
    if c_m is None:
        c_m = CategoryModel()
    return c_m

r_m = None
def get_r_m():
    global r_m
    if r_m is None:
        r_m = RelevanceModel()
    return r_m

    
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

@app.route('/analyse_url', methods=['POST'])
def analyse_url():    
    session = Session()
    status=None
    gkg_id=None
    url = request.get_json(silent=True)['url'] or request.form['url']
    if url is None:
        return json.dumps({'success': False}), 422, {'ContentType': 'application/json'}
    gkg = session.query(Gkg.id).filter(
         Gkg.document_identifier.like("%" + url + "%")).order_by(Gkg.date.asc()).first()
    if gkg: 
        gkg_id=gkg.id
        status='url already in DB'
    else:
        analysis=create_new_analysis_from_url(session,url)
        gkg_id=analysis.gkg_id
        status='url added to DB'
        try:
            work(session,analysis,Status.SCRAPING,Status.SCRAPED,Status.SCRAPING_FAILED,scrape)
            # TODO add classification
            # work(session,analysis,Status.CLASSIFYING,Status.CLASSIFIED,Status.CLASSIFYING_FAILED,lambda article: classify(article, get_c_m(), get_r_m()))
            work(session,analysis,Status.EXTRACTING,Status.EXTRACTED,Status.EXTRACTING_FAILED,extract_facts)
            work(session,analysis,Status.GEOTAGGING,Status.GEOTAGGED,Status.GEOTAGGING_FAILED,process_locations)
        except Exception as e:
            print(traceback.format_exc())
            return json.dumps({'success': False, 'Exception':str(e)}), 422, {'ContentType': 'application/json'}
        finally:
            session.close()
    try:
        document=get_document(session, gkg_id)
        entries = get_facts_for_document(session, gkg_id)
        resp = jsonify({'document': document, 'facts': entries, 'status' : status})
        resp.status_code = 200
        return resp
    finally:
        session.close()

if __name__ == "__main__":
    # Start flask app
    app.run(host='0.0.0.0', port=5001, debug=True, threaded=True)
