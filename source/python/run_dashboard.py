import inspect
import pandas as pd
from bokeh.plotting import figure, curdoc
from bokeh.models import ColumnDataSource
from bokeh.layouts import row, column, widgetbox
from sqlalchemy import create_engine

from idetect.model import db_url, Session, Status, Analysis
from dashboard.plotting import status_plot
from dashboard.plot_data import db_connect, fetch_statuses, fetch_model_categories


def update():
    data = fetch_statuses(session)
    data = data['status'].value_counts()
    status = data.index.values
    values = data.values
    data = dict(status=status, value=values)
    source.data = data


c = curdoc()

Session.configure(bind=db_connect())
session = Session()

source = ColumnDataSource(data=dict(status=[],
                                    value=[]))
status_categories = fetch_model_categories(Status)
plot = status_plot(source, status_categories)

update() # initial load of data and plots

curdoc().add_root(plot)
curdoc().add_periodic_callback(update, 200)
