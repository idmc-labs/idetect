import requests
from idetect.model import LocationType

class GeotagException(Exception):
    pass


def coords_tostring(long_lat_floats):
    longitude, latitude = long_lat_floats
    return "{},{}".format(latitude, longitude)


def mapzen_coordinates(place_name, country_code=None):
    api_key = 'mapzen-i8JEmx7'
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
        raise GeotagException()


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
