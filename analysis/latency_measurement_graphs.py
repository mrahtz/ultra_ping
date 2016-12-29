#!/usr/bin/env python3
"""
Analyse packet latency measurements made by packet_latency_tester.

Specifically, plot graphs showing a timeseries of packet latencies and a
histogram of packet latency distribution.
"""

from __future__ import print_function, division
import argparse
import os.path
import numpy as np
import matplotlib
import graph_common

description = """Plot graphs of latency measurements made by packet_latency_tester.
Specifically, plot a timeseries of latencies and a
histogram of packet latency distribution."""
parser = argparse.ArgumentParser(description=description)

parser.add_argument(
    "measurement_filenames",
    nargs='+',
    help='One or more latency measurement files produced by packet_latency_tester'
)
parser.add_argument(
    "--cutoff_time_ms",
    type=int,
    default=10,
    help='The latency beyond which packets are considered delayed')
parser.add_argument(
    "--histogram_merge_all_files",
    action='store_true',
    help='Merge packet latencies from all files when drawing the histogram')

parser.add_argument(
    "--noninteractive",
    action='store_true',
    help='Only save the graphs to .png files without showing anything on screen'
)
parser.add_argument(
    "--fast",
    action='store_true',
    help="Don't calculate statistics which take a while to compute")
parser.add_argument("--no_histograms", action='store_true')
parser.add_argument("--no_timeseries", action='store_true')

parser.add_argument(
    "--output_postfix",
    default='',
    help="Postfix for the output graph filesnames")
args = parser.parse_args()

if args.noninteractive:
    matplotlib.use('Agg')
import matplotlib.pyplot as plt


def main():
    """
    Call appropriate drawing functions depending on command-line arguments.
    """
    data_path = os.path.dirname(args.measurement_filenames[0])
    data_all_files = graph_common.read_latencies_files(
        args.measurement_filenames)

    if not args.no_histograms:
        draw_histograms(data_all_files, args.histogram_merge_all_files,
                        args.fast, args.cutoff_time_ms, data_path,
                        args.output_postfix)
    if not args.no_timeseries:
        draw_timeseries(data_all_files, args.cutoff_time_ms, data_path,
                        args.output_postfix)

    if not args.noninteractive:
        plt.show()


def draw_histograms(packets_all_hosts, histogram_merge_all_files,
                    skip_slow_analyses, cutoff_time_ms, save_dir,
                    output_postfix):
    """
    Draw histograms of packet latency.
    """
    if histogram_merge_all_files:
        packet_data = graph_common.merge_all_hosts(packets_all_hosts)
    else:
        packet_data = packets_all_hosts

    bins_log_scale = graph_common.calculate_histogram_bins(packet_data)
    n_result_sets = len(packet_data)
    plt.figure(figsize=(10, 6))
    plt.suptitle("Packet latency histograms")
    text_vertical_spacing = 1.0 / n_result_sets
    for result_set_n in range(n_result_sets):
        (filename, packet_ns, latencies_ms,
         total_n_packets) = packet_data[result_set_n]
        plt.subplot(n_result_sets, 1, result_set_n + 1)
        plt.title(filename)
        last_plot = (result_set_n == (n_result_sets - 1))
        if last_plot:
            xlabel = True
        else:
            xlabel = False
        graph_common.draw_histogram(latencies_ms, bins_log_scale, cutoff_time_ms, xlabel)
        y = 1 - result_set_n * text_vertical_spacing - 0.5 * text_vertical_spacing
        text = gen_histogram_text(packet_ns, latencies_ms, total_n_packets,
                                  cutoff_time_ms, skip_slow_analyses)
        plt.figtext(0.55, y, text, verticalalignment='center')
    plt.tight_layout()
    plt.subplots_adjust(top=0.9)  # to make room for suptitle
    plt.subplots_adjust(right=0.5)

    plot_filename = os.path.join(save_dir, 'udp_latency_histogram%s.png' %
                                 output_postfix)
    plt.savefig(plot_filename)




def gen_histogram_text(packet_ns, latencies_ms, total_n_packets,
                       cutoff_time_ms, skip_slow_analyses):
    """
    Generate the informational text describing characteristics of the latency
    distribution to accompany the histograms.
    """
    basicStats = graph_common.calc_basic_statistics(packet_ns, latencies_ms,
                                       total_n_packets, cutoff_time_ms)
    text = 'Packet statistics (assuming %d ms cutoff):\n' % cutoff_time_ms
    text += '%.1f%% (%d packets) totally dropped\n' % (
        basicStats.pct_totally_dropped, basicStats.n_totally_dropped)
    text += '%.1f%% (%d packets) totally dropped or delayed\n' % (
        basicStats.pct_dropped_or_beyond_cutoff,
        basicStats.n_dropped_or_beyond_cutoff)

    if not skip_slow_analyses:
        consecutiveStats = graph_common.calc_consecutive_drop_statistics(
            packet_ns, latencies_ms, total_n_packets, cutoff_time_ms)
        text += '%.1f%% consecutive pairs of packets dropped/delayed\n(out-of-order packets ignored)\n' % consecutiveStats.pct_consecutive_drops_out_of_order_removed
        text += '%.1f%% consecutive pairs of packets dropped/delayed\n(packets reordered)\n' % consecutiveStats.pct_consecutive_drops_resorted

    return text


def draw_timeseries(packets_all_hosts, cutoff_time_ms, save_dir,
                    output_postfix):
    """
    Draw a timeseries of packet latencies over time, in order that the packets
    were sent in
    """
    plt.figure()
    plt.suptitle("Packet latency over time")

    n_hosts = len(packets_all_hosts)
    for board_n in range(n_hosts):
        (filename, packet_ns, latencies_ms,
         total_n_packets) = packets_all_hosts[board_n]
        # Make copies, so that we don't distort the data that the other plots make use of
        packet_ns = list(packet_ns)
        latencies_ms = list(latencies_ms)

        (packet_ns, latencies_ms, dropped_packet_nos) = \
            add_dropped_packets_and_sort(total_n_packets, packet_ns, latencies_ms)

        plt.subplot(n_hosts, 1, 1 + board_n)
        plt.title(filename)

        line = plt.plot(packet_ns, latencies_ms)[0]
        if board_n == (n_hosts - 1):
            plt.xlabel("Packet no.")
        plt.ylabel("Latency (ms)")

        plt.twinx()  # Set up a second y-axis
        (bin_starts, bin_width_packets, drops) = drops_or_delays_in_each_bin(
            packet_ns, latencies_ms, cutoff_time_ms)
        bars = plt.bar(bin_starts,
                       drops,
                       bin_width_packets,
                       alpha=0.5,
                       color='red')
        plt.ylabel("Pct. packets dropped\nor > %d ms" % cutoff_time_ms)
        plt.ylim([0, 100])

        if board_n == 0:
            plt.legend([line, bars], ['Latencies', 'Pct. delayed packets'])

    plt.tight_layout()
    plt.subplots_adjust(top=0.9)  # to make room for suptitle

    plot_filename = os.path.join(save_dir, 'udp_latency_timeseries%s.png' %
                                 output_postfix)
    plt.savefig(plot_filename)


def add_dropped_packets_and_sort(total_n_packets, packet_ns, latencies_ms):
    """
    Fill in packets that were dropped (with a zero latency value), and then
    sort the list of packets in the order that they were sent
    """
    if total_n_packets != len(packet_ns):
        print("Warning: using untested code for handling dropped packets")
    dropped_packet_nos = np.array(
        list(set(range(total_n_packets)).difference(set(packet_ns))))
    for packet_n in dropped_packet_nos:
        packet_ns.append(packet_n)
        # Dropped packets are distinguishable as packets with zero latency
        latencies_ms.append(0)

    sort_idxs = np.argsort(packet_ns)
    packet_ns = np.array(packet_ns)[sort_idxs]
    latencies_ms = np.array(latencies_ms)[sort_idxs]

    return (packet_ns, latencies_ms, dropped_packet_nos)


def drops_or_delays_in_each_bin(packet_ns,
                                latencies_ms,
                                cutoff_time_ms,
                                bin_width_packets=100):
    """
    Calculate percentage of packets lost or delayed beyond the specific cutoff
    time in each segment (bin_width_packets long) of the latency data.

    (We assume that packets are being sent at a constant rate, so that packet
    number is an accurate representation of packet send time, which is what
    we're binning against.)
    """
    # We assume that packet_ns is continuous
    # (i.e. that dropped packets have already been dealt with)
    bin_starts = range(0, len(packet_ns), bin_width_packets)

    drops = []
    for bin_start in bin_starts:
        bin_end = bin_start + bin_width_packets
        n_drops = \
            np.sum(np.array(latencies_ms[bin_start:bin_end]) > cutoff_time_ms)
        # Dropped packets have their latency set to zero, so we have to count them separately
        n_drops += \
            np.sum(np.array(latencies_ms[bin_start:bin_end]) == 0)

        n_drops_pct = 100 * n_drops / bin_width_packets
        drops.append(n_drops_pct)

    return (bin_starts, bin_width_packets, drops)


main()
