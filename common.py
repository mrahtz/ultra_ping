"""
Common code for all measurement types:
the program main() function, and argument parsing.
"""

import argparse

SERVER_RECV_BUFFER_SIZE = 4096

def main(Measurement):
    """
    Process arguments and run the appropriate functions depending on whether
    we're in server mode or client mode.
    """

    args = parse_args(Measurement.description)

    if args.payload_len > SERVER_RECV_BUFFER_SIZE:
        print("Warning: payload_len (%d) is greater than "
              "SERVER_RECV_BUFFER_SIZE (%d)" % (args.payload_len,
                                                SERVER_RECV_BUFFER_SIZE))

    tester = Measurement(args.output_filename)
    if args.server:
        tester.run_server(args.listen_port, SERVER_RECV_BUFFER_SIZE)
    elif args.client:
        target_address = (args.client, args.listen_port)
        tester.run_client(target_address, args.n_packets, args.payload_len,
                          args.send_rate_kBps)

def parse_args(description):
    """
    Parse arguments.
    """

    parser = argparse.ArgumentParser(
        description=description, formatter_class=argparse.RawTextHelpFormatter)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--server', action='store_true')
    group.add_argument('--client')
    parser.add_argument("--n_packets", type=int, default=100)
    parser.add_argument("--payload_len", type=int, default=256)
    parser.add_argument("--send_rate_kBps", type=int, default=400)
    parser.add_argument(
        "--output_filename", default='udp_packetn_latency_pairs')
    parser.add_argument("--listen_port", type=int, default=8888)
    args = parser.parse_args()
    return args

