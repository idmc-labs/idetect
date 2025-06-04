import click

from idetect.configs import Command


@click.command()
@click.option('--single-run', is_flag=True, help='non indefinitely mode (Only process current data)')
def run(single_run):
    Command(__file__, [], is_initiator=True).run(is_single_run=single_run)


if __name__ == '__main__':
    run()
