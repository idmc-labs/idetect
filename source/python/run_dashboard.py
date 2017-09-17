from idetect.model import db_url, Session, Status

import inspect
import pandas as pd
from bokeh.plotting import figure, curdoc
from bokeh.models import ColumnDataSource
from bokeh.layouts import row, column, widgetbox
from sqlalchemy import create_engine

def db_connect():
    engine = create_engine(db_url())
    conn = engine.connect()
    return conn, engine


def mysql_query_to_df(query):
    conn, engine = db_connect()
    with engine.connect() as conn, conn.begin():
        df = pd.read_sql(query, conn)
    return df


def update():
    query = 'select status from article'
    data = mysql_query_to_df(query)
    data = data['status'].value_counts()
    status = data.index.values
    values = data.values
    source.data = dict(status=status,
                       value=values)

def get_categories(model):
    attributes = inspect.getmembers(model, lambda a:not(inspect.isroutine(a)))
    attrs = [a[1] for a in attributes if not(a[0].startswith('__') and 
                                             a[0].endswith('__'))]
    return attrs


c = curdoc()

source = ColumnDataSource(data=dict(status=[],
                                    value=[]))

possible_statuses = get_categories(Status)

plot = figure(x_range=possible_statuses)
plot.vbar(x='status', top='value', source=source,
          width=0.9, color='navy')

update() # initial load of data and plots

curdoc().add_root(plot)
