import click

from idetect.configs import Command
from idetect.geotagger import process_locations
from idetect.model import Status, Analysis


@click.command()
@click.option('--single-run', is_flag=True, help='non indefinitely mode (Only process current data)')
def run(single_run):
    Command(
        __file__,
        [
            lambda query: query.filter(Analysis.status == Status.EXTRACTED),
            Status.GEOTAGGING, Status.GEOTAGGED, Status.GEOTAGGING_FAILED,
            process_locations
        ],
    ).run(is_single_run=single_run)


if __name__ == '__main__':
    run()
