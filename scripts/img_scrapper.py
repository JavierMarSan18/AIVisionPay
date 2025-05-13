#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Standard library
import argparse
import os
import time
import uuid
import json
import hashlib
from io import BytesIO
from urllib.parse import urlparse

# Third-party libraries
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
            confirm = input(
                f"⚠️ Trusted domain list at '{path}' is empty. Continue? (y/n): "
            ).strip().lower()
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
                    content = f.read()
                    hashes.add(compute_image_hash(content))
            except Exception as e:
                print(f"⚠️ Could not read {path}: {e}")
    return hashes

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

    assert mode in ("train","validation"), "Mode must be 'train' or 'validation'"

    out_dir   = os.path.join(base_path, version, f"{mode}_data", class_name)
    train_dir = os.path.join(base_path, version, "train_data", class_name)
    os.makedirs(out_dir, exist_ok=True)

    # Count existing images
    existing = [
        f for f in os.listdir(out_dir)
        if f.lower().endswith((".jpg",".jpeg",".png",".webp"))
    ]
    count_exist = len(existing)

    # Print initial status
    print(f"📦 {class_name}: currently {count_exist} images", end="")
    if min_limit is not None:
        rem_min = max(min_limit - count_exist, 0)
        print(f"; needs ≥ {min_limit} (remaining {rem_min})", end="")
    if max_limit is not None:
        rem_max = max_limit - count_exist
        print(f"; max allowed {max_limit} (remaining capacity {rem_max})", end="")
    print(".")

    # If already above max, skip
    if max_limit is not None and count_exist >= max_limit:
        print(f"✅ Skipping {class_name}: reached max {max_limit} images.")
        return

    images_saved = count_exist
    train_hashes = collect_hashes_from_directory(train_dir)

    with DDGS() as ddgs:
        for term in terms:
            # break if reached limits
            if max_limit     is not None and images_saved >= max_limit: break
            if min_limit and images_saved >= min_limit:
                print(f"✅ Reached min {min_limit} images for {class_name}.")
                break

            print(f"\n🔍 Searching for term: {term}")
            retries = 0
            while retries < retry_cfg.get("max_retries",3):
                try:
                    results = ddgs.images(term, max_results=term_limit*2)
                    break
                except RatelimitException:
                    if not retry_cfg.get("enabled",True): break
                    w = retry_cfg.get("wait_seconds",10)
                    print(f"⚠️ Rate limit; retry {retries+1}/{retry_cfg['max_retries']} in {w}s")
                    time.sleep(w)
                    retries += 1
            else:
                print(f"❌ No results for '{term}' due to rate limit.")
                continue

            saved_term = 0
            for r in results:
                if saved_term >= term_limit:    break
                if max_limit and images_saved>=max_limit: break

                url = r["image"]
                try:
                    resp = requests.get(url, timeout=10)
                    if resp.status_code!=200: continue

                    buf = resp.content
                    h   = compute_image_hash(buf)
                    if h in train_hashes: continue

                    img = Image.open(BytesIO(buf))
                    fmt = img.format.upper()
                    if fmt not in allowed:    continue
                    if img.width<min_w or img.height<min_h: continue
                    if len(buf)/(1024*1024)>max_mb: continue

                    dom = urlparse(url).netloc.lower()
                    if trusted_domains and not any(d in dom for d in trusted_domains):
                        continue

                    fname = f"{class_name.replace(' ','_')}_{uuid.uuid4().hex}.{fmt.lower()}"
                    with open(os.path.join(out_dir,fname),"wb") as f:
                        f.write(buf)
                    if config.get("log_successful_downloads",True):
                        print(f"  ✅ Saved: {fname}")

                    saved_term  += 1
                    images_saved+= 1

                    # Print progress after each save
                    status = f"🔢 {class_name}: {images_saved} total"
                    if min_limit is not None:
                        rem_min = max(min_limit - images_saved, 0)
                        status += f", need ≥{min_limit} (remaining {rem_min})"
                    if max_limit is not None:
                        rem_max = max_limit - images_saved
                        status += f", max {max_limit} (capacity {rem_max})"
                    print(status)

                    # break if reached min after save
                    if min_limit and images_saved>=min_limit:
                        print(f"✅ Reached min {min_limit} images for {class_name}.")
                        break

                except Exception as e:
                    if config.get("log_errors",True):
                        print(f"  ⚠️ Error with {url}: {e}")

            print("⏳ Waiting before next term...\n")
            time.sleep(wait_sec)


if __name__=="__main__":
    p=argparse.ArgumentParser(description="Image scraping")
    p.add_argument("--config",required=True,help="Path to scraping_config.json")
    args=p.parse_args()

    cfg = load_json(args.config)
    use_dom = cfg.get("use_trusted_domains", True)
    trusted = (load_trusted_domains(cfg["trusted_domains_path"]) if use_dom else [])
    classes = load_json(cfg["classes_path"])

    for e in classes:
        name  = e["class"]["name"]
        terms = e["class"]["terms_to_seek"]
        print(f"\n🔽 Processing class: {name}")
        search_and_save_images(terms,name,cfg,trusted)