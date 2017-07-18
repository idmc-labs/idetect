'''Method(s) for getting geo info.
'''
import ast
import unicodedata
from itertools import permutations

import pycountry
import requests
from flask import Blueprint
from flask import jsonify
from flask import request
from idetect import cities_to_countries

geo_api = Blueprint('geo_api', __name__)


@geo_api.route('/geo_info', methods=['GET'])
def geo_info():
    '''This exposes the internal geo tagging functionality.
    In fact extraction, the geo tagging solution can be internal or external.

    :params places_list: A list of place names in the text.
    :return: JSON of geo_info for each place name:
        place_name: original place name provided as param
        country_code: 3-letter ISO country code
        city_name: name of city, if available
        subdivision: name of subdivision (state, district etc), if available
        latlong: String of lat/long coordinates, if available
    '''
    places_list = ast.literal_eval(request.args.get('places_list'))
    hints = places_list.copy()
    output = []
    for p in places_list:
        location_info = {}
        country_info = city_subdivision_country(p)
        if country_info:
            location_info['description'] = p
            location_info['country_code'] = country_info['country_code']
            output.append(location_info)
        else:
            c_info = get_coordinates_mapzen(
                p, use_layers=False, hints=hints)
            country_code = c_info['country_code']
            if country_code != '':
                location_info['description'] = p
                location_info['country_code'] = country_code
                output.append(location_info)
    return jsonify(results = output)


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
    return separator.join(map(str, coords_list))


def common_names(place_name):
    '''Convert countries or places with commonly used names
    to their official names
    '''
    return{
        'Syria': 'Syrian Arab Republic',
        'Bosnia': 'Bosnia and Herzegovina'
    }.get(place_name, place_name)


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


def city_subdivision_country(place_name, hints=[]):
    '''Return dict with city (if applicable), subdivision (if applicable),
        and the ISO-3166 alpha_3 country code for a given place name.
        Return None if the country cannot be identified.
        '''
    place_name = common_names(place_name)
    country_code, country_name = match_country_name(place_name)
    if country_code:
        return {'city': None, 'subdivision': None, 'country_code': country_code, 'country_name': country_name}

    # Try getting the country code using a subdivision name
    country_code, country_name = subdivision_country_code(place_name)
    if country_code:
        return {'city': None, 'subdivision': place_name, 'country_code': country_code, 'country_name': country_name}

    # Try getting the country code using a city name
    country_code = cities_to_countries.get(
        strip_accents(place_name), None)
    if country_code:
        country = pycountry.countries.get(alpha_2=country_code)
        return {'city': place_name, 'subdivision': None,
                'country_code': country.alpha_3, 'country_name': country.name}
    return None


def get_coordinates_mapzen(city=None, subdivision=None, country=None, use_layers=True, hints=[]):
    '''Return geo coordinates by supplying location name
    Parameters
    ----------
    city: string, default None
    subdivision: string, default None
    country: string, default None
    hints: array, default [], other locations mentioned in the text that might
           help identify the proper location 

    Returns
    -------
    coordinates: string of comma separated lat an long
    '''
    if city in hints:
        hints.remove(city)

    api_key = 'mapzen-neNu6xZ'
    base_url = 'https://search.mapzen.com/v1/search'

    # turns all empty entities to none
    place_units = [city, subdivision, country]
    for unit in place_units:
        if unit == '':
            unit == None

    # creates the extra parameter in order to make sure
    # we are looking for the correct type of location
    place_layers = 'locality'
    if city is None:
        place_layers = 'region'
        if subdivision is None:
            place_layers = 'country'

    # creates the text parameter
    place_name = ','.join([p for p in place_units if p is not None])

    # makes a call to mapzen an retrieves the data
    qry = {'text': place_name, 'api_key': api_key}
    if use_layers:
        resp = requests.get(base_url, params={'api_key': api_key,
                                              'text': place_name,
                                              'layers': place_layers})
    else:
        resp = requests.get(base_url, params={'api_key': api_key,
                                              'text': place_name})

    res = resp.json()
    data = res["features"]

    # if there are no results from the call ...
    if len(data) == 0:
        return {u'coordinates': '', u'flag': "no-results", u'country_code': ''}
    # best case - there is just a single result ...
    elif len(data) == 1:
        return {u'coordinates': coords_tostring(data[0]['geometry']['coordinates']),
                u'flag': "single-result", u'country_code': data[0]['properties']['country_a']}
    # most complicated case - there are multiple results
    elif len(data) > 1:
        # if there are hints, ry to make a best guess and
        # and if not - returns the first result in the list
        data_filt = [data]
        if len(hints) > 0:
            layers_mapzen = {0: 'locality', 1: 'region', 2: 'country'}
            hints.append('')
            # creates a new list with indices of all missing items in
            # the places list
            miss_idx = [i for i, v in enumerate(place_units) if v is None]
            # creates a list of all the possible combinations
            combs = list(permutations(hints, len(miss_idx)))
            for comb in combs:
                c = 0
                for i, idx in enumerate(miss_idx):
                    if comb[i] != '':
                        # filters the dictionary based on the different options
                        if c == 0:
                            # if it's a first valid iteration, the data source is
                            # basically the raw dictionary
                            data_filt.append([l for l in data
                                              if layers_mapzen[idx] in l['properties']
                                              and l['properties'][layers_mapzen[idx]] == comb[i]])
                        else:
                            # if it's one of the later tierations, the data source
                            # is the newly created filtered dictionary
                            data_filt[-1] = [l for l in data_filt[-1]
                                             if layers_mapzen[idx] in l['properties']
                                             and l['properties'][layers_mapzen[idx]] == comb[i]]
                        c += 1

            # trying to get the best match (minimum number of results gt zero)
            # creating a list with all the options filtered
            data_filt = [d for d in data_filt if len(d) > 0]
            data_filt = sorted(data_filt, key=lambda k: len(k))
        coords = coords_tostring(data_filt[0][0]['geometry']['coordinates'])
        if 'country_a' in data_filt[0][0]['properties'].keys():
            c_code = data_filt[0][0]['properties']['country_a']
        else:
            c_code = ''
        return {u'coordinates': coords, u'flag': "multiple-results", u'country_code': c_code}
