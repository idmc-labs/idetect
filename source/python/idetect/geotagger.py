'''Method(s) for getting geo info.
'''
import unicodedata

import pycountry
from itertools import groupby
from idetect.model import LocationType, Fact
from idetect.geo_external import nominatim_coordinates, GeotagException
from sqlalchemy.orm import object_session


def process_locations(analysis):
    '''Geotag locations for a given article
    :params analysis: instance of Analysis
    :return: None
    '''
    session = object_session(analysis)
    facts = analysis.facts
    for fact in facts:
        if len(fact.locations) > 0:
            process_fact(fact, analysis, session)


def process_fact(fact, analysis, session):
    '''Geotag locations for a given fact
    If the locations represent multiple countries, duplicate
    the fact for each country
    :params fact: instance of Fact
    :params analysis: instance of Analysis
    :params session: object session for Analysis
    :return: None
    '''
    for location in fact.locations:
        if location.country == '' or location.country is None:
            process_location(location, session)

    country_locations = fact.locations
    country_locations.sort(key=lambda x: x.country.iso3)
    country_groups = [(key, [loc for loc in group]) for key, group in groupby(country_locations, lambda x: x.country.iso3)]
    # If all locations from same country
    # Update the Fact iso3 field, then done
    if len(country_groups) == 1:
        fact.iso3 = country_groups[0][0]
        session.commit()
    else:
        # Empty the fact locations
        fact.locations = []
        # Update the iso3 and locations for original fact
        fact.iso3 = country_groups[0][0]
        fact.locations = [location for location in country_groups[0][1]]
        # Duplicate the fact for the remaining countries
        for key, group in country_groups[1:]:
            f = Fact(unit=fact.unit, term=fact.term,
                excerpt_start=fact.excerpt_start, excerpt_end=fact.excerpt_end,
                specific_reported_figure=fact.specific_reported_figure,
                vague_reported_figure=fact.vague_reported_figure, iso3=key,
                tag_locations=fact.tag_locations)
            session.add(f)
            analysis.facts.append(f)
            f.locations.extend([location for location in group])
        session.commit()


def process_location(location, session):
    '''Geotag and update given location object
    :params location: instance of Location
    :params session: session object
    :return: None
    '''
    loc_info = get_geo_info(location.location_name)
    location.location_type = loc_info['type']
    location.country_iso3 = loc_info['country_code']
    location.latlong = loc_info['coordinates']
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
    # TODO here we should limit the countries
    country_info = city_subdivision_country(place_name)
    if country_info:
        coords = nominatim_coordinates(place_name, country_info['country_code'])
        country_info['coordinates'] = coords['coordinates']
        country_info['flag'] = coords['flag']
    else:
        country_info = nominatim_coordinates(place_name,'USA')

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
