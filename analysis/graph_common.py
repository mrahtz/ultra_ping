from __future__ import print_function, division
import os.path
import collections
import matplotlib.pyplot as plt
from matplotlib.ticker import ScalarFormatter
import numpy as np

"""
Helper functions used by both latency_measurement_graphs.py and other projects
analysing latency data.
"""


def draw_histogram(latencies_ms,
                   bins,
                   cutoff_time_ms,
                   draw_xlabel=True,
                   draw_ylabel=True):
    """
    Draw one individual histogram.
    """
    n, bins, patches = plt.hist(latencies_ms, bins, color='white', hatch='/')
    if draw_xlabel:
        plt.xlabel("Packet latency (ms)")
    if draw_ylabel:
        plt.ylabel("Frequency")
    plt.gca().set_xscale("log")
    plt.gca().xaxis.set_major_formatter(ScalarFormatter())
    plt.xlim([min(bins), max(bins)])
    plt.xticks([1, cutoff_time_ms, 100])


def read_latencies_file(latencies_filename):
    """
    Read the list of packet numbers, latencies, and the total number of received
    packets from one recording file.
    """
    with open(latencies_filename, 'r') as latencies_file:
        lines = latencies_file.read().split('\n')
    packet_ns = []
    latencies_ms = []
    total_n_packets = int(lines[0])
    for line in lines[1:]:
        if len(line) == 0:
            continue
        fields = line.split(' ')
        packet_n = int(fields[0])
        packet_ns.append(packet_n)
        latency_us = float(fields[1])
        latency_ms = latency_us / 1000
        latencies_ms.append(latency_ms)
    packet_ns = np.array(packet_ns)
    latencies_ms = np.array(latencies_ms)
    return (packet_ns, latencies_ms, total_n_packets)


def read_latencies_files(filenames):
    """
    Read latency data from multiple files, and return the data from each file as
    a separate entry in a list
    """
    data_all_files = []
    for path in filenames:
        (packet_ns, latencies_ms, total_n_packets) = read_latencies_file(path)
        filename = os.path.basename(path)
        datum = (filename, packet_ns, latencies_ms, total_n_packets)
        data_all_files.append(datum)
    return data_all_files


def merge_all_hosts(data_all_hosts):
    """
    Concenate data from all hosts, for combined analysis.
    """
    all_packet_ns = []
    all_latencies_ms = []
    all_total_n_packets = 0
    all_filenames = ""
    for board_n in range(len(data_all_hosts)):
        (filename, packet_ns, latencies_ms,
         total_n_packets) = data_all_hosts[board_n]
        all_packet_ns.extend(packet_ns)
        all_latencies_ms.extend(latencies_ms)
        all_total_n_packets += total_n_packets
        if all_filenames == "":
            all_filenames = filename
        else:
            all_filenames += (", %s" % filename)
    return [(all_filenames, all_packet_ns, all_latencies_ms,
             all_total_n_packets)]


def calculate_max_latency(data_all_hosts):
    """
    Find the maximum latency observed in all data.
    """
    all_latencies = []
    for i in range(len(data_all_hosts)):
        (_, _, latencies_ms, _) = data_all_hosts[i]
        all_latencies.extend(latencies_ms)
    max_latency_ms = np.amax(all_latencies)
    return max_latency_ms


def calculate_histogram_bins(packet_data, n_bins=20, min_latency_ms=1):
    """
    Calculate logarithmically-spaced covering the data from min_latency_ms up to
    the maximum latency observed.
    """
    max_latency_ms = calculate_max_latency(packet_data)
    bins_log_scale = np.logspace(
        np.log10(min_latency_ms), np.log10(max_latency_ms), n_bins)
    return bins_log_scale


def calc_basic_statistics(packet_ns, latencies_ms, total_n_packets,
                          cutoff_time_ms):
    """
    Calculate number/percentage of packets totally dropped and arriving beyond
    the specified cutoff time
    """
    print("Calculating basic drop statistics...", end='')

    n_totally_dropped = total_n_packets - len(packet_ns)
    pct_totally_dropped = 100 * (n_totally_dropped / total_n_packets)

    n_made_it = sum(np.array(latencies_ms) < cutoff_time_ms)
    n_dropped_or_beyond_cutoff = total_n_packets - n_made_it
    pct_dropped_or_beyond_cutoff = \
            100 * (n_dropped_or_beyond_cutoff / total_n_packets)

    BasicStats = collections.namedtuple(
        "BasicStats",
        "pct_totally_dropped pct_dropped_or_beyond_cutoff n_totally_dropped n_dropped_or_beyond_cutoff"
    )

    print("done!")
    return BasicStats(pct_totally_dropped, pct_dropped_or_beyond_cutoff,
                      n_totally_dropped, n_dropped_or_beyond_cutoff)


def calc_consecutive_drop_statistics(packet_ns, latencies_ms, total_n_packets,
                                     cutoff_time_ms):
    """
    Calculate the number of times that two packets in a row are dropped or
    delayed, considering two scenarios:
    1) out-of-order packets are dropped 2) packets are reordered
    """
    print("Calculating consecutive drop statistics...")

    # First, generate a list of booleans representing whether each
    # original packet was received OK

    # Generate one list where "OK" means "received in order and within cutoff
    # time", and one list where "OK" just means "within cutoff time"

    out_of_order_packet_indices = find_out_of_order_packet_indices(packet_ns)
    packet_ns_out_of_order_removed = \
        np.delete(packet_ns, out_of_order_packet_indices)
    latencies_ms_out_of_order_removed = \
        np.delete(latencies_ms, out_of_order_packet_indices)
    received_packets_out_of_order_removed = \
        packets_received_within_cutoff(packet_ns_out_of_order_removed,
                latencies_ms_out_of_order_removed,
                                   total_n_packets, cutoff_time_ms)

    sort_idxs = np.argsort(packet_ns)
    packet_ns_reordered = np.array(packet_ns)[sort_idxs]
    latencies_ms_reordered = np.array(latencies_ms)[sort_idxs]
    received_packets_sorted = packets_received_within_cutoff(
        packet_ns_reordered, latencies_ms_reordered, total_n_packets,
        cutoff_time_ms)

    # Then use those lists to find all the pairs of packets marked 'not OK'

    n_consecutive_drops_out_of_order_removed = \
        count_consecutive_n_drops(
            received_packets_out_of_order_removed, n_drops=2
        )
    n_consecutive_drops_resorted = \
        count_consecutive_n_drops(
            received_packets_sorted, n_drops=2
        )
    # total_n_packets - 1: the number of pairs of packets
    pct_consecutive_drops_out_of_order_removed = (
        100 * n_consecutive_drops_out_of_order_removed / (total_n_packets - 1))
    pct_consecutive_drops_resorted = (100 * n_consecutive_drops_resorted /
                                      (total_n_packets - 1))

    ConsecutiveStats = collections.namedtuple(
        "ConsecutiveStats",
        "pct_consecutive_drops_out_of_order_removed pct_consecutive_drops_resorted"
    )
    return ConsecutiveStats(pct_consecutive_drops_out_of_order_removed,
                            pct_consecutive_drops_resorted)


def find_out_of_order_packet_indices(packet_ns):
    """
    Return indices of packets which have apparently arrived out-of-order.
    Specifically: return indices of any packet number which was less than the
    previous packet number. For example, for the list of packet numbers:
        0, 1, 2, 3, 5, 4, 6, 7.
    return index 5 (corresponding to '4').
    """
    indices = []
    prev_packet_n = packet_ns[0] - 1
    for i in range(len(packet_ns)):
        packet_n = packet_ns[i]
        if packet_n > prev_packet_n:
            # say, if the previous packet was 2, and now we're at 3
            # or if the previous packet was 3, and now we're at 5
            prev_packet_n = packet_n
        elif packet_n < prev_packet_n:
            # e.g. if the previous packet was 5, and we're now at 4
            # (having given up all hope of seeing 4 again when we saw 5)
            indices.append(i)
    return indices


def packets_received_within_cutoff(packet_ns, latencies_ms, total_n_packets,
                                   cutoff_time_ms):
    """
    Return a list of booleans indicating whether each of the total_n_packets
    packets was received before the specified cutoff time.
    """
    received_packets = []
    for packet_n in range(total_n_packets):
        idx = np.where(packet_ns == packet_n)[0]
        if len(idx) == 0:
            # Packet wasn't received at all
            received_packets.append(False)
        elif latencies_ms[idx] > cutoff_time_ms:
            # Received beyond cutoff
            received_packets.append(False)
        else:
            received_packets.append(True)
    return received_packets


def count_consecutive_n_drops(packets_received, n_drops):
    # This is horrible, but the basic idea is:
    # a = [1, 2, 3, 4, 5]
    # In [25]: zip(a[0:-1], a[1:])
    # Out[25]: [(1, 2), (2, 3), (3, 4), (4, 5)]
    # In [26]: zip(a[0:-2], a[1:], a[2:])
    # Out[26]: [(1, 2, 3), (2, 3, 4), (3, 4, 5)]
    zip_list = []
    shift = packets_received[0:-(n_drops - 1)]
    zip_list.append(shift)
    for i in range(1, n_drops):
        shift = packets_received[i:]
        zip_list.append(shift)
    packet_blocks = zip(*zip_list)

    consecutive_n_drops = 0
    for packet_block in packet_blocks:
        if list(packet_block) == [False] * n_drops:
            consecutive_n_drops += 1

    return consecutive_n_drops
