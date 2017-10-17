'''Method(s) for getting geo info.
'''
import unicodedata

import pycountry
import requests

from idetect.model import LocationType



def save_facts(analysis, facts, session):
    '''Loop through extracted facts and save them to database
    :params article: instance of Article
    :params facts: list of extracted facts
    :params session: session object corresponding to the article
    :return: None
    '''
    for f in facts:
        # First geolocate locations; split into countries and create one fact per country
        country_locations = []
        for location in f.locations:
            country_locations.extend((process_location(location, session)))

        if len(country_locations) > 0:
            country_locations.sort(key=lambda x: x.country.iso3)
            for key, group in groupby(country_locations, lambda x: x.country.iso3):

                fact = Fact(unit=f.reporting_unit, term=f.reporting_term,
                        excerpt_start=f.sentence_start, excerpt_end=f.sentence_end,
                        specific_reported_figure=f.quantity[0],
                        vague_reported_figure=f.quantity[1], iso3=key,
                        tag_locations=json.dumps(f.tag_spans))
                session.add(fact)
                analysis.facts.append(fact)
                fact.locations.extend([location for location in group])
                session.commit()
        else:
            fact = Fact(unit=f.reporting_unit, term=f.reporting_term,
                        excerpt_start=f.sentence_start, excerpt_end=f.sentence_end,
                        specific_reported_figure=f.quantity[0],
                        vague_reported_figure=f.quantity[1], iso3=None,
                        tag_locations=json.dumps(f.tag_spans))
            session.add(fact)
            analysis.facts.append(fact)
            session.commit()



def get_geo_info(place_name):
    '''This exposes the internal geo tagging functionality.
    In fact extraction, the geo tagging solution can be internal or external.

    :params place_name: A place name to get info for
    :return: Dict of geo_info for each place name:
        place_name: original place name provided as param
        country_code: 3-letter ISO country code
        type: type of location: Country, Subdivision, City or Neighberhood
        coordinates: String of lat/long coordinates, if available
        flag: Indicator of number of results encountered
    '''

    country_info = city_subdivision_country(place_name)
    if country_info:
        coords = mapzen_coordinates(place_name, country_info['country_code'])
        country_info['coordinates'] = coords['coordinates']
        country_info['flag'] = coords['flag']
    else:
        country_info = mapzen_coordinates(place_name)

    return country_info


def strip_accents(s):
    '''Strip out accents from text'''
    return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')


def compare_strings(s1, s2):
    '''Compare two strings by first stripping out accents'''
    s1_clean = strip_accents(s1).lower()
    s2_clean = strip_accents(s2).lower()
    return s1_clean == s2_clean


def strip_words(place_name):
    '''Strip out common words that often appear in extracted entities
    '''
    place_name = place_name.lower()
    words_to_replace = {"the": "", "province": "",
                        "county": "", "district": "", "city": "", "township": ""}
    rep = dict((re.escape(k), v) for k, v in words_to_replace.items())
    pattern = re.compile("|".join(rep.keys()))
    place_name = pattern.sub(lambda m: rep[re.escape(m.group(0))], place_name)
    return place_name.strip().title()


def coords_tostring(coords_list, separator=','):
    return separator.join(map(str, coords_list[::-1]))


def subdivision_country_code(place_name):
    '''Try and extract the country code by looking
    at country subdivisions i.e. States, Provinces etc.
    return the country code if found
    '''
    subdivisions = (s for s in list(pycountry.subdivisions))
    for sub_division in subdivisions:
        if compare_strings(sub_division.name, place_name):
            return sub_division.country.alpha_3, sub_division.country.name
            break
    return None, None


def match_country_name(place_name):
    '''Try and match the country name directly
    return the country code if found
    '''
    countries = (c for c in list(pycountry.countries))
    for country in countries:  # Loop through all countries
        if country.name == place_name:  # Look directly at country name
            return country.alpha_3, country.name
            break
        # In some cases the country also has a common name
        elif hasattr(country, 'common_name') and country.common_name == place_name:
            return country.alpha_3, country.common_name
            break
        # In some cases the country also has an official name
        elif hasattr(country, 'official_name') and country.official_name == place_name:
            return country.alpha_3, country.name
            break
    return None, None


def city_subdivision_country(place_name):
    '''Return dict with city (if applicable), subdivision (if applicable),
        and the ISO-3166 alpha_3 country code for a given place name.
        Return None if the country cannot be identified.
        '''
    country_code, country_name = match_country_name(place_name)
    if country_code:
        return {'place_name': place_name, 'country_code': country_code, 'type': 'country'}

    # Try getting the country code using a subdivision name
    country_code, country_name = subdivision_country_code(place_name)
    if country_code:
        return {'place_name': place_name, 'country_code': country_code, 'type': 'subdivision'}

    return None


def mapzen_coordinates(place_name, country_code=None):
    api_key = 'mapzen-neNu6xZ'
    base_url = 'https://search.mapzen.com/v1/search'

    query_params = {'text': place_name, 'api_key': api_key}
    if country_code:
        query_params['boundary.country'] = country_code
    try:
        resp = requests.get(base_url, params=query_params)
        res = resp.json()
        data = res["features"]
        if len(data) == 0:
            return {'place_name': place_name, 'type': '', 'country_code': country_code, 'flag': 'no-results', 'coordinates': ''}
        else:
            if len(data) > 1:
                flag = "multiple-results"
            else:
                flag = "single-result"

            data.sort(key=lambda x: x['properties']['confidence'], reverse=True)
            return {'place_name': place_name, 'type': layer_to_entity(data[0]['properties']['layer']),
                    'country_code': data[0]['properties']['country_a'], 'flag': flag,
                    'coordinates': coords_tostring(data[0]['geometry']['coordinates'])}
    except:
        return {'place_name': place_name, 'type': '', 'country_code': country_code, 'flag': 'no-results', 'coordinates': ''}


def layer_to_entity(layer):
    if layer in ('address', 'street'):
        return LocationType.ADDRESS
    elif layer in ('neighbourhood', 'borough', 'localadmin'):
        return LocationType.NEIGHBORHOOD
    elif layer in ('locality'):
        return LocationType.CITY
    elif layer in ('county', 'region'):
        return LocationType.SUBDIVISION
    elif layer in ('country'):
        return LocationType.COUNTRY
    else:
        return LocationType.UNKNOWN
