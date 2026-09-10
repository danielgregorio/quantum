"""Crawl the built docs site and fail on any internal link that does not resolve.

    npx vitepress build docs
    npx vitepress preview docs --port 4173 &
    python scripts/check-docs-links.py http://localhost:4173/quantum/

The VitePress config has `ignoreDeadLinks: true`, so the build never reports a
link to a page that does not exist. That hid 18 of them — five in the guide's
own sidebar (Actions & Forms, Authentication, Sessions, Email, Data Import).
This walks every page reachable from the root, follows every href/src that
stays under the site's base path, and exits 1 if any answers 4xx/5xx or if a
link escapes the base (which breaks on GitHub Pages).
"""
import re
import sys
import time
import urllib.error
import urllib.request
from urllib.parse import urldefrag, urljoin, urlparse


def main(root: str) -> int:
    base = urlparse(root).path
    for _ in range(120):
        try:
            urllib.request.urlopen(root, timeout=2)
            break
        except Exception:
            time.sleep(0.5)
    else:
        print(f"site not reachable at {root}")
        return 1

    seen, queue, broken, escaping, origin = set(), [root], [], set(), {}
    pages = 0
    while queue:
        url = queue.pop()
        if url in seen:
            continue
        seen.add(url)
        try:
            response = urllib.request.urlopen(url, timeout=15)
            body, ctype = response.read(), response.headers.get('content-type', '')
        except urllib.error.HTTPError as e:
            broken.append((e.code, url, origin.get(url)))
            continue
        if 'html' not in ctype:
            continue
        pages += 1
        for match in re.finditer(r'(?:href|src)="([^"]+)"', body.decode('utf-8', 'replace')):
            target = match.group(1)
            if target.startswith(('http', 'mailto:', 'data:', '#', 'javascript:')):
                continue
            absolute = urldefrag(urljoin(url, target))[0]
            if not urlparse(absolute).path.startswith(base):
                escaping.add((target, url))
                continue
            origin.setdefault(absolute, url)
            if absolute not in seen:
                queue.append(absolute)

    print(f"{pages} pages, {len(seen)} URLs checked")
    for code, url, source in sorted(broken):
        print(f"  BROKEN {code} {url}  (linked from {source})")
    for target, source in sorted(escaping):
        print(f"  ESCAPES BASE {target}  (in {source})")
    return 1 if broken or escaping else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else 'http://localhost:4173/quantum/'))
