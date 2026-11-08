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
    urlopen, calls = failing(*[504] * (len(godot_bin.RETRY_WAITS) + 1))
    monkeypatch.setattr(godot_bin.urllib.request, 'urlopen', urlopen)
    with pytest.raises(urllib.error.HTTPError):
        godot_bin._fetch('https://example.test/godot.zip', sleep=lambda s: None)
    assert len(calls) == len(godot_bin.RETRY_WAITS) + 1
    urlopen, calls = failing(404)
    monkeypatch.setattr(godot_bin.urllib.request, 'urlopen', urlopen)
    with pytest.raises(urllib.error.HTTPError):
        godot_bin._fetch('https://example.test/godot.zip', sleep=lambda s: None)
    assert len(calls) == 1


def test_when_github_keeps_failing_godots_own_service_is_asked(monkeypatch, tmp_path):
    import zipfile
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, 'w') as zf:
        zf.writestr('Godot_v4.4.1-stable_linux.x86_64', b'binary')
    asked = []

    def urlopen(url, timeout):
        asked.append(url)
        if 'github.com' in url:
            raise urllib.error.HTTPError(url, 504, 'Gateway Time-out', {}, io.BytesIO())
        return io.BytesIO(archive.getvalue())

    monkeypatch.setattr(godot_bin.urllib.request, 'urlopen', urlopen)
    monkeypatch.setattr(godot_bin.time, 'sleep', lambda s: None)
    monkeypatch.setattr(godot_bin, 'release_platform', lambda: 'linux.x86_64')
    monkeypatch.setattr(godot_bin, 'cache_dir', lambda: tmp_path)
    binary = godot_bin.download_godot()
    assert binary.read_bytes() == b'binary'
    assert sum('github.com' in u for u in asked) == len(godot_bin.RETRY_WAITS) + 1
    assert asked[-1] == ('https://downloads.godotengine.org/?version=4.4.1&flavor=stable'
                         '&slug=linux.x86_64.zip&platform=linux.64')
