#! /usr/bin/python3

"""
Extract times from results csv files, and generate plots according to the given
parameters.

Author        Dimitar Misev
"""

from matplotlib import pyplot as plt
import matplotlib
import argparse
import csv
import sys

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
            xtick_label = xtick_label[:xtick_label.find(".")]
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
                if len(row[col.get_index()]) == 0:
                    continue
                data_value = float(row[col.get_index()])
                stddev_value = None
                if plotline.isMean:
                    stddev_ind = col.get_index() + OFFSET_STATS[COL_STDDEV]
                    if stddev_ind < len(row) and HAS_STDDEV:
                        stddev_value = float(row[stddev_ind])
                plotline.append(data_value, xtick_label, stddev_value)

    return plotlines


def plot_data(files, col_specs, data_labels, xlabel, ylabel, title,
              xtick_labels, out_file, legend_title, xtick_legend):
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
    nrows = 6
    if subplot_count == 2:
        nrows = 8
    elif subplot_count == 3:
        nrows = 10
    plt.figure(figsize=(8, nrows))
    ax = None
    curr_ax = None
    for i in range(subplot_count):
        if ax is None:
            ax = plt.subplot(subplot_count, 1, i + 1)
            curr_ax = ax
        else:
            curr_ax = plt.subplot(subplot_count, 1, i + 1, sharex=ax)

        plotlines = all_plotlines[i]
        for (p, label, color) in zip(plotlines, data_labels, COLORS):
            stddev = None
            if len(p.stddev) > 0:
                stddev = p.stddev
            plt.errorbar(range(len(xtick_labels)), p.data, stddev, label=label,
                         marker='.', lw=1.0, markersize=9, color=color,
                         linestyle='-')

            if subplot_count == 1:
                correct_font(plt.ylabel(p.ylabel), fontsize_axis)
            else:
                correct_font(curr_ax.set_title(p.ylabel), fontsize_axis)
            plt.grid(True)

        for tick in curr_ax.yaxis.get_major_ticks():
            correct_font(tick.label, fontsize_ticks)

        if i < subplot_count - 1:
            # make these tick labels invisible
            plt.setp(curr_ax.get_xticklabels(), visible=False)

    # set labels, title and legend
    correct_font(plt.xlabel(xlabel), fontsize_axis)
    if title:
        correct_font(plt.suptitle(title))
    if xtick_legend:
        xtick_legend = xtick_legend.replace(";", "\n")
        yoffset = 0.72
        correct_font(plt.figtext(0.04, yoffset, xtick_legend), fontsize_ticks)

    legend_colls = 2 if len(files) > 4 else 1
    ax.legend(loc='best', ncol=legend_colls, title=legend_title,
              fontsize=fontsize_legend)

    plt.xticks(range(len(xtick_labels)), xtick_labels, rotation=70)

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
    parser.add_argument("-o", "--outfile",
        help="file name for saving the plot.",
        default="plot.png")
    return parser


def check_args(args):
    if not args.files:
        exit_with_error("Please specify the benchmark result files.")


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
              args.xtick_legend)
