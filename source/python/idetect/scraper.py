import newspaper
import urllib
from urllib import request
from urllib.parse import urlparse
import textract
import os
import datetime
from bs4 import BeautifulSoup
import re
from sqlalchemy.orm import object_session
from idetect.model import Content
from tempfile import NamedTemporaryFile


def scrape_article(article):
    session = object_session(article)
    # Update the retrieval date and retrieval_attempts
    article.retrieval_date = datetime.datetime.now()
    article.retrieval_attempts += 1
    session.commit()
    # Attempt to scrape article
    scrape(article, session)


def scrape(article, session, scrape_pdfs=True):
    """
    Scrapes content and metadata from an url
    Parameters
    ----------
    article: the article object to be scraped
    session: the article session
    scrape_pdfs: determines whether pdf files will be scraped or not
                 default: True

    """
    pdf_check = is_pdf_consolidated_test(article.url)
    if pdf_check and scrape_pdfs:
        pdf_article(pdf_check, article, session)
    elif not pdf_check:
        html_article(article, session)
    else:
        pass


# PDF helper functions


def is_pdf_simple_tests(url):
    '''Test a url to see if it is a pdf by looking at url and content headers
    If so, return the relevant pdf url for parsing
    '''
    # Simple url-based test
    if re.search(r'\.pdf$', url):
        return url

    # Test based on headers
    page = request.urlopen(url)
    content_type = page.getheader('Content-Type')
    if content_type == 'application/pdf':
        return url


def is_pdf_iframe_test(url):
    '''Test a url to see if the page contains an iframe
    and if the iframe content is pdf or not; if True, return the pdf url
    '''
    page = request.urlopen(url)
    soup = BeautifulSoup(page, "html.parser")
    iframes = soup.find_all('iframe')
    if len(iframes) > 0:
        for frame in iframes:
            if 'src' in frame.attrs.keys():
                src = frame.attrs['src']
                # should probably replace with something more robust
                if 'http' in src:
                    if is_pdf_simple_tests(src):
                        return src


def is_pdf_consolidated_test(url):
    '''Run a series of tests to determine if it is a pdf
    If True, return the relevant url
    '''

    # Carry out simple tests based upon url and content type
    pdf_attempt_1 = is_pdf_simple_tests(url)
    if pdf_attempt_1:
        return pdf_attempt_1

    # Carry out additional test based by looking for iframe
    pdf_attempt_2 = is_pdf_iframe_test(url)
    if pdf_attempt_2:
        return pdf_attempt_2

    return False


def remove_newline(text):
    ''' Removes new line and &nbsp characters.
    '''
    text = text.replace('\n', ' ')
    text = text.replace('\xa0', ' ')
    return text


def format_date(date_string):
    '''Formats date string from http headers
    Returns standardized date format as string
    '''
    try:
        dt = datetime.datetime.strptime(
            date_string, "%a, %d %b %Y %H:%M:%S %Z")
        formatted_date = dt.strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError, AttributeError):
        formatted_date = None
    return formatted_date


def html_article(article, session):
    """Downloads and extracts content plus metadata for html page
    Parameters
    ----------
    article: article object to be scraped
    session: the article session

    Returns
    -------
    article: The updated article object
    """

    a = newspaper.Article(article.url)
    a.download()
    if a.download_state == 2:
        a.parse()
        article.domain = a.source_url
        article.title = a.title
        article.authors = a.authors
        article.publication_date = a.publish_date

        content = Content(article=[article],
                          content=remove_newline(a.text), content_type='text')
        session.add(content)
        session.commit()

        return article
    else:  # Temporary fix to deal with https://github.com/codelucas/newspaper/issues/280
        raise Exception("Retrieval Failed")


def get_pdf(url):
    ''' Takes a pdf url, downloads it and saves it locally.'''
    pdf_file = NamedTemporaryFile( suffix=".pdf", prefix="tmp_", delete=False )
    response = request.urlopen(url)  # not sure if this is needed?
    publish_date = response.getheader('Last-Modified')
    #pdf_file = open(ntf, 'wb')
    pdf_file.write(response.read())
    pdf_file.close()
    return os.path.join('./', pdf_file.name), publish_date


def get_body_text(url):
    ''' This function will extract all text from the url passed in
    '''
    filepath, publish_date = get_pdf(url)
    print(filepath)
    if filepath == '':
        return '', None
    else:
        try:
            text = str(textract.process(filepath, method='pdfminer'), 'utf-8')
            text = text.replace('\n', ' ')  # can replace with a call to
            text = text.replace('\xa0', ' ')  # the helper function.
            publish_date = format_date(publish_date)
            os.unlink(filepath)
            return text, publish_date
        except:
            os.unlink(filepath)
            raise Exception("PDF2Text Failed")


def pdf_article(url, article, session):
    article_text, article_pub_date = get_body_text(url)
    if article_text == '':
        raise Exception("Retrieval Failed")
    else:
        article.domain = urlparse(url).hostname
        article.publication_date = article_pub_date

        article_content_type = 'pdf'
        # improve parsing of pdfs to extract these?
        content = Content(article=[article],
                          content=article_text, content_type='pdf')
        session.add(content)
        session.commit()
