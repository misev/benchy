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
STDDEV_FIELD_OFFSET = 3


class PlotLine:
    """
    A line on a plot has data values, label of y axis, and tick labels on x axis
    """
    def __init__(self, ylabel):
        self.data = []
        self.stddev = []
        self.ylabel = ylabel
        self.isMean = "mean " in self.ylabel.lower()
        self.xtick_labels = []

    def append(self, data_value, xtick_label, stddev_value=None):
        self.data.append(data_value)
        self.xtick_labels.append(xtick_label)
        if stddev_value is not None:
            self.stddev.append(stddev_value)


def get_csv_fields(csv_file, data_fields):
    """
    Get the data in columns indicated by data_fields indices from a csv_file
    """
    plotlines = None
    with open(csv_file) as f_obj:
        reader = csv.reader(f_obj, delimiter=',', skipinitialspace=True)
        for row in reader:
            if len(row) == 0:
                continue

            if plotlines is None:
                # header row
                plotlines = [PlotLine(row[i]) for i in data_fields]
            else:
                xtick_label = row[0]
                if "." in xtick_label:
                    xtick_label = xtick_label[:xtick_label.find(".")]

                for (data_ind, plotline) in zip(data_fields, plotlines):
                    stddev_value = None
                    if plotline.isMean:
                        stddev_ind = data_ind + STDDEV_FIELD_OFFSET
                        if stddev_ind < len(row):
                            stddev_value = float(row[stddev_ind])
                    plotline.append(float(row[data_ind]), xtick_label, stddev_value)

    return plotlines


def plot_data(files, data_fields, data_labels, xlabel, ylabel, title,
              xtick_labels, out_file, legend_title, xtick_legend):
    """
    Generate plot.
    """
    fontname = "cmr10"
    fontsize = 22
    fontsize_legend = 16
    font = {'family': fontname, 'size': fontsize_legend}
    matplotlib.rc('font', **font)

    def correct_font(x, fontsize=fontsize):
        x.set_fontsize(fontsize)
        x.set_fontname(fontname)

    # load data into alldata
    alldata = []
    allstddevs = []
    data_lbls = []
    ind = 0
    for f in files:
        plotlines = get_csv_fields(f, data_fields)
        for p in plotlines:
            alldata.append(p.data)
            if len(p.stddev) > 0:
                allstddevs.append(p.stddev)
            else:
                allstddevs.append(None)
        data_lbls.append(data_labels[ind])
        if xtick_labels is None:
            xtick_labels = plotlines[0].xtick_labels
        if ylabel is None:
            ylabel = plotlines[0].ylabel
        ind += 1

    # plot data
    plt.figure(figsize=(8, 6))
    plt.subplot(111)
    for (data, stddev, label, color) in zip(alldata, allstddevs, data_lbls, COLORS):
        plt.errorbar(range(len(xtick_labels)), data, stddev, label=label,
                     marker='.', lw=1.0, markersize=9, color=color, linestyle='-')

    # set labels, title and legend
    correct_font(plt.xlabel(xlabel))
    correct_font(plt.ylabel(ylabel))
    if title:
        correct_font(plt.suptitle(title), int(1.3 * fontsize))
    if xtick_legend:
        xtick_legend = xtick_legend.replace(";", "\n")
        yoffset = 0.72
        correct_font(plt.figtext(0.04, yoffset, xtick_legend))

    legend_colls = 2 if len(alldata) > 4 else 1
    plt.legend(loc='best', ncol=legend_colls, title=legend_title, fontsize=fontsize_legend)

    plt.xticks(range(len(xtick_labels)), xtick_labels, rotation=50)
    plt.grid(True)

    # plt.tight_layout()
    if out_file:
        plt.savefig(out_file, bbox_inches='tight')
    else:
        plt.show()


def get_argument_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--files", help="comma-separated list of CSV files, e.g. file1,file2,...")
    parser.add_argument("--data-fields", help="get data values for the plot from the given field in the CSV file (0-indexed).", default="1")
    parser.add_argument("--data-labels", help="manually list the labels for the legend, separated by ','.", default=None)
    parser.add_argument("--xlabel", help="x axis label.", default="Execution time (s)")
    parser.add_argument("--ylabel", help="y axis label.", default=None)
    parser.add_argument("--xtick-labels", help="custom tick labels for the X axis, comma-separated.", default=None)
    parser.add_argument("--xtick-legend", help="legend for the X axis ticks, as ';' separated strings.")
    parser.add_argument("--title", help="plot title.", default="Benchmark")
    parser.add_argument("--legend-title", help="legend title.")
    parser.add_argument("-o", "--outfile", help="file name for saving the plot.", default="plot.png")
    return parser


def exit_with_error(msg):
    print >> sys.stderr, msg
    sys.exit(1)


def check_args(args):
    if not args.files and not args.dir:
        exit_with_error("Please specify benchmark result files.")
    elif not args.data_fields:
        exit_with_error("Please specify the data field index.")


def get_list_arg(arg):
    return arg.split(",") if arg else None


if __name__ == "__main__":
    parser = get_argument_parser()
    args = parser.parse_args()
    check_args(args)

    data_fields_str_list = get_list_arg(args.data_fields)
    data_fields = [int(field) for field in data_fields_str_list]

    plot_data(get_list_arg(args.files),
              data_fields,
              get_list_arg(args.data_labels),
              args.xlabel,
              args.ylabel,
              args.title,
              get_list_arg(args.xtick_labels),
              args.outfile,
              args.legend_title,
              args.xtick_legend)
