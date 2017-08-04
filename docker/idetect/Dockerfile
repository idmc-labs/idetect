FROM ubuntu:latest

# python basics
RUN apt-get update && \
    apt-get -y install python3 python3-pip python3-dev

# cld2-cffi doesn't install properly after the rest of the packages, for some reason
RUN apt-get -y install libffi-dev && \
    pip3 install cld2-cffi

# install the big packages and the ones with complex dependencies
RUN apt-get -y install libxslt1-dev antiword unrtf poppler-utils pstotext \
        tesseract-ocr flac ffmpeg lame libmad0 libsox-fmt-mp3 sox libjpeg-dev \
        postgresql libpq-dev git
RUN pip3 install --upgrade pip && \
    pip3 install NumPy SciPy spacy scikit-learn nltk gensim

## download the spacy model using curl for progress indication
## uncomment the below to include it in the build
#RUN apt-get -y install curl && \
#    mkdir /spacy-data && \
#    curl -L -o "/spacy-data/en_core_web_md-1.2.1.tar.gz" $zflag \
#        https://github.com/explosion/spacy-models/releases/download/en_core_web_md-1.2.1/en_core_web_md-1.2.1.tar.gz
#RUN pip3 install "/spacy-data/en_core_web_md-1.2.1.tar.gz" && \
#    python3 -m spacy link en_core_web_md en_default

COPY ./source/python/requirements.txt /tmp
RUN pip3 install -r /tmp/requirements.txt

RUN useradd -ms /bin/bash idetect
USER idetect
WORKDIR /home/idetect
COPY ./source /home/idetect
