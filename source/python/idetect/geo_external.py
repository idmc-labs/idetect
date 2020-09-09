import os
import requests
import pycountry

from idetect.model import LocationType

class GeotagException(Exception):
    pass


def match_iso3(iso2):
    '''Try and match the iso2 with is3
    return the country code if found
    '''
    countries = (c for c in list(pycountry.countries))
    for country in countries:  # Loop through all countries
        if country.alpha_2 == iso2:  # Look directly at iso2
            return country.alpha_3
            break
    return 'XXX'

def nominatim_coordinates(place_name, country_code='XXX'):
    base_url='http://nominatim.openstreetmap.org/search'
    base_params = {'q':place_name,'addressdetails': 1,'format':'json','extratags':1,'accept-language':'en'}
    if country_code != 'XXX':
        try:
            country=pycountry.countries.get(alpha_3=country_code)
            base_params['countrycodes'] = country.alpha_2.lower()
        except:
            pass
    try:
        resp = requests.get(base_url, params=base_params)
        res = resp.json()        
        data = res
        if len(data) == 0:
            return {'place_name': place_name, 'type': '',
                    'country_code': country_code,
                    'flag': 'no-results', 'coordinates': ''}
        else:
            if len(data) > 1:
                flag = "multiple-results"
            else:
                flag = "single-result"
        # in principle this is redundant as the data is already ordered by importance
        data.sort(key=lambda x: x['importance'], reverse=True)

        geo_entity=data[0]
        placetype=LocationType.UNKNOWN
        try:
            placetype = OSM_place_to_entity(geo_entity['extratags']['place'])
        except:
            try:
                placetype = OSM_place_to_entity(geo_entity['type'])
            except:
                try:
                    placetype = OSM_place_to_entity(geo_entity['class'])
                except:
                    pass
        iso2 = geo_entity['address']['country_code'].upper()
        iso3 = match_iso3(iso2)    
        return {
            'place_name': place_name, 'type': placetype,
            'country_code': iso3, 'flag': flag,
            'coordinates': '{},{}'.format(geo_entity['lat'],geo_entity['lon'])
        }
    except:
        raise GeotagException()


def OSM_place_to_entity(place):
    if place in ('address', 'street','locality','building'):
        return LocationType.ADDRESS
    elif place in ('neighbourhood', 'borough', 'localadmin','quarter','city_block','plot','hamlet','isolated_dwelling','farm','allotments'):
        return LocationType.NEIGHBORHOOD
    elif place in ('locality','city','municipality','town',"village"):
        return LocationType.CITY
    elif place in ('county', 'region','province','district','state'):
        return LocationType.SUBDIVISION
    elif place in ('country'):
        return LocationType.COUNTRY
    else:
        return LocationType.UNKNOWN
