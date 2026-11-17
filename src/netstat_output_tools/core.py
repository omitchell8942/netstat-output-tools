"""Parsers for the text output of ``netstat -an`` and ``netstat -rn``.

The two commands are parsed independently because their line formats are
unrelated: ``-an`` emits one record per socket, ``-rn`` emits one record per
route. Keeping them in separate functions means a caller who only has one of
the two outputs does not have to care about the other.

The parser is deliberately line-oriented and tolerant: real ``netstat`` output
varies between platforms and between releases, so instead of failing on a line
we cannot understand we skip it. That is a trade-off: the parser never raises
for malformed input, but it also cannot tell you that it silently dropped a
line. Callers that need strictness should compare the number of parsed records
against the number of non-header lines themselves.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Iterator, List, Optional, Sequence


@dataclass(frozen=True)
class Connection:
    """A single active connection as reported by ``netstat -an``.

    ``local_address`` and ``foreign_address`` are kept exactly as printed,
    including any ``.port`` suffix. Splitting host and port apart is left to
    the caller because the separator differs between the IPv4 (``.``) and
    IPv6 (``.`` inside brackets) forms and guessing wrong loses information.
    """

    protocol: str
    local_address: str
    foreign_address: str
    state: str


@dataclass(frozen=True)
class Route:
    """A single routing table entry as reported by ``netstat -rn``.

    ``flags`` is a tuple because the flag column is a set of single-character
    flags; storing it as a string makes ``"U" in flags`` accidentally true for
    ``"UG"``, which is a bug waiting to happen.
    """

    destination: str
    gateway: str
    genmask: str
    flags: tuple
    metric: int
    ref: int
    use: int
    iface: str


_PROTOCOLS = frozenset({"tcp", "tcp4", "tcp6", "udp", "udp4", "udp6"})


def _is_header(line: str) -> bool:
    """Return True for the column header lines netstat prints.

    Header detection is by first token rather than by column count because
    the column set differs between ``-an`` and ``-rn`` and we want one helper
    to serve both. ``Proto`` and ``Destination`` are the first tokens on the
    respective headers on every platform we care about.
    """

    first = line.split(None, 1)[0] if line.split() else ""
    return first in ("Proto", "Active", "Destination", "Kernel", "Routing")


def parse_connections(text: str) -> List[Connection]:
    """Parse ``netstat -an`` output into :class:`Connection` records.

    Lines whose first token is not a known IP protocol are skipped. This is
    what makes the function safe to feed the whole captured output of the
    command, including the ``Active Internet connections`` banner and the
    ``Proto Recv-Q Send-Q ...`` header.

    The ``-an`` layouts include two leading numeric columns (``Recv-Q`` and
    ``Send-Q``) before the address columns for both TCP and UDP. The address
    columns are therefore the two fields after those counters, and the state
    is whatever follows (UDP lines have no state column).
    """

    connections: List[Connection] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or _is_header(line):
            continue
        parts = line.split()
        if len(parts) < 5:
            continue
        proto = parts[0].lower()
        if proto not in _PROTOCOLS:
            continue
        # Skip the Recv-Q and Send-Q counters; the address columns follow.
        local = parts[3]
        foreign = parts[4]
        state = parts[5] if len(parts) > 5 else ""
        connections.append(
            Connection(
                protocol=proto,
                local_address=local,
                foreign_address=foreign,
                state=state,
            )
        )
    return connections


def parse_routes(text: str) -> List[Route]:
    """Parse ``netstat -rn`` output into :class:`Route` records.

    The Linux ``-rn`` layout is ``Destination Gateway Genmask Flags Metric
    Ref Use Iface``. BSD and macOS print a different set of columns, so this
    function only claims to understand the Linux layout; other layouts are
    skipped rather than mis-parsed. Rows whose numeric columns are not
    integers are skipped for the same reason.
    """

    routes: List[Route] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or _is_header(line):
            continue
        parts = line.split()
        if len(parts) < 8:
            continue
        destination, gateway, genmask, flags, metric_s, ref_s, use_s, iface = (
            parts[0],
            parts[1],
            parts[2],
            parts[3],
            parts[4],
            parts[5],
            parts[6],
            parts[7],
        )
        try:
            metric = int(metric_s)
            ref = int(ref_s)
            use = int(use_s)
        except ValueError:
            # A non-numeric metric/ref/use means this is not a Linux route
            # row; skipping is safer than guessing at an alternative layout.
            continue
        routes.append(
            Route(
                destination=destination,
                gateway=gateway,
                genmask=genmask,
                flags=tuple(flags),
                metric=metric,
                ref=ref,
                use=use,
                iface=iface,
            )
        )
    return routes
