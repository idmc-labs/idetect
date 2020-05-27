# Sources
- GDELT
- Chrome Extension

# Flow

## run_initiator

- read `Gkgs`: for which there are no `Analysis`
- create `Analysis`
    - sets status as NEW

## run_scraper

- read `Analysis`: NEW or SCRAPING_FAILED (also checks last run time and max attempt)
    - sets status as SCRAPING
    - sets status as SCRAPING_FAILED
    - sets status as SCRAPED
- can scrape pdf and html
    - text language is detected
- create `DocumentContent`
    - text is extracted
    - text is sanitized
- set language in `Analysis`

## run_classifier

- read `Analysis`: SCRAPED
    - sets status as CLASSIFYING
    - sets status as CLASSIFYING_FAILED
    - sets status as CLASSIFIED
- uses `CategoryModel` and `RelevanceModel`
    - loads model from aws s3 (https://s3-us-west-2.amazonaws.com/idmc-idetect/category_models/category.pkl)
    - saves model locally as cache
- set category and relevance in `Analysis`

- run_extractor (facts)
- uses `Interpreter` (need to look into this later)
- read `Analysis`: CLASSIFIED
    - sets status as EXTRACTING
    - sets status as EXTRACTING_FAILED
    - sets status as EXTRACTED
- reads `countries` and `keywords` (may not be used)
    - countries read locally from csv
    - keywords hardcoded
    - written to database
- create `Fact`
    - relate to `Analysis`
    - creates `Location`
        - relate to `Fact`

## run_geotagger

- read `Analysis`: EXTRACTED
    - set status as GEOTAGGING
    - set status as GEOTAGGING_FAILED
    - set status as GEOTAGGED
- if country not set in `Fact`
    - sets locations
        - calls nominatim
- if more than one country in fact, duplicate `Fact`
    - for duplicated facts: separate locations according to country
    - set iso3 on fact

## run_api

- run flask app at 0.0.0.0:5001
