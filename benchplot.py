#! /usr/bin/python3

"""
Extract times from results csv files, and generate plots according to the given
parameters.

Author        Dimitar Misev
"""

from matplotlib import pyplot as plt
import matplotlib
import math
import argparse
import csv
import sys
import re

COLORS = ['black', 'red', 'gold', 'green', 'blue', 'magenta',
          'cyan', 'gray', 'darkorange', 'navy', 'violet', 'lime', 'pink']

# columns specification
# [(all|time|memory|cpu)[:(mean|median|min)]]
COL_ALL = 'all'
COL_TIME = 'time'
COL_MEMORY = 'memory'
COL_CPU = 'cpu'
COL_MEAN = 'mean'
COL_MEDIAN = 'median'
COL_MIN = 'min'
COL_STDDEV = 'stddev'

COL_BENCHMARK_NAME_OFFSET = 0
COL_TIME_OFFSET = 1
COL_MEMORY_OFFSET = 5
COL_CPU_OFFSET = 9

HAS_STDDEV = False
NUM_STATS = 3

OFFSET_STATS = {COL_MEAN: 0, COL_MEDIAN: 1, COL_MIN: 2, COL_STDDEV: 3}
OFFSET_MEASUREMENTS = {COL_ALL: 0, COL_TIME: 0, COL_MEMORY: 1, COL_CPU: 2}


def exit_with_error(msg):
    print >> sys.stderr, msg
    sys.exit(1)


class PlotLine:
    """
    A line on a plot has data values, label of y axis, and tick labels on x axis
    """
    def __init__(self, ylabel):
        self.data = []
        self.stddev = []
        self.ylabel = ylabel
        self.isMean = "mean" in self.ylabel.lower()
        self.xtick_labels = []

    def append(self, data_value, xtick_label, stddev_value=None):
        self.data.append(data_value)
        if "." in xtick_label:
            xtick_label = xtick_label[:xtick_label.rfind(".")]
        xtick_label = re.sub(r'^0+', '', xtick_label) # remove leading zeros
        self.xtick_labels.append(xtick_label)
        if stddev_value is not None:
            self.stddev.append(stddev_value)


class ColSpec:
    """
    A column is some combination of (all|time|memory|cpu) and (mean|median|min)
    """
    VALID_MEASUREMENTS = [COL_TIME, COL_MEMORY, COL_CPU]
    VALID_STATS = [COL_MEAN, COL_MEDIAN, COL_MIN]

    def __init__(self, measurement, stat):
        if measurement not in self.VALID_MEASUREMENTS and measurement != COL_ALL:
            exit_with_error("Invalid measurement '" + str(measurement) + "', \
                             expected one of all, time, memory, or cpu.")
        if stat not in self.VALID_STATS:
            exit_with_error("Invalid statistic '" + str(stat) + "', expected one \
                             of mean, median, or min.")
        self.measurement = measurement
        self.stat = stat

    def get_index(self):
        measurement_offset = 1 + NUM_STATS * OFFSET_MEASUREMENTS[self.measurement]
        return measurement_offset + OFFSET_STATS[self.stat]


def get_csv_fields(csv_file, col_specs):
    """
    Get the data in columns indicated by the column specifications
    """
    global NUM_STATS
    global HAS_STDDEV
    plotlines = None
    with open(csv_file) as f_obj:
        reader = csv.reader(f_obj, delimiter=',', skipinitialspace=True)
        header = None
        for row in reader:
            if len(row) == 0:
                continue

            if plotlines is None:
                # handle header row (first iteration only)
                header = row
                for col_header in header:
                    if COL_STDDEV in col_header.lower():
                        NUM_STATS = 4
                        HAS_STDDEV = True
                        break
                plotlines = []
                for col in col_specs:
                    ylabel = row[col.get_index()]
                    tmp = ylabel.lower()
                    if col.measurement not in tmp or col.stat not in tmp:
                        exit_with_error("Corrupt csv file '" + csv_file + "'? "
                                        "Invalid column header '" + ylabel + "'.")

                    plotlines.append(PlotLine(ylabel))
                continue

            xtick_label = row[COL_BENCHMARK_NAME_OFFSET]
            for (col, plotline) in zip(col_specs, plotlines):
                if row[col.get_index()] == "":
                    continue
                data_value = float(row[col.get_index()])
                stddev_value = None
                if plotline.isMean:
                    stddev_ind = col.get_index() + OFFSET_STATS[COL_STDDEV]
                    if stddev_ind < len(row) and HAS_STDDEV:
                        stddev_value = float(row[stddev_ind])
                plotline.append(data_value, xtick_label, stddev_value)

    return plotlines


def percentile(values, percent):
    """
    Find the percentile of a list of values.
    Code adapted from https://stackoverflow.com/a/2753343
    @parameter values - is a list of values.
    @parameter percent - a float value from 0.0 to 1.0.
    @return - the percentile of the values
    """
    if not values:
        return None
    values.sort()
    k = (len(values)-1) * percent
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return values[int(k)]
    d0 = values[int(f)] * (c-k)
    d1 = values[int(c)] * (k-f)
    return d0+d1


def plot_data(files, col_specs, data_labels, xlabel, ylabel, title,
              xtick_labels, out_file, legend_title, xtick_legend, chart_type,
              yscale):
    """
    Generate plot.
    """
    fontname = "cmr10"
    fontsize = 22
    fontsize_axis = 18
    fontsize_legend = 16
    fontsize_ticks = 14
    font = {'family': fontname, 'size': fontsize_legend}
    matplotlib.rc('font', **font)

    def correct_font(x, fontsize=fontsize):
        x.set_fontsize(fontsize)
        x.set_fontname(fontname)

    def fix_underscores(s, r=' '):
        return s.replace('_', r)

    # load data into alldata
    all_plotlines = None
    subplot_count = 1
    for f in files:
        plotlines = get_csv_fields(f, col_specs)
        if all_plotlines is None:
            all_plotlines = [[plotline] for plotline in plotlines]
            subplot_count = len(plotlines)
            if xtick_labels is None:
                xtick_labels = plotlines[0].xtick_labels
            if ylabel is None:
                ylabel = plotlines[0].ylabel
        else:
            for (data, plotline) in zip(all_plotlines, plotlines):
                data.append(plotline)

    # plot data
    n = len(data_labels)
    nrows = 6
    if subplot_count == 2:
        nrows = 8
    elif subplot_count == 3:
        nrows = 10
    ncols = max(8, len(xtick_labels)/1.5)
    plt.figure(figsize=(ncols, nrows))
    ax = None
    curr_ax = None
    for i in range(subplot_count):
        if ax is None:
            ax = plt.subplot(subplot_count, 1, i + 1)
            curr_ax = ax
        else:
            curr_ax = plt.subplot(subplot_count, 1, i + 1, sharex=ax)

        plotlines = all_plotlines[i]

        bar_width = 0.8 / n
        bar_offset = 0 - (n - 1) * (bar_width / 2)

        for (p, label, color) in zip(plotlines, data_labels, COLORS):
            stddev = None
            if len(p.stddev) > 0:
                stddev = p.stddev
            if chart_type == "bar":
                ind = [x+bar_offset for x in range(len(xtick_labels))]
                plt.bar(ind, p.data, bar_width, label=label, yerr=stddev)
            else:
                plt.errorbar(range(len(xtick_labels)), p.data, stddev, label=label,
                             marker='.', lw=1.0, markersize=9, color=color,
                             linestyle='-')
            bar_offset += bar_width

            if subplot_count == 1:
                correct_font(plt.ylabel(p.ylabel), fontsize_axis)
            else:
                correct_font(curr_ax.set_title(p.ylabel), fontsize_axis)

            if chart_type == "bar":
                plt.grid(True, axis="y", alpha=0.4)
            else:
                plt.grid(True)

        for tick in curr_ax.yaxis.get_major_ticks():
            correct_font(tick.label, fontsize_ticks)

        if i < subplot_count - 1:
            # make these tick labels invisible
            plt.setp(curr_ax.get_xticklabels(), visible=False)

    if yscale == "symlog":
        alldata = []
        for plotlines in all_plotlines:
            for p in plotlines:
                alldata.extend(p.data)
        perc = percentile(alldata, 0.8)
        ax.set_yscale(yscale, linthreshy=perc)
        ax.axhline(perc, linewidth=1, alpha=0.4)
        ax.set_yticks([perc], minor=True)
        ax.set_yticklabels(["log $\\uparrow$\n" + str(perc) + "\nlin $\\downarrow$"], minor=True, fontsize=fontsize_ticks)
    else:
        ax.set_yscale(yscale)

    # set labels, title and legend
    correct_font(plt.xlabel(xlabel), fontsize_axis)
    if title:
        correct_font(plt.suptitle(fix_underscores(title)))
    if xtick_legend:
        xtick_legend = xtick_legend.replace(";", "\n")
        plt.figtext(0.93, 0.12, xtick_legend, fontsize=fontsize_ticks-2, family="monospace",
            bbox={"facecolor":"orange", "alpha":0.5, "pad":5})

    legend_colls = 2 if len(files) > 4 else 1
    ax.legend(loc='best', ncol=legend_colls, title=legend_title,
              fontsize=fontsize_legend)

    max_xtick_label_len = 0
    for lbl in xtick_labels:
        max_xtick_label_len = max(max_xtick_label_len, len(lbl))
    rotation = 0
    if max_xtick_label_len > 20:
        rotation = 80
    elif max_xtick_label_len > 15:
        rotation = 75
    elif max_xtick_label_len > 10:
        rotation = 70
    elif max_xtick_label_len > 5:
        rotation = 65
    plt.xticks(range(len(xtick_labels)), xtick_labels, rotation=rotation)

    # plt.tight_layout()
    if out_file:
        plt.savefig(out_file, bbox_inches='tight')
    else:
        plt.show()


def get_argument_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--files",
        help="comma-separated list of CSV files, e.g. file1,file2,...")
    parser.add_argument("--columns",
        help="specification of the data columns to be extracted from each file \
              as comma-separated values of the format \
              [(all|time|memory|cpu)[:(mean|median|min)]]. By default the first \
              part is 'all' and the second is 'mean'.",
        default="all:mean")
    parser.add_argument("--data-labels",
        help="manually list the labels for the legend, separated by ','.",
        default=None)
    parser.add_argument("--xlabel",
        help="x axis label.",
        default="Query")
    parser.add_argument("--ylabel",
        help="y axis label.",
        default=None)
    parser.add_argument("--yscale",
        help="y axis scale (linear | log | logit | symlog).",
        default="linear")
    parser.add_argument("--xtick-labels",
        help="custom tick labels for the X axis, comma-separated.",
        default=None)
    parser.add_argument("--xtick-legend",
        help="legend for the X axis ticks, as ';' separated strings.")
    parser.add_argument("--title",
        help="plot title.",
        default="Benchmark")
    parser.add_argument("--legend-title",
        help="legend title.")
    parser.add_argument("--chart-type",
        help="specify the chart type (line|bar).",
        default="line")
    parser.add_argument("-o", "--outfile",
        help="file name for saving the plot.",
        default="plot.png")
    return parser


def check_args(args):
    if not args.files:
        exit_with_error("Please specify the benchmark result files.")
    if args.chart_type and args.chart_type != "line" and args.chart_type != "bar":
        exit_with_error("Invalid chart type specified, expected 'line' or 'bar'.")
    ys = args.yscale
    if ys and ys != "linear" and ys != "log" and ys != "logit" and ys != "symlog":
        exit_with_error("Invalid y-axis scale specified, expected linear, log, \
            logit, or symlog.")


def get_list_arg(arg):
    return arg.split(",") if arg else None


def parse_column_specs(columns_arg):
    columns = get_list_arg(columns_arg)
    ret = []
    for column in columns:
        if ":" in column:
            tmp = column.split(":")
            ret.append(ColSpec(tmp[0], tmp[1]))
        else:
            ret.append(ColSpec(column, COL_MEAN))
        if ret[-1].measurement == COL_ALL and len(columns) > 1:
            exit_with_error("Only one column can be specified with --columns \
                             when using 'all'.")
    if ret[-1].measurement == COL_ALL:
        # replace 'all' with all valid measurements
        col = ret[-1]
        ret = [ColSpec(m, col.stat) for m in ColSpec.VALID_MEASUREMENTS]
    return ret

if __name__ == "__main__":
    parser = get_argument_parser()
    args = parser.parse_args()
    check_args(args)

    plot_data(get_list_arg(args.files),
              parse_column_specs(args.columns),
              get_list_arg(args.data_labels),
              args.xlabel,
              args.ylabel,
              args.title,
              get_list_arg(args.xtick_labels),
              args.outfile,
              args.legend_title,
              args.xtick_legend,
              args.chart_type,
              args.yscale)
