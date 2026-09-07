"""Manual link check: python backend/check_learning_resources.py [--verbose].

This is deliberately separate from application requests and unit tests. A 403
or timeout may be a crawler block, so inspect failures before replacing links.
Only static catalog URLs are fetched; user data and search fallbacks are excluded.
"""

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from html import unescape
import re

import requests

from learning_resources import RESOURCE_CATALOG


def check_link(url):
    try:
        with requests.get(url, timeout=(5, 20), stream=True, headers={'User-Agent': 'ResuMind-resource-link-check/1.0'}) as response:
            sample = next(response.iter_content(chunk_size=131072), b'').decode('utf-8', errors='replace')
            title_match = re.search(r'<title[^>]*>(.*?)</title>', sample, re.S | re.I)
            title = re.sub(r'\s+', ' ', unescape(title_match.group(1))).strip() if title_match else ''
            soft_failure = bool(re.search(r'\b404\b|page not found|just a moment|access denied', title, re.I))
            ok = response.status_code == 200 and not soft_failure
            return ok, response.status_code, url, response.url, title[:160]
    except requests.RequestException as error:
        return False, type(error).__name__, url, url, ''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verbose', action='store_true')
    args = parser.parse_args()
    urls = sorted({resource['url'] for group in RESOURCE_CATALOG.values() for resource in group})
    failures = 0
    with ThreadPoolExecutor(max_workers=6) as pool:
        for future in as_completed([pool.submit(check_link, url) for url in urls]):
            ok, status, url, final_url, title = future.result()
            failures += not ok
            if args.verbose or not ok:
                print('OK' if ok else 'CHECK', status, url, '->', final_url, '|', title, flush=True)
    print(f'{len(urls) - failures}/{len(urls)} resource URLs passed; {failures} need review.')
    return 1 if failures else 0


if __name__ == '__main__':
    raise SystemExit(main())
