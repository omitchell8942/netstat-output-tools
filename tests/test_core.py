import unittest

from netstat_output_tools import (
    Connection,
    Route,
    parse_connections,
    parse_routes,
)


class ParseConnectionsTests(unittest.TestCase):
    def test_parses_tcp_and_udp_lines(self):
        text = (
            "Active Internet connections (servers and established)\n"
            "Proto Recv-Q Send-Q Local Address           Foreign Address         State\n"
            "tcp        0      0 0.0.0.0:22              0.0.0.0:*               LISTEN\n"
            "tcp        0      0 127.0.0.1:5432          127.0.0.1:51000         ESTABLISHED\n"
            "udp        0      0 0.0.0.0:68              0.0.0.0:*\n"
        )
        got = parse_connections(text)
        self.assertEqual(
            got,
            [
                Connection("tcp", "0.0.0.0:22", "0.0.0.0:*", "LISTEN"),
                Connection("tcp", "127.0.0.1:5432", "127.0.0.1:51000", "ESTABLISHED"),
                Connection("udp", "0.0.0.0:68", "0.0.0.0:*", ""),
            ],
        )

    def test_udp_line_without_state_column_gets_empty_state(self):
        # UDP rows have no State column; the parser must not invent one and
        # must not treat the missing column as an error.
        text = "udp 0 0 0.0.0.0:68 0.0.0.0:*\n"
        self.assertEqual(
            parse_connections(text),
            [Connection("udp", "0.0.0.0:68", "0.0.0.0:*", "")],
        )

    def test_skips_unknown_protocols_and_short_lines(self):
        text = (
            "unix  2      [ ]         DGRAM\n"
            "tcp 0 0 0.0.0.0:22\n"
            "tcp 0 0 0.0.0.0:22 0.0.0.0:* LISTEN\n"
        )
        self.assertEqual(
            parse_connections(text),
            [Connection("tcp", "0.0.0.0:22", "0.0.0.0:*", "LISTEN")],
        )

    def test_empty_input_returns_empty_list(self):
        self.assertEqual(parse_connections(""), [])

    def test_protocol_is_lowercased(self):
        text = "TCP 0 0 0.0.0.0:22 0.0.0.0:* LISTEN\n"
        self.assertEqual(
            parse_connections(text),
            [Connection("tcp", "0.0.0.0:22", "0.0.0.0:*", "LISTEN")],
        )

    def test_ipv6_addresses_are_kept_verbatim(self):
        text = "tcp6 0 0 :::22 :::* LISTEN\n"
        self.assertEqual(
            parse_connections(text),
            [Connection("tcp6", ":::22", ":::*", "LISTEN")],
        )


class ParseRoutesTests(unittest.TestCase):
    def test_parses_linux_layout(self):
        text = (
            "Kernel IP routing table\n"
            "Destination     Gateway         Genmask         Flags Metric Ref    Use Iface\n"
            "0.0.0.0         192.168.1.1     0.0.0.0         UG    100    0        0 eth0\n"
            "192.168.1.0     0.0.0.0         255.255.255.0   U     100    0        0 eth0\n"
        )
        got = parse_routes(text)
        self.assertEqual(
            got,
            [
                Route("0.0.0.0", "192.168.1.1", "0.0.0.0", ("U", "G"), 100, 0, 0, "eth0"),
                Route("192.168.1.0", "0.0.0.0", "255.255.255.0", ("U",), 100, 0, 0, "eth0"),
            ],
        )

    def test_flags_are_a_tuple_not_a_string(self):
        # A string would make `"U" in flags` true for "UG", which is wrong.
        text = "0.0.0.0 192.168.1.1 0.0.0.0 UG 100 0 0 eth0\n"
        route = parse_routes(text)[0]
        self.assertIsInstance(route.flags, tuple)
        self.assertEqual(route.flags, ("U", "G"))

    def test_skips_non_numeric_metric_rows(self):
        # BSD/macOS rows have a different column count and non-numeric
        # fields; they must be skipped rather than mis-parsed.
        text = (
            "default            192.168.1.1       UGScg                 en0\n"
            "0.0.0.0 192.168.1.1 0.0.0.0 UG 100 0 0 eth0\n"
        )
        self.assertEqual(
            parse_routes(text),
            [Route("0.0.0.0", "192.168.1.1", "0.0.0.0", ("U", "G"), 100, 0, 0, "eth0")],
        )

    def test_empty_input_returns_empty_list(self):
        self.assertEqual(parse_routes(""), [])

    def test_metric_ref_use_are_ints(self):
        text = "0.0.0.0 192.168.1.1 0.0.0.0 UG 100 0 0 eth0\n"
        route = parse_routes(text)[0]
        self.assertEqual((route.metric, route.ref, route.use), (100, 0, 0))
        self.assertIsInstance(route.metric, int)
        self.assertIsInstance(route.ref, int)
        self.assertIsInstance(route.use, int)

    def test_skips_short_lines(self):
        text = "0.0.0.0 192.168.1.1 0.0.0.0 UG 100\n"
        self.assertEqual(parse_routes(text), [])


if __name__ == "__main__":
    unittest.main()
