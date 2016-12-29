#!/usr/bin/env python

"""
Measure round-trip UDP packet latency between two hosts.

One host runs the script in server mode.
Server mode simply listens for packets on the designated port,
and when it receives a packet, sends it back to the host it came from.

The other host runs in client mode. The client mode runs two threads:
- One thread sends packets to the host in server mode. Each packet contains a
  timestamp specifying when the packet was sent.
- One thread receives packets that have been bounced back from the server. The
  round-trip latency is calculated for each packet by comparing the send
  timestamp in the packet to the time of packet receipt.

The client-mode script outputs a plain text list of packet number/round-trip
latency (in milliseconds) tuples for each packet received, one per line. The
first line of the file specifies the number of packets sent, enabling
calculation of the number of packets that got lost along the way.
"""

import common
import roundtripmeasurement

common.main(roundtripmeasurement.RoundTripMeasurement)
