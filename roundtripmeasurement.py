"""
Measure round-trip packet latencies.
"""

import measurement
import socket
import multiprocessing
import time
import pickle
import sys

class RoundTripMeasurement(measurement.Measurement):

    description = """Measure round-trip UDP packet latency.
On your server host, run:
    $ ./echo.py --server
On your client host(s), run:
    $ ./echo.py --client <IP address of server host>
echo.py on your client host will spit out a file containing the round-trip
latencies of each packet received back from the server."""

    def run_client(self, target_address, n_packets, payload_len,
            send_rate_kbytes_per_s):
        """
        Start the two client threads: one to send packets, and one to receive them.
        """
        sender = multiprocessing.Process(
            target=self.send_packets,
            args=(target_address, n_packets, payload_len, send_rate_kbytes_per_s))

        listen_port = target_address[1] + 1
        output_filename = self.test_output_filename
        receiver = multiprocessing.Process(
            target=self.recv_packets,
            args=(listen_port, n_packets, payload_len, output_filename))

        receiver.start()
        sender.start()

        sender.join()
        receiver.join()


    @staticmethod
    def pre_send(n_packets, sock_out):
        return

    def run_server(self, listen_port, recv_buffer_size):
        """
        Listen for UDP packets on listen_port, and when a packet is
        received, immediately send it back to the host it came from (to
        port listen_port + 1).
        """
        sock_in = \
            socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock_in.bind(("0.0.0.0", listen_port))

        sock_out = \
            socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)

        print("UDP server running...")

        while True:
            try:
                data, recv_addr = sock_in.recvfrom(recv_buffer_size)
                if not data:
                    break
                send_addr = (recv_addr[0], listen_port + 1)
                sock_out.sendto(data, send_addr)
            except KeyboardInterrupt:
                break
        print("Closing...")
        sock_out.close()
        sys.exit(0)

    @classmethod
    def get_packet_payload(cls, packet_n):
        send_time_seconds = time.time()
        payload = pickle.dumps((packet_n, send_time_seconds))
        return payload

    @classmethod
    def recv_packets(cls, listen_port, n_packets_expected, payload_len,
                     output_filename):
        """
        Receive packets bounced back from the server. Calculate the round-trip
        latency for each packet by comparing the transmission timestamp contained
        within the packet to the system time at time of packet receipt.
        """

        sock_in = \
            socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock_in.bind(("0.0.0.0", listen_port))

        timeout_seconds = 5
        sock_in.settimeout(timeout_seconds)

        packets = []
        try:
            while len(packets) < n_packets_expected:
                packet = sock_in.recv(payload_len)
                recv_time = time.time()
                payload = packet.rstrip("a")
                (packet_n, send_time) = pickle.loads(payload)
                latency_us = (recv_time - send_time) * 1e6
                packets.append((packet_n, latency_us))
        except socket.timeout:
            print("Note: timed out waiting to receive packets")
            print("So far, had received %d packets" % len(packets))

        print("Received %d/%d packets back from server" % (len(packets),
                                                           n_packets_expected))

        cls.save_packet_latencies(packets, n_packets_expected, output_filename)
        sock_in.close()
