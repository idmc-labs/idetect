FROM ubuntu:latest

ENV DEBIAN_FRONTEND noninteractive

# python basics
RUN apt-get update && \
    apt-get -y install python3 python3-pip python3-dev

## download the spacy model using curl for progress indication
# This is quite large, so we're downloading it early in the build for the sake of caching
RUN apt-get -y install curl && \
    mkdir /spacy-data && \
    curl -L -o "/spacy-data/en_core_web_md-1.2.1.tar.gz" $zflag \
        https://github.com/explosion/spacy-models/releases/download/en_core_web_md-1.2.1/en_core_web_md-1.2.1.tar.gz

RUN apt-get -y install postgresql libpq-dev git

# install the big packages and the ones with complex dependencies
# sklearn version needs to be the same as was used for model creation
RUN pip3 install --upgrade 'pip<10' && \
    pip3 install NumPy==1.13.1 SciPy==0.19.1 spacy==1.9.0 scikit-learn==0.19.0 pandas==0.20.3 nltk==3.2.4 \
    gensim==2.3.0 pdfminer.six==20170720 pycountry==17.5.14

RUN pip3 install "/spacy-data/en_core_web_md-1.2.1.tar.gz" && \
    python3 -m spacy link en_core_web_md en_default

COPY ./source/python/requirements.txt /tmp
RUN pip3 install -r /tmp/requirements.txt

RUN apt-get -y install supervisor && \
    chmod 777 /var/log/supervisor && \
    mkdir /var/log/workers && \
    chmod 777 /var/log/workers

RUN apt-get -y install nginx
COPY ./config/nginx.conf /etc/nginx/nginx.conf
RUN pip install uwsgi
COPY ./config/uwsgi.ini /etc/uwsgi/uwsgi.ini

ARG UID
RUN useradd -ms /bin/bash -u $UID idetect
RUN mkdir -p /var/log/nginx && chown -R idetect /var/log/nginx && \
    mkdir -p /var/lib/nginx && chown -R idetect /var/lib/nginx

USER idetect
WORKDIR /home/idetect
COPY ./source /home/idetect
