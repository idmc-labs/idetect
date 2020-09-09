FROM ubuntu:18.04

ENV DEBIAN_FRONTEND noninteractive
ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8

# python basics
RUN apt-get clean \
    && apt-get update \
    && apt-get -y install \
        python3.6 python3-pip python3-dev \
    && apt-get -y --no-install-recommends install \
        curl \
        postgresql libpq-dev git \
        supervisor \
        nginx \
    ## download the spacy model using curl for progress indication
    # This is quite large, so we're downloading it early in the build for the sake of caching
    && mkdir /spacy-data \
    && curl -L -o "/spacy-data/en_core_web_md-1.2.1.tar.gz" $zflag \
        https://github.com/explosion/spacy-models/releases/download/en_core_web_md-1.2.1/en_core_web_md-1.2.1.tar.gz \
    # install the big packages and the ones with complex dependencies
    # sklearn version needs to be the same as was used for model creation
    && pip3 install --no-cache-dir --upgrade 'pip<10' \
    && pip3 install --no-cache-dir \
        NumPy==1.13.1 \
        SciPy==0.19.1 spacy==1.9.0 scikit-learn==0.19.0 pandas==0.20.3 nltk==3.2.4 \
        gensim==2.3.0 pdfminer.six==20170720 pycountry==17.5.14 \
        uwsgi \
    && pip3 install --no-cache-dir "/spacy-data/en_core_web_md-1.2.1.tar.gz" \
    && python3 -m spacy link en_core_web_md en_default \
    # Cleanup
    && rm -rf /spacy-data/ \
    && rm -rf /var/lib/apt/lists/*

COPY ./source/python/requirements.txt /tmp
RUN pip3 install --no-cache-dir -r /tmp/requirements.txt

ARG UID
# Make sure all containers have save UID
RUN useradd -ms /bin/bash -u ${UID:-1001} idetect

RUN chmod 777 /var/log/supervisor \
    && mkdir /var/log/workers \
    && chmod 777 /var/log/workers \
    && mkdir -p /var/log/nginx && chown -R idetect /var/log/nginx \
    && mkdir -p /var/lib/nginx && chown -R idetect /var/lib/nginx

COPY ./config/nginx.conf /etc/nginx/nginx.conf
COPY ./config/uwsgi.ini /etc/uwsgi/uwsgi.ini
# NOTE: This configs are used when starting containers
COPY ./config/api-supervisord.conf \
    ./config/worker-supervisord.conf \
    ./config/crontab \
    /idetect-configs/

USER idetect
WORKDIR /home/idetect
COPY --chown=idetect ./source /home/idetect
