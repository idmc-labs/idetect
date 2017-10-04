FROM ubuntu:latest

# python basics
RUN apt-get update && \
    apt-get -y install python3 python3-pip python3-dev

## download the spacy model using curl for progress indication
# This is quite large, so we're downloading it early in the build for the sake of caching
RUN apt-get -y install curl && \
    mkdir /spacy-data && \
    curl -L -o "/spacy-data/en_core_web_md-1.2.1.tar.gz" $zflag \
        https://github.com/explosion/spacy-models/releases/download/en_core_web_md-1.2.1/en_core_web_md-1.2.1.tar.gz

# cld2-cffi doesn't install properly after the rest of the packages, for some reason
RUN apt-get -y install libffi-dev && \
    pip3 install cld2-cffi

RUN apt-get -y install postgresql libpq-dev git

# install the big packages and the ones with complex dependencies
# sklearn version needs to be the same as was used for model creation
RUN pip3 install --upgrade pip && \
    pip3 install NumPy SciPy spacy scikit-learn==0.19.0 pandas nltk gensim pdfminer.six pycountry

RUN pip3 install "/spacy-data/en_core_web_md-1.2.1.tar.gz" && \
    python3 -m spacy link en_core_web_md en_default

COPY ./source/python/requirements.txt /tmp
RUN pip3 install -r /tmp/requirements.txt

RUN apt-get -y install supervisor && \
    chmod 777 /var/log/supervisor && \
    mkdir /var/log/workers && \
    chmod 777 /var/log/workers

RUN useradd -ms /bin/bash -u 1001 idetect
USER idetect
WORKDIR /home/idetect
COPY ./source /home/idetect
COPY ./config/supervisord.conf /etc/supervisord.conf
