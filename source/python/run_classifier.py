import click

from idetect.configs import Command
from idetect.classifier import classify
from idetect.model import Status, Analysis

from idetect.nlp_models.category import CategoryModel
from idetect.nlp_models.relevance import RelevanceModel
# NOTE: Throws error is not provided for pickle
from idetect.nlp_models.category import *  # noqa: F403 F401
from idetect.nlp_models.relevance import *  # noqa: F403 F401


@click.command()
@click.option('--single-run', is_flag=True, help='non indefinitely mode (Only process current data)')
def run(single_run):
    c_m = CategoryModel()
    r_m = RelevanceModel()
    Command(
        __file__,
        [
            lambda query: query.filter(Analysis.status == Status.SCRAPED), Status.CLASSIFYING,
            Status.CLASSIFIED, Status.CLASSIFYING_FAILED,
            lambda article: classify(article, c_m, r_m)
        ],
    ).run(is_single_run=single_run)


if __name__ == '__main__':
    run()
