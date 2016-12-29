"""
Interface with a hardware timer implemented as a counter on a ValentF(x) LOGI
Pi FPGA board.
"""

import logi

counter_timestep_us = 10
max_counter_value = 65535

def read_counter():
    """
    Read the current value of the counter.
    """
    address = 0
    type_size = 2
    n_reads = 1
    return logi.logiRead(address, n_reads, type_size)[0]

def counter_delta(counter_value_2, counter_value_1):
    """
    Calculate counter_value_2 - counter_value_1 (accounting for wraparound)
    """
    delta = counter_value_2 - counter_value_1
    if delta < 0:
        # counter has wrapped around
        delta += max_counter_value
    return delta

def counter_delta_to_us(delta):
    """
    Convert a difference in counter values to a time difference.
    """
    return delta * counter_timestep_us
