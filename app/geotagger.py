'''Method(s) for getting geo info.
'''
from flask import Blueprint
import pycountry

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
    pass
    print("Country info")
    return ''
