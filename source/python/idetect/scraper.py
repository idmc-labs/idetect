import datetime
import os
import re
from io import StringIO
from tempfile import NamedTemporaryFile
from urllib.parse import urlparse

import newspaper
import requests
from bs4 import BeautifulSoup
from pdfminer.converter import TextConverter
from pdfminer.layout import LAParams
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.pdfpage import PDFPage
from sqlalchemy.orm import object_session
from langdetect import detect

from idetect.model import DocumentContent


def scrape(analysis, scrape_pdfs=True):
    """
    Scrapes content and metadata from an url
    Parameters
    ----------
    analysis: the anlysis object to be scraped
    scrape_pdfs: determines whether pdf files will be scraped or not
                 default: True

    """

    # Update the retrieval date and retrieval_attempts
    analysis.retrieval_date = datetime.datetime.now()
    analysis.retrieval_attempts += 1
    session = object_session(analysis)
    session.commit()
    if scrape_pdfs:
        pdf_url = get_pdf_url(analysis.document.url)
        if pdf_url:
            return scrape_pdf(pdf_url, analysis)
    return scrape_html(analysis)


def get_pdf_url_simple(url):
    '''Test a url to see if it is a pdf by looking at url and content headers
    If so, return the relevant pdf url for parsing
    '''
    # Simple url-based test
    if url.endswith('.pdf'):
        return url

    # Test based on headers
    if requests.head(url).headers.get('Content-Type') == 'application/pdf':
        return url

    return None


def get_pdf_url_iframe(url):
    '''Test a url to see if the page contains an iframe
    and if the iframe content is pdf or not; if True, return the pdf url
    '''
    content = requests.get(url).content
    soup = BeautifulSoup(content, "html.parser")
    for frame in soup.find_all('iframe'):
        src = frame.attrs.get('src', '')
        if 'http' in src:
            if get_pdf_url_simple(src):
                return src
    return None


def get_pdf_url(url):
    '''Run a series of tests to determine if it is a pdf
    If True, return the relevant url
    '''
    return get_pdf_url_simple(url) or get_pdf_url_iframe(url)


def scrape_html(analysis):
    """Downloads and extracts content plus metadata for html page
    Parameters
    ----------
    analysis: analysis object to be scraped
    session: the analysis session

    Returns
    -------
    analysis: The updated analysis object
    """

    a = newspaper.Article(analysis.document.url)
    a.download()
    if a.download_state == 2:
        a.parse()
        analysis.title = a.title
        analysis.authors = a.authors
        analysis.publication_date = a.publish_date

        text = re.sub('\s+', ' ', a.text)  # collapse all whitespace
        analysis.language = detect(text)
        content = DocumentContent(analysis=[analysis], content=text, content_type='text')
        session = object_session(analysis)
        session.add(content)
        session.commit()
        return analysis
    else:  # Temporary fix to deal with https://github.com/codelucas/newspaper/issues/280
        raise Exception("Retrieval Failed")


def download_pdf(url):
    ''' Takes a pdf url, downloads it and saves it locally. Returns the filename and the last-modified date'''
    with NamedTemporaryFile(suffix=".pdf", prefix="tmp_", delete=False) as pdf_file:
        r = requests.get(url, stream=True)
        pdf_file.writelines(r.iter_content(1024))
        return pdf_file.name, r.headers['Last-Modified']


def extract_pdf_text(pdf_file_path, codec='utf-8'):
    with open(pdf_file_path, 'rb') as fh:
        with StringIO() as extracted:
            resource_manager = PDFResourceManager()
            device = TextConverter(resource_manager, extracted, codec=codec, laparams=LAParams())
            interpreter = PDFPageInterpreter(resource_manager, device)
            for page in PDFPage.get_pages(fh, pagenos=set(), maxpages=0, caching=True, check_extractable=True):
                interpreter.process_page(page)
            device.close()
            response = extracted.getvalue()
    return response


def scrape_pdf(url, analysis):
    pdf_file_path, last_modified = download_pdf(url)
    try:
        text = extract_pdf_text(pdf_file_path)
        if not text:
            raise Exception("No text extracted from PDF at {}".format(url))
        text = re.sub('\s+', ' ', text)  # collapse all whitespace
        analysis.domain = urlparse(url).hostname
        analysis.publication_date = last_modified
        analysis.language = detect(text)
        content = DocumentContent(analysis=[analysis], content=text, content_type='pdf')
        session = object_session(analysis)
        session.add(content)
        session.commit()
        return analysis
    finally:
        os.unlink(pdf_file_path)
