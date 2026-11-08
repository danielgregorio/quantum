"""The Godot release, and its export templates, are fetched again when GitHub's CDN fails for a while, and
from Godot's own download service when it keeps failing (quantum/runtime/godot_bin.py)."""

import io
import urllib.error
import zipfile

import pytest

from quantum.runtime import godot_bin


def a_zip(name='Godot_v4.4.1-stable_linux.x86_64', body=b'binary'):
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, 'w') as zf:
        zf.writestr(name, body)
    return archive.getvalue()


def answers(*replies):
    """An urlopen that answers each call with the next reply: a status (an error) or bytes."""
    calls = []

    def urlopen(request, timeout):
        url = request.full_url
        calls.append(url)
        reply = replies[min(len(calls), len(replies)) - 1]
        if isinstance(reply, int):
            raise urllib.error.HTTPError(url, reply, 'Gateway Time-out', {}, io.BytesIO())
        return io.BytesIO(reply)
    return urlopen, calls


@pytest.fixture(autouse=True)
def no_waiting(monkeypatch):
    monkeypatch.setattr(godot_bin.time, 'sleep', lambda s: None)


def test_a_server_failure_is_tried_again(monkeypatch, tmp_path):
    urlopen, calls = answers(504, 502, b'zip')
    monkeypatch.setattr(godot_bin.urllib.request, 'urlopen', urlopen)
    said = []
    godot_bin._fetch_to('https://example.test/godot.zip', tmp_path / 'g.zip', said.append)
    assert (tmp_path / 'g.zip').read_bytes() == b'zip' and len(calls) == 3
    assert said == ['HTTP 504; trying again in 5s', 'HTTP 502; trying again in 15s']
    assert not (tmp_path / 'g.zip.part').exists()


def test_it_gives_up_after_the_last_wait_and_on_a_404_at_once(monkeypatch, tmp_path):
    urlopen, calls = answers(504)
    monkeypatch.setattr(godot_bin.urllib.request, 'urlopen', urlopen)
    with pytest.raises(urllib.error.HTTPError):
        godot_bin._fetch_to('https://example.test/godot.zip', tmp_path / 'g.zip')
    assert len(calls) == len(godot_bin.RETRY_WAITS) + 1 and not (tmp_path / 'g.zip').exists()
    urlopen, calls = answers(404)
    monkeypatch.setattr(godot_bin.urllib.request, 'urlopen', urlopen)
    with pytest.raises(urllib.error.HTTPError):
        godot_bin._fetch_to('https://example.test/godot.zip', tmp_path / 'g.zip')
    assert len(calls) == 1


def test_when_github_keeps_failing_godots_own_service_is_asked(monkeypatch, tmp_path):
    asked = []

    def urlopen(request, timeout):
        url = request.full_url
        asked.append(url)
        if 'github.com' in url:
            raise urllib.error.HTTPError(url, 504, 'Gateway Time-out', {}, io.BytesIO())
        return io.BytesIO(a_zip())

    monkeypatch.setattr(godot_bin.urllib.request, 'urlopen', urlopen)
    monkeypatch.setattr(godot_bin, 'release_platform', lambda: 'linux.x86_64')
    monkeypatch.setattr(godot_bin, 'cache_dir', lambda: tmp_path)
    binary = godot_bin.download_godot()
    assert binary.read_bytes() == b'binary' and not list(tmp_path.glob('*.zip'))
    assert sum('github.com' in u for u in asked) == len(godot_bin.RETRY_WAITS) + 1
    assert asked[-1] == ('https://downloads.godotengine.org/?version=4.4.1&flavor=stable'
                         '&slug=linux.x86_64.zip&platform=linux.64')


def test_each_request_names_its_client(monkeypatch, tmp_path):
    # Godot's download service turns away a request that names Python's urllib as its client (403)
    seen = []

    def urlopen(request, timeout):
        seen.append(request.get_header('User-agent'))
        return io.BytesIO(b'zip')

    monkeypatch.setattr(godot_bin.urllib.request, 'urlopen', urlopen)
    godot_bin._fetch_to('https://downloads.godotengine.org/?version=4.4.1', tmp_path / 'g.zip')
    assert seen == [godot_bin.USER_AGENT] and 'urllib' not in godot_bin.USER_AGENT


def test_a_page_that_is_not_the_release_asks_the_next_source(monkeypatch, tmp_path):
    urlopen, calls = answers(b'<html>busy</html>', a_zip())
    monkeypatch.setattr(godot_bin.urllib.request, 'urlopen', urlopen)
    target = godot_bin.fetch_release(['https://a.test/x.zip', 'https://b.test/x.zip'], tmp_path / 'x.zip',
                                     check=lambda p: zipfile.ZipFile(p).close())
    assert zipfile.is_zipfile(target) and calls == ['https://a.test/x.zip', 'https://b.test/x.zip']


def test_the_templates_come_from_the_same_two_sources():
    github, service = godot_bin.templates_urls()
    assert github.endswith('/4.4.1-stable/Godot_v4.4.1-stable_export_templates.tpz')
    assert service == ('https://downloads.godotengine.org/?version=4.4.1&flavor=stable'
                       '&slug=export_templates.tpz&platform=templates')
