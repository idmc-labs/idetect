import click
import logging
from datetime import timedelta

from sqlalchemy import func

from idetect.configs import Command
from idetect.model import Status, Analysis
from idetect.scraper import scrape

MAX_RETRIEVAL_ATTEMPTS = 3
HOURS_BETWEEN_ATTEMPTS = 12


logger = logging.getLogger(__name__)


# Filter function for identifying analyses to scrape
def scraping_filter(query):
    # Choose either New analyses OR
    # Analyses where Scraping Failed &
    # less than 3 scraping attempts &
    # last scraping attempt greater than 12 hours ago
    return query.filter(
        (Analysis.status == Status.NEW) |
        (
            (Analysis.status == Status.SCRAPING_FAILED) &
            (Analysis.retrieval_attempts < MAX_RETRIEVAL_ATTEMPTS) &
            (func.now() > Analysis.retrieval_date + timedelta(hours=HOURS_BETWEEN_ATTEMPTS))
        )
    )


@click.command()
@click.option('--single-run', is_flag=True, help='non indefinitely mode (Only process current data)')
def run(single_run):
    Command(
        __file__,
        [scraping_filter, Status.SCRAPING, Status.SCRAPED, Status.SCRAPING_FAILED, scrape],
    ).run(is_single_run=single_run)


if __name__ == '__main__':
    run()
