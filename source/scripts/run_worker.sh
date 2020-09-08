#!/bin/bash -xe

cd /home/idetect/python

python3 run_initiator.py --single-run
python3 run_scraper.py --single-run
python3 run_classifier.py --single-run
python3 run_extractor.py --single-run
python3 run_geotagger.py --single-run
