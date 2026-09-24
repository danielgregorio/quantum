"""
Without psutil, the admin scanned ports 1-9999 of localhost, one at a time.

`ResourceDiscovery._scan_ports_socket` did a connect_ex with a 0.1 s timeout
on each port. On Linux a closed port refuses at once and nobody noticed; on
Windows each attempt waits for the timeout — measured: ~109 ms per port, about
18 MINUTES for a single request to /api/resources/overview.

Found by running the suite on a new clone: psutil was declared nowhere, the
development machine happened to have it, and on the clean clone the admin's
smoke test hung until it was killed.
"""

import pathlib
import sys

ADMIN = pathlib.Path(__file__).resolve().parents[2] / "quantum_admin"
for path in (str(ADMIN), str(ADMIN / "backend")):
    if path not in sys.path:
        sys.path.insert(0, path)

from backend.resource_manager import ResourceDiscovery  # noqa: E402


def test_without_psutil_it_does_not_scan_ports(monkeypatch):
    # A fake socket that only counts: against the old code this test fails in
    # milliseconds (10 thousand attempts) instead of hanging for 18 minutes.
    import backend.resource_manager as rm

    attempts = []

    class CountingSocket:
        def __init__(self, *a, **k):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def settimeout(self, _):
            pass

        def connect_ex(self, address):
            attempts.append(address)
            return 1

    monkeypatch.setattr(rm.socket, "socket", CountingSocket)
    discovery = ResourceDiscovery()
    discovery._psutil_available = False

    assert discovery.scan_ports_in_use() == []
    assert attempts == [], f"it scanned {len(attempts)} ports"


def test_psutil_is_a_declared_dependency_of_the_admin():
    requirements = (ADMIN / "backend" / "requirements.txt").read_text(encoding="utf-8")
    assert any(l.strip().startswith("psutil") for l in requirements.splitlines())
