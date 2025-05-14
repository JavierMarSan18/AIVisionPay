import argparse
import os
import time
import uuid
import json
import hashlib
from io import BytesIO
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from PIL import Image
from duckduckgo_search import DDGS
from duckduckgo_search.exceptions import RatelimitException

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def load_trusted_domains(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            domains = [line.strip() for line in f if line.strip()]
        if not domains:
            confirm = input(f"⚠️ Trusted domain list at '{path}' is empty. Continue? (y/n): ").strip().lower()
            if confirm != "y":
                print("❌ Aborting due to empty trusted domain list.")
                exit(1)
        return domains
    except FileNotFoundError:
        print(f"⚠️ Trusted domain file not found: {path}")
        return []

def compute_image_hash(content_bytes):
    return hashlib.md5(content_bytes).hexdigest()

def collect_hashes_from_directory(directory):
    hashes = set()
    for root, _, files in os.walk(directory):
        for file in files:
            path = os.path.join(root, file)
            try:
                with open(path, 'rb') as f:
                    hashes.add(compute_image_hash(f.read()))
            except Exception as e:
                print(f"⚠️ Could not read {path}: {e}")
    return hashes

def fetch_and_save(session, url, out_dir, class_name, train_hashes,
                   allowed_formats, min_w, min_h, max_mb,
                   trusted_domains):
    try:
        resp = session.get(url, timeout=10)
        if resp.status_code != 200:
            return None
        buf = resp.content
        h = compute_image_hash(buf)
        if h in train_hashes:
            return None

        img = Image.open(BytesIO(buf))
        fmt = img.format.upper()
        if fmt not in allowed_formats:
            return None
        if img.width < min_w or img.height < min_h:
            return None
        if len(buf) / (1024 * 1024) > max_mb:
            return None

        dom = urlparse(url).netloc.lower()
        if trusted_domains and not any(d in dom for d in trusted_domains):
            return None

        filename = f"{class_name.replace(' ', '_')}_{uuid.uuid4().hex}.{fmt.lower()}"
        path = os.path.join(out_dir, filename)
        with open(path, "wb") as f:
            f.write(buf)
        return filename
    except Exception:
        return None

def search_and_save_images(terms, class_name, config, trusted_domains):
    version       = config["version"]
    mode          = config["mode"]
    term_limit    = config["limits"]["image_limit_per_term"]
    max_limit     = config["limits"].get("max_image_limit_per_class")
    min_limit     = config["limits"].get("min_image_limit_per_class")
    base_path     = config["output_base_path"]
    min_w, min_h  = config["min_resolution"]
    max_mb        = config["max_file_size_mb"]
    allowed       = {fmt.upper() for fmt in config["allowed_formats"]}
    retry_cfg     = config["retry_on_rate_limit"]
    wait_sec      = config["sleep_between_queries"]
    concurrency   = config.get("concurrency", 10)

    assert mode in ("train","validation"), "Mode must be 'train' or 'validation'"

    out_dir   = os.path.join(base_path, version, f"{mode}_data", class_name)
    train_dir = os.path.join(base_path, version, "train_data", class_name)
    os.makedirs(out_dir, exist_ok=True)

    existing = [
        f for f in os.listdir(out_dir)
        if f.lower().endswith((".jpg",".jpeg",".png",".webp"))
    ]
    count_exist = len(existing)
    print(f"📦 {class_name}: {count_exist} existing images")

    if max_limit is not None and count_exist >= max_limit:
        print(f"✅ Skipping {class_name}: reached max {max_limit} images.")
        return

    images_saved = count_exist
    train_hashes = collect_hashes_from_directory(train_dir)
    session = requests.Session()

    with DDGS() as ddgs:
        for term in terms:
            if max_limit and images_saved >= max_limit:
                break
            if min_limit and images_saved >= min_limit:
                print(f"✅ Reached min {min_limit} for {class_name}.")
                break

            print(f"\n🔍 Searching term: {term}")
            retries = 0
            while retries < retry_cfg.get("max_retries",3):
                try:
                    results = ddgs.images(term, max_results=term_limit*2)
                    break
                except RatelimitException:
                    if not retry_cfg.get("enabled",True):
                        break
                    w = retry_cfg.get("wait_seconds",10)
                    print(f"⚠️ Rate limit; retry {retries+1}/{retry_cfg['max_retries']} in {w}s")
                    time.sleep(w)
                    retries += 1
            else:
                print(f"❌ No results for '{term}' due to rate limit.")
                continue

            urls = [r["image"] for r in results]
            saved_term = 0

            with ThreadPoolExecutor(max_workers=concurrency) as executor:
                futures = {
                    executor.submit(
                        fetch_and_save, session, url, out_dir, class_name,
                        train_hashes, allowed, min_w, min_h, max_mb, trusted_domains
                    ): url for url in urls
                }
                for future in as_completed(futures):
                    filename = future.result()
                    if filename:
                        print(f"  ✅ Saved: {filename}")
                        saved_term += 1
                        images_saved += 1
                    if saved_term >= term_limit or (max_limit and images_saved >= max_limit):
                        break

            print(f"⏳ {class_name}: {images_saved} total, waiting {wait_sec}s before next term\n")
            time.sleep(wait_sec)

if __name__=="__main__":
    p = argparse.ArgumentParser(description="Image scraping")
    p.add_argument("--config", required=True, help="Path to scraping_config.json")
    args = p.parse_args()

    cfg     = load_json(args.config)
    use_dom = cfg.get("use_trusted_domains", True)
    trusted = load_trusted_domains(cfg["trusted_domains_path"]) if use_dom else []
    classes = load_json(cfg["classes_path"])

    for e in classes:
        name  = e["class"]["name"]
        terms = e["class"]["terms_to_seek"]
        print(f"\n🔽 Processing class: {name}")
        search_and_save_images(terms, name, cfg, trusted)
