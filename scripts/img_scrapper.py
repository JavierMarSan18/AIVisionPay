#!/usr/bin/env python3
import argparse
import os
import time
import uuid
import json
import hashlib
import random
from io import BytesIO
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import urllib.robotparser

import requests
from PIL import Image
from duckduckgo_search import DDGS
from duckduckgo_search.exceptions import RatelimitException
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from requests.exceptions import ProxyError

# Lista de User Agents para evitar bloqueos 403
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:115.0) Gecko/20100101 Firefox/115.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7; rv:114.0) Gecko/20100101 Firefox/114.0"
]

def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_trusted_domains(path):
    try:
        return {line.strip().lower() for line in open(path, 'r', encoding='utf-8') if line.strip()}
    except FileNotFoundError:
        print(f"⚠️ Trusted domain file not found: {path}")
        return set()


def compute_image_hash(content_bytes):
    return hashlib.md5(content_bytes).hexdigest()


def collect_hashes_from_directory(directory):
    hashes = set()
    for root, _, files in os.walk(directory):
        for file in files:
            try:
                buf = open(os.path.join(root, file), 'rb').read()
                hashes.add(compute_image_hash(buf))
            except:
                continue
    return hashes


def create_session(config):
    session = requests.Session()
    proxies = config.get('proxies') or {}
    session.proxies.update(proxies)
    session.headers.update({
        'User-Agent': random.choice(USER_AGENTS),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'es-ES,es;q=0.9,en-US;q=0.8',
        'Connection': 'keep-alive'
    })
    if config.get('referer'):
        session.headers['Referer'] = config['referer']
    return session


def attach_retry(session, config):
    retry_cfg = config.get('retry_on_rate_limit', {})
    retry = Retry(
        total=retry_cfg.get('max_retries', 3),
        backoff_factor=retry_cfg.get('wait_seconds', 5),
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=['GET', 'HEAD']
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)


def get_crawl_delay(config, base_url):
    try:
        rp = urllib.robotparser.RobotFileParser()
        rp.set_url(base_url.rstrip('/') + '/robots.txt')
        rp.read()
        delay = rp.crawl_delay('*')
        if delay is not None:
            return delay
    except:
        pass
    return config.get('sleep_between_queries', 0.5)


def overflow_collector(out_dir, max_limit, allowed_exts, log_success):
    files = [f for f in os.listdir(out_dir)
             if os.path.isfile(os.path.join(out_dir, f)) and
                f.split('.')[-1].lower() in allowed_exts]
    total = len(files)
    if total <= max_limit:
        return
    files_full = [os.path.join(out_dir, f) for f in files]
    files_full.sort(key=lambda x: os.path.getctime(x))
    to_remove = files_full[: total - max_limit]
    for path in to_remove:
        try:
            os.remove(path)
            if log_success:
                print(f"🗑️ Removed overflow image: {os.path.basename(path)}")
        except Exception as e:
            print(f"⚠️ Error removing {path}: {e}")


def fetch_and_save(session, url, out_dir, class_name, train_hashes,
                   allowed_exts, min_w, min_h, max_mb,
                   trusted_domains, overwrite, log_success, log_errors):
    session.headers['User-Agent'] = random.choice(USER_AGENTS)
    original_proxies = session.proxies.copy()
    try:
        try:
            resp = session.get(url, timeout=10)
        except ProxyError:
            if log_errors:
                print(f"⚠️ Proxy error for {url}, retrying without proxy")
            session.proxies = {}
            resp = session.get(url, timeout=10)
        if resp.status_code == 403:
            if log_errors:
                print(f"🚫 403 for {url}")
            return False
        if resp.status_code != 200 or not resp.content:
            if log_errors:
                print(f"⚠️ HTTP {resp.status_code} for {url}")
            return False
        buf = resp.content
        img_hash = compute_image_hash(buf)
        if img_hash in train_hashes:
            return False
        img = Image.open(BytesIO(buf))
        fmt = (img.format or '').lower()
        if fmt not in allowed_exts:
            return False
        if img.width < min_w or img.height < min_h:
            return False
        if len(buf) / (1024 * 1024) > max_mb:
            return False
        domain = urlparse(url).netloc.lower()
        if trusted_domains and domain not in trusted_domains:
            return False
        filename = f"{class_name}_{uuid.uuid4().hex}.{fmt}"
        save_path = os.path.join(out_dir, filename)
        if not overwrite and os.path.exists(save_path):
            return False
        with open(save_path, 'wb') as f:
            f.write(buf)
        if log_success:
            print(f"✅ Saved: {filename}")
        return True
    except Exception as e:
        if log_errors:
            print(f"❌ Error saving {url}: {e}")
        return False
    finally:
        session.proxies = original_proxies


def search_and_save_images(terms, class_name, config, trusted_domains):
    base_path = config['output_base_path']
    version = config['version']
    mode = config['mode']
    limits = config['limits']
    min_limit = limits.get('min_image_limit_per_class', 0)
    max_limit = limits.get('max_image_limit_per_class')
    min_w, min_h = config.get('min_resolution', [0,0])
    max_mb = config.get('max_file_size_mb', 5)
    allowed_exts = tuple(fmt.lower() for fmt in config.get('allowed_formats', []))
    overwrite = config.get('overwrite_existing', False)
    log_success = config.get('log_successful_downloads', True)
    log_errors = config.get('log_errors', True)

    out_dir = os.path.join(base_path, version, f"{mode}_data", class_name)
    train_dir = os.path.join(base_path, version, "train_data", class_name)
    os.makedirs(out_dir, exist_ok=True)

    existing = [f for f in os.listdir(out_dir)
                if f.split('.')[-1].lower() in allowed_exts]
    images_saved = len(existing)
    print(f"📦 {class_name}: {images_saved} existing images")
    if max_limit and images_saved > max_limit:
        overflow_collector(out_dir, max_limit, allowed_exts, log_success)
        images_saved = max_limit
        print(f"🔽 Trimmed to max limit: {max_limit} images")

    train_hashes = collect_hashes_from_directory(train_dir)
    session = create_session(config)
    attach_retry(session, config)
    base_url = session.headers.get('Referer', 'https://www.google.com')
    delay = get_crawl_delay(config, base_url)

    with DDGS() as ddgs:
        round_count = 0
        while images_saved < min_limit:
            round_count += 1
            print(f"🔄 Round {round_count}: {images_saved}/{min_limit}")
            all_urls = []
            for term in terms:
                print(f"🔍 Searching: {term}")
                attempts = 0
                results = []
                while True:
                    try:
                        results = ddgs.images(term, max_results=100)
                        break
                    except RatelimitException:
                        attempts += 1
                        if attempts > config['retry_on_rate_limit'].get('max_retries', 3):
                            print(f"⚠️ Skipping term {term} after rate limit")
                            break
                        wait = config['retry_on_rate_limit'].get('wait_seconds', 5)
                        print(f"⏳ Back-off {wait}s due to rate limit")
                        time.sleep(wait)
                urls = [r.get('image') for r in results if r.get('image')]
                all_urls.extend(urls)
                time.sleep(delay + random.uniform(0, delay))

            unique_urls = list(dict.fromkeys(all_urls))
            random.shuffle(unique_urls)

            prev_count = images_saved
            # CORRECCIÓN: incluir 'for url in unique_urls' en la comprensión
            with ThreadPoolExecutor(max_workers=config.get('concurrency', 10)) as executor:
                futures = {
                    executor.submit(
                        fetch_and_save, session, url, out_dir, class_name,
                        train_hashes, allowed_exts, min_w, min_h, max_mb,
                        trusted_domains, overwrite, log_success, log_errors
                    ): url for url in unique_urls
                }

                for future in as_completed(futures):
                    url = futures[future]
                    try:
                        if future.result():
                            images_saved += 1
                        if max_limit and images_saved > max_limit:
                            break
                    except Exception as e:
                        if log_errors:
                            print(f"❌ Error downloading {url}: {e}")

            if max_limit and images_saved > max_limit:
                overflow_collector(out_dir, max_limit, allowed_exts, log_success)
                images_saved = max_limit
            if images_saved == prev_count:
                print("⚠️ No new images this round, aborting")
                break

    if images_saved < min_limit:
        print(f"❌ {class_name}: only {images_saved}, minimum {min_limit}")
        exit(1)
    print(f"🎉 {class_name}: completed with {images_saved}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Image scraping')
    parser.add_argument('--config', required=True)
    args = parser.parse_args()

    cfg = load_json(args.config)
    trusted = set()
    if cfg.get('use_trusted_domains', False):
        trusted = load_trusted_domains(cfg.get('trusted_domains_path', ''))

    classes = load_json(cfg.get('classes_path', ''))
    for entry in classes:
        cls = entry.get('class', {})
        name = cls.get('name')
        terms = cls.get('terms_to_seek', [])
        if not name or not terms:
            print(f"⚠️ Skipping invalid entry: {entry}")
            continue
        print(f"\n🔽 Clase: {name}")
        search_and_save_images(terms, name, cfg, trusted)