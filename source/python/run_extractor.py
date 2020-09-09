import click

from idetect.configs import Command
from idetect.fact_extractor import extract_facts
from idetect.load_data import load_countries, load_terms
from idetect.model import Session, Status, Analysis, Country, FactKeyword


@click.command()
@click.option('--single-run', is_flag=True, help='non indefinitely mode (Only process current data)')
def run(single_run):
    command = Command(
        __file__,
        [
            lambda query: query.filter(Analysis.status == Status.CLASSIFIED),
            Status.EXTRACTING, Status.EXTRACTED, Status.EXTRACTING_FAILED,
            extract_facts
        ],
    )

    # Check necessary data exists prior to fact extraction
    session = Session()
    # Load the Countries data if necessary
    countries = session.query(Country).all()
    if len(countries) == 0:
        load_countries(session)

    # Load the Keywords if neccessary
    keywords = session.query(FactKeyword).all()
    if len(keywords) == 0:
        load_terms(session)
    session.close()

    command.run(is_single_run=single_run)


if __name__ == '__main__':
    run()
