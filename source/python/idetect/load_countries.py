from idetect.model import Country, CountryTerm, Location, LocationType
import csv


def load_countries(session):

    if len(session.query(Country).all()) == 0:
        with open('/home/idetect/data/all_countries.csv', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                country = Country(code=row['code_3'],
                                  preferred_term=row['country_name'])
                session.add(country)
                session.commit()

                country_name = CountryTerm(
                    term=row['country_name'], country=row['code_3'])
                session.add(country_name)

                if len(row['common_name']) > 0:
                    common_name = CountryTerm(
                        term=row['common_name'], country=row['code_3'])
                    session.add(common_name)

                if len(row['official_name']) > 0:
                    official_name = CountryTerm(
                        term=row['official_name'], country=row['code_3'])
                    session.add(official_name)

                location = Location(description=row['country_name'], location_type=LocationType.COUNTRY,
                                    latlong=row['latlong'], country_code=row['code_3'])
                session.add(location)
                session.commit()
