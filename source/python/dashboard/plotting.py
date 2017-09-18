import math
from bokeh.plotting import figure
from bokeh.layouts import column


def status_plot(source, categories):
    # create hover tooltip
    # build plot
    p = figure(x_range=categories, plot_width=450, plot_height=350,
               title='Processing Status')
    p.vbar(x='status', top='value', source=source,
           width=0.9, color='red')
    # plot style formatting
    p.xgrid.grid_line_color = None
    p.ygrid.grid_line_color = None
    p.yaxis.minor_tick_line_color = None
    p.outline_line_width = 1
    p.outline_line_color = 'black'
    p.xaxis.major_label_orientation = math.pi / 4
    p.yaxis.axis_label = 'Count'
    p.title.align = 'center'
    return p
