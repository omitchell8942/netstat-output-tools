# netstat-output-tools

Parses the text output of `netstat -an` and `netstat -rn` into structured records.

## Usage

```python
from netstat_output_tools import parse_connections, parse_routes

connections = parse_connections(
    "Proto Recv-Q Send-Q Local Address  Foreign Address  State\n"
    "tcp        0      0 0.0.0.0:22     0.0.0.0:*        LISTEN\n"
)
# [Connection(protocol='tcp', local_address='0.0.0.0:22',
#             foreign_address='0.0.0.0:*', state='LISTEN')]

routes = parse_routes(
    "Destination  Gateway      Genmask      Flags Metric Ref Use Iface\n"
    "0.0.0.0      192.168.1.1  0.0.0.0      UG    100    0   0   eth0\n"
)
# [Route(destination='0.0.0.0', gateway='192.168.1.1', genmask='0.0.0.0',
#        flags=('U', 'G'), metric=100, ref=0, use=0, iface='eth0')]
```

The exported names are exactly `Connection`, `Route`, `parse_connections`, and
`parse_routes`.

## Why this exists

`netstat` output is text and its column layout is not stable across platforms:
UDP rows have no state column, IPv6 addresses contain colons that look like
separators, and BSD/macOS routing tables use a different column set from Linux.
The trade-off this library makes is that it never raises for a line it does not
understand. It skips the line instead. That keeps a single malformed row from
taking down a whole parse, at the cost of silently dropping data. If you need
to know whether anything was dropped, count the non-header lines yourself and
compare against the length of the returned list.

## The awkward edge

`parse_routes` only understands the Linux `-rn` layout. BSD and macOS print a
different set of columns, and rows that do not match the Linux layout are
skipped. If you feed it macOS output you will get an empty list rather than an
error. That is deliberate: guessing at a column layout we have not been given
is more likely to produce wrong data than no data.
