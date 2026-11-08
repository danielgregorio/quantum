"""The Godot release is downloaded again when GitHub's CDN fails for a while (quantum/runtime/godot_bin.py)."""

import io
import urllib.error

import pytest

from quantum.runtime import godot_bin


def failing(*codes):
    """An urlopen that fails with these statuses, then answers."""
    calls = []

    def urlopen(url, timeout):
        calls.append(url)
        if len(calls) <= len(codes):
            raise urllib.error.HTTPError(url, codes[len(calls) - 1], 'Gateway Time-out', {}, io.BytesIO())
        return io.BytesIO(b'zip')
    return urlopen, calls


def test_a_server_failure_is_tried_again(monkeypatch):
    urlopen, calls = failing(504, 502)
    monkeypatch.setattr(godot_bin.urllib.request, 'urlopen', urlopen)
    said, waited = [], []
    assert godot_bin._fetch('https://example.test/godot.zip', said.append, waited.append) == b'zip'
    assert len(calls) == 3 and waited == [5, 15]
    assert said == ['HTTP 504; trying again in 5s', 'HTTP 502; trying again in 15s']


def test_it_gives_up_after_the_last_wait_and_a_404_at_once(monkeypatch):
    urlopen, calls = failing(504, 504, 504, 504)
    monkeypatch.setattr(godot_bin.urllib.request, 'urlopen', urlopen)
    with pytest.raises(urllib.error.HTTPError):
        godot_bin._fetch('https://example.test/godot.zip', sleep=lambda s: None)
    assert len(calls) == 4
    urlopen, calls = failing(404)
    monkeypatch.setattr(godot_bin.urllib.request, 'urlopen', urlopen)
    with pytest.raises(urllib.error.HTTPError):
        godot_bin._fetch('https://example.test/godot.zip', sleep=lambda s: None)
    assert len(calls) == 1
