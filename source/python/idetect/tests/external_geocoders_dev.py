import os
import requests
import pycountry

class LocationType:
    ADDRESS = 'address'
    NEIGHBORHOOD = 'neighborhood'
    CITY = 'city'
    SUBDIVISION = 'subdivision'
    COUNTRY = 'country'
    UNKNOWN = 'unknown'

class GeotagException(Exception):
    pass


def coords_tostring(long_lat_floats):
    longitude, latitude = long_lat_floats
    return "{},{}".format(latitude, longitude)


def mapzen_coordinates(place_name, country_code='XXX'):
    # api_key = os.environ.get('MAPZEN_KEY')
    api_key = 'mapzen-P9waquQ'
    # print("api",api_key)
    base_url = 'https://search.mapzen.com/v1/search'

    query_params = {'text': place_name, 'api_key': api_key}
    if country_code != 'XXX':
        query_params['boundary.country'] = country_code
    try:
        resp = requests.get(base_url, params=query_params)
        res = resp.json()
        # print(res)
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
        raise GeotagException()

def mapbox_coordinates(place_name, country_code='XXX'):
    base_url='https://api.mapbox.com/geocoding/v5/mapbox.places/'+place_name+'.json'
    api_key='thisisnotakey'
    query_params = {'access_token': api_key}
    if country_code != 'XXX':
        try:
            country = pycountry.countries.get(alpha_3=country_code)
            query_params['countrycodes'] = country.alpha_2
        except:
            pass
    try:
        resp = requests.get(base_url,params=query_params)
        res=resp.json()
        data = res["features"]
        if len(data) == 0:
            return {'place_name': place_name, 'type': '', 'country_code': country_code, 'flag': 'no-results', 'coordinates': ''}
        else:
            if len(data) > 1:
                flag = "multiple-results"
            else:
                flag = "single-result"
        #TODO do we need to sort results with mapbox?
        # data.sort(key=lambda x: x['properties']['confidence'], reverse=True)
        # print(data)
        placetype=layer_to_entity(data[0]['place_type'][0])
        if placetype==LocationType.COUNTRY:
            iso2 = data[0]['properties']['short_code'][:2]
        else:
            context=[obj for obj in data[0]['context'] if('country' in obj['id'])]
            iso2 = context[0]['short_code'][:2]
        iso3=pycountry.countries.get(alpha_2=iso2.upper()).alpha_3

        return {'place_name': place_name, 'type': placetype,
                'country_code': iso3, 'flag': flag,
                'coordinates': coords_tostring(data[0]['geometry']['coordinates'])
                }
    except:
        raise GeotagException()

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
        # print(geo_entity)
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
        iso3='XXX'
        iso2=geo_entity['address']['country_code'].upper()
        try:
            iso3 = pycountry.countries.get(alpha_2=iso2).alpha_3
        except:
            pass
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


def layer_to_entity(layer):
    if layer in ('address', 'street',):
        return LocationType.ADDRESS
    elif layer in ('neighbourhood', 'borough', 'localadmin'):
        return LocationType.NEIGHBORHOOD
    elif layer in ('locality','city'):
        return LocationType.CITY
    elif layer in ('county', 'region'):
        return LocationType.SUBDIVISION
    elif layer in ('country'):
        return LocationType.COUNTRY
    else:
        return LocationType.UNKNOWN

locations=[
           ["Bidibidi","XXX"],
        #    ["Torino","XXX"],
        #    ["Torino","USA"],
        #    ["Torino","RRR"],
        #    ["Mosul","XXX"],
        #    ["Mosul","IRQ"],
        #    ["rue d'Ermenonville 7","XXX"],
        #    ["rue d'Ermenonville 7","USA"],
        #    ["San Francisco","XXX"],
        #    ["Vietnam","XXX"],
        #    ["Nigeria","XXX"],
        #    ["North Kivu","XXX"]
           ]
for location in locations:
    print(mapzen_coordinates(location[0],location[1]))
    # print(mapbox_coordinates(location[0],location[1]))
    print(nominatim_coordinates(location[0],location[1]))
    print('')
